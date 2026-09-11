# Copyright: (c) 2026, Jonas Mauer
# SPDX-License-Identifier: MIT
"""Native LDAP storage shared by domain password policies and PSOs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ansible_collections.jomrr.samba.plugins.module_utils.samba_conn import (
    connect_samdb,
)
from ansible_collections.jomrr.samba.plugins.module_utils.samba_user_io import (
    build_child_dn,
    load_ldb,
)

DOMAIN_ATTRIBUTES = {
    "minimum_length": "minPwdLength",
    "history_length": "pwdHistoryLength",
    "minimum_age_days": "minPwdAge",
    "maximum_age_days": "maxPwdAge",
    "lockout_threshold": "lockoutThreshold",
    "lockout_duration_minutes": "lockoutDuration",
    "lockout_window_minutes": "lockOutObservationWindow",
}
PSO_ATTRIBUTES = {
    "minimum_length": "msDS-MinimumPasswordLength",
    "history_length": "msDS-PasswordHistoryLength",
    "minimum_age_days": "msDS-MinimumPasswordAge",
    "maximum_age_days": "msDS-MaximumPasswordAge",
    "lockout_threshold": "msDS-LockoutThreshold",
    "lockout_duration_minutes": "msDS-LockoutDuration",
    "lockout_window_minutes": "msDS-LockoutObservationWindow",
    "complexity": "msDS-PasswordComplexityEnabled",
    "reversible_encryption": "msDS-PasswordReversibleEncryptionEnabled",
}
INTERVALS = {
    "minimum_age_days": 864_000_000_000,
    "maximum_age_days": 864_000_000_000,
    "lockout_duration_minutes": 600_000_000,
    "lockout_window_minutes": 600_000_000,
}
PASSWORD_FLAGS = {"complexity": 1, "reversible_encryption": 16}
NEVER = -(1 << 63)
Settings = dict[str, int | float]


def settings_argument_spec() -> dict[str, dict[str, str]]:
    """Expose the same settings for the domain and individual PSOs."""
    return {
        name: {"type": "bool" if name in PASSWORD_FLAGS else "int"}
        for name in PSO_ATTRIBUTES
    }


def attribute_values(record: Any, attribute: str) -> list[str]:
    """Decode LDAP values without treating bytes as their Python repr."""
    return [value.decode("utf-8") for value in record.get(attribute, [])]


def read_settings(record: Any, *, pso: bool = False) -> Settings:
    """Translate LDAP flags and relative NT timestamps into policy values."""
    attributes = PSO_ATTRIBUTES if pso else DOMAIN_ATTRIBUTES
    result: Settings = {}
    for name, attribute in attributes.items():
        value = attribute_values(record, attribute)[0]
        if name in PASSWORD_FLAGS:
            result[name] = value.upper() == "TRUE"
        elif name in INTERVALS:
            ticks = int(value)
            whole, remainder = divmod(-ticks, INTERVALS[name])
            result[name] = 0 if ticks == NEVER else whole + remainder / INTERVALS[name]
        else:
            result[name] = int(value)
    if not pso:
        flags = int(attribute_values(record, "pwdProperties")[0])
        result.update({name: bool(flags & bit) for name, bit in PASSWORD_FLAGS.items()})
    return result


def merge_settings(current: Settings, requested: dict[str, Any]) -> Settings:
    """Preserve unspecified values and validate the resulting age relationship."""
    desired = current | {
        name: value for name, value in requested.items() if value is not None
    }
    for name, value in desired.items():
        if name not in PASSWORD_FLAGS and value < 0:
            raise ValueError(f"{name} must not be negative")
    if desired["maximum_age_days"] and (
        desired["minimum_age_days"] >= desired["maximum_age_days"]
    ):
        raise ValueError("minimum_age_days must be less than maximum_age_days")
    return desired


def encode_settings(
    settings: Settings, *, pso: bool = False, password_flags: int = 0
) -> dict[str, list[str]]:
    """Encode policy values, preserving unrelated domain password flags."""
    attributes = PSO_ATTRIBUTES if pso else DOMAIN_ATTRIBUTES
    result = {}
    for name, attribute in attributes.items():
        value = settings.get(name)
        if value is None:
            continue
        if name in PASSWORD_FLAGS:
            encoded = "TRUE" if value else "FALSE"
        elif name in INTERVALS:
            ticks = -int(value) * INTERVALS[name]
            if value == 0 and (
                name == "maximum_age_days" or (not pso and name.startswith("lockout_"))
            ):
                ticks = NEVER
            encoded = str(ticks)
        else:
            encoded = str(value)
        result[attribute] = [encoded]
    if not pso and any(settings.get(name) is not None for name in PASSWORD_FLAGS):
        for name, bit in PASSWORD_FLAGS.items():
            if settings.get(name) is None:
                continue
            password_flags = (
                password_flags | bit if settings[name] else password_flags & ~bit
            )
        result["pwdProperties"] = [str(password_flags)]
    return result


def inherited_pso_attributes(domain: Any) -> dict[str, list[str]]:
    """Copy domain defaults to a new PSO without rounding relative timestamps."""
    attributes = {
        PSO_ATTRIBUTES[name]: attribute_values(domain, attribute)
        for name, attribute in DOMAIN_ATTRIBUTES.items()
    }
    flags = int(attribute_values(domain, "pwdProperties")[0])
    attributes.update(
        encode_settings(
            {name: bool(flags & bit) for name, bit in PASSWORD_FLAGS.items()}, pso=True
        )
    )
    for name in ("lockout_duration_minutes", "lockout_window_minutes"):
        attribute = PSO_ATTRIBUTES[name]
        if attributes[attribute] == [str(NEVER)]:
            attributes[attribute] = ["0"]
    return attributes


class PasswordPolicyStore:
    """Read and reconcile password-policy attributes through a bound SamDB."""

    def __init__(self, samdb: Any) -> None:
        self.samdb = samdb
        self.ldb = load_ldb()

    def read(self, dn: Any, attributes: list[str]) -> Any:
        """Return a policy object or None when the requested PSO does not exist."""
        try:
            return self.samdb.search(
                base=dn, scope=self.ldb.SCOPE_BASE, attrs=attributes
            )[0]
        except self.ldb.LdbError as error:
            if error.args[0] == self.ldb.ERR_NO_SUCH_OBJECT:
                return None
            raise

    def domain(self) -> Any:
        """Read the domain's password settings and flag word."""
        return self.read(
            self.samdb.domain_dn(), list(DOMAIN_ATTRIBUTES.values()) + ["pwdProperties"]
        )

    def write(
        self, dn: Any, attributes: dict[str, list[str]], current: Any, check_mode: bool
    ) -> bool:
        """Create a PSO or replace only changed attributes in one LDAP request."""
        changes = {
            name: values
            for name, values in attributes.items()
            if current is None
            or sorted(attribute_values(current, name)) != sorted(values)
        }
        if changes and not check_mode:
            message = self.ldb.Message(self.ldb.Dn(self.samdb, str(dn)))
            for name, values in changes.items():
                message[name] = self.ldb.MessageElement(
                    values, self.ldb.FLAG_MOD_REPLACE, name
                )
            if current is None:
                self.samdb.add(message)
            else:
                self.samdb.modify(message)
        return bool(changes)

    def subjects(self, names: list[str]) -> list[str]:
        """Resolve account names or DNs to users and global security groups."""
        resolved = set()
        for name in names:
            escaped = self.ldb.binary_encode(name)
            expression = (
                f"(&(|(sAMAccountName={escaped})(distinguishedName={escaped}))"
                "(|(&(objectClass=user)(!(objectClass=computer)))"
                "(&(objectClass=group)(groupType=-2147483646))))"
            )
            result = self.samdb.search(
                base=self.samdb.domain_dn(), expression=expression, attrs=[]
            )
            if len(result) != 1:
                raise ValueError(f"User or global security group not found: {name}")
            resolved.add(str(result[0].dn))
        return sorted(resolved)


def reconcile_domain(samdb: Any, params: dict[str, Any], check_mode: bool) -> dict:
    """Update requested domain settings without overwriting other password flags."""
    store = PasswordPolicyStore(samdb)
    current = store.domain()
    desired = merge_settings(read_settings(current), params["settings"])
    attributes = encode_settings(
        params["settings"],
        password_flags=int(attribute_values(current, "pwdProperties")[0]),
    )
    changed = store.write(current.dn, attributes, current, check_mode)
    return {"changed": changed, "dn": str(current.dn), "settings": desired}


def reconcile_pso(samdb: Any, params: dict[str, Any], check_mode: bool) -> dict:
    """Manage a PSO and its exact set of subjects; inherit creation defaults."""
    store = PasswordPolicyStore(samdb)
    parent = store.ldb.Dn(
        samdb, f"CN=Password Settings Container,CN=System,{samdb.domain_dn()}"
    )
    dn = build_child_dn(samdb, "CN", params["name"], parent)
    current = store.read(
        dn,
        list(PSO_ATTRIBUTES.values())
        + ["msDS-PasswordSettingsPrecedence", "msDS-PSOAppliesTo"],
    )
    if params["state"] == "absent":
        if current is not None and not check_mode:
            samdb.delete(dn)
        return {"changed": current is not None, "dn": str(dn), "state": "absent"}
    baseline = store.domain() if current is None else current
    desired = merge_settings(
        read_settings(baseline, pso=current is not None), params["settings"]
    )
    attributes = encode_settings(params["settings"], pso=True)
    if current is None:
        attributes = inherited_pso_attributes(baseline) | attributes
    subjects = store.subjects(params["applies_to"])
    attributes["msDS-PasswordSettingsPrecedence"] = [str(params["precedence"])]
    attributes["msDS-PSOAppliesTo"] = subjects
    if current is None:
        attributes["objectClass"] = ["msDS-PasswordSettings"]
        if not subjects:
            del attributes["msDS-PSOAppliesTo"]
    changed = store.write(dn, attributes, current, check_mode)
    return {
        "changed": changed,
        "dn": str(dn),
        "state": "present",
        "settings": desired,
        "applies_to": subjects,
        "precedence": params["precedence"],
    }


def run_module(
    module: Any, reconcile: Callable[[Any, dict[str, Any], bool], dict]
) -> None:
    """Bind and report policy changes through the common Ansible interface."""
    samdb = connect_samdb(module)
    ldb = load_ldb()
    try:
        result = reconcile(samdb, module.params, module.check_mode)
    except (ValueError, ldb.LdbError) as error:
        module.fail_json(msg=str(error))
    else:
        module.exit_json(**result)
