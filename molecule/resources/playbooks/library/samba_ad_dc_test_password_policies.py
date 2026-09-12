#!/usr/bin/python
"""Exercise domain password policies and fine-grained password settings."""

import importlib
import tempfile
from pathlib import Path
from typing import Any

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.jomrr.samba.plugins.module_utils.samba_conn import (
    connect_samdb,
    connection_argument_spec,
)

DOCUMENTATION = r"""
module: samba_ad_dc_test_password_policies
short_description: Exercise password policies throughout the Molecule lifecycle
description:
  - Verifies effective password policies and explicit PSO assignments.
  - Seeds precise LDAP intervals and checks preservation during role updates.
  - Verifies policy changes, deletion, inheritance and check-mode preservation.
extends_documentation_fragment:
  - jomrr.samba.connection
options:
  phase:
    description: Fixture phase to seed or verify.
    type: str
    required: true
    choices: [initial, seed, seeded, updated]
author:
  - Jonas Mauer (@jomrr)
"""

EXAMPLES = r"""
- name: SAMBA_AD_DC | Verify password policies
  samba_ad_dc_test_password_policies:
    server: dc1.ad.example.test
    bind_username: Administrator
    bind_password: "{{ samba_ad_dc_admin_password }}"
    phase: initial
"""

DOMAIN_INTERVALS = {
    "minPwdAge": "-432000000000",
    "lockoutDuration": "-900000000",
    "lockOutObservationWindow": "-900000000",
}
PSO_INTERVALS = {
    "msDS-MinimumPasswordAge": "-216000000000",
    "msDS-LockoutDuration": "-1500000000",
    "msDS-LockoutObservationWindow": "-1500000000",
}

ATTRIBUTES = [
    "msDS-ResultantPSO",
    "msDS-PasswordSettingsPrecedence",
    "msDS-PSOAppliesTo",
    "msDS-MinimumPasswordLength",
    "minPwdLength",
    *DOMAIN_INTERVALS,
    *PSO_INTERVALS,
]


def expect(record: Any, attribute: str, values: list[str]) -> None:
    """Compare directory attributes without returning any account secrets."""
    actual = [value.decode() for value in record.get(attribute, [])]
    if sorted(actual) != sorted(values):
        raise RuntimeError(f"Unexpected {attribute} on {record.dn}: {actual}")


def ticket(module: Any, username: str, password: str, cache: str) -> None:
    """Obtain a real ticket in a disposable cache and verify its encryption."""
    environment = {"KRB5CCNAME": f"FILE:{cache}", "LC_ALL": "C"}
    module.run_command(
        ["kinit", f"{username}@{module.params['realm']}"],
        data=password,
        environ_update=environment,
        check_rc=True,
    )
    _, output, _ = module.run_command(
        ["klist", "-e"], environ_update=environment, check_rc=True
    )
    if (
        "aes256-cts-hmac-sha1-96" not in output
        and "aes128-cts-hmac-sha1-96" not in output
    ):
        raise RuntimeError("The issued Kerberos ticket does not use AES")


def verify_password_settings(samdb: Any) -> None:
    """An ordinary user inherits the domain policy and then the administrator PSO."""
    ldb = importlib.import_module("ldb")
    username = "molecule-policy"
    expression = f"(sAMAccountName={username})"
    samdb.newuser(username, "Ordinary-Pw1!")
    user = samdb.search(expression=expression, attrs=["msDS-ResultantPSO"])[0]
    try:
        if "msDS-ResultantPSO" in user:
            raise RuntimeError("The ordinary user unexpectedly has a PSO")
        samdb.add_remove_group_members("Domain Admins", [username], True)
        user = samdb.search(expression=expression, attrs=["msDS-ResultantPSO"])[0]
        expected = ldb.Dn(
            samdb,
            f"CN=domain_admins,CN=Password Settings Container,CN=System,{samdb.domain_dn()}",
        )
        applied = user.get("msDS-ResultantPSO")
        if applied is None or ldb.Dn(samdb, applied[0].decode()) != expected:
            raise RuntimeError("The administrator group PSO is not effective")
        try:
            samdb.setpassword(
                expression, "Different-Pw2!", force_change_at_next_login=False
            )
        except ldb.LdbError as error:
            if "0000052D" not in str(error):
                raise
        else:
            raise RuntimeError(
                "The administrator PSO accepted a password shorter than 16"
            )
        samdb.setpassword(
            expression,
            "Molecule-Long-Admin-Password3!",
            force_change_at_next_login=False,
        )
    finally:
        samdb.delete(user.dn)


class PolicyChecks:
    """Check the fixture's lifecycle using native directory queries."""

    def __init__(self, samdb: Any) -> None:
        self.samdb = samdb
        self.ldb = importlib.import_module("ldb")
        self.base = str(samdb.domain_dn())
        self.policies = f"CN=Password Settings Container,CN=System,{self.base}"

    def read(self, dn: str) -> Any:
        """Read attributes relevant to role-owned state, or return None."""
        matches = self.samdb.search(
            base=self.base,
            expression=f"(distinguishedName={self.ldb.binary_encode(dn)})",
            attrs=ATTRIBUTES,
        )
        return matches[0] if matches else None

    def seed(self) -> None:
        """Install valid intervals that the role's integer inputs cannot express."""
        for dn, attributes in (
            (self.base, DOMAIN_INTERVALS),
            (f"CN=molecule-managed,{self.policies}", PSO_INTERVALS),
        ):
            message = self.ldb.Message(self.ldb.Dn(self.samdb, dn))
            for attribute, value in attributes.items():
                message[attribute] = self.ldb.MessageElement(
                    value, self.ldb.FLAG_MOD_REPLACE, attribute
                )
            self.samdb.modify(message)

    def intervals(self) -> None:
        """Assert unmanaged domain and existing PSO intervals retain exact ticks."""
        for dn, attributes in (
            (self.base, DOMAIN_INTERVALS),
            (f"CN=molecule-managed,{self.policies}", PSO_INTERVALS),
        ):
            record = self.read(dn)
            for attribute, value in attributes.items():
                expect(record, attribute, [value])

    def initial(self, *, seeded: bool = False) -> None:
        """Verify initial policies and check-mode preservation."""
        expect(self.read(self.base), "minPwdLength", ["12"])
        expect(
            self.read(f"CN=molecule-managed,{self.policies}"),
            "msDS-PSOAppliesTo",
            [f"CN=Domain Admins,CN=Users,{self.base}"],
        )
        if seeded:
            self.intervals()
        expect(
            self.read(f"CN=molecule-managed,{self.policies}"),
            "msDS-PasswordSettingsPrecedence",
            ["20"],
        )
        if self.read(f"CN=molecule-delete,{self.policies}") is None:
            raise RuntimeError("The policy scheduled for deletion is missing")
        if self.read(f"CN=molecule-inherited,{self.policies}") is not None:
            raise RuntimeError("Check mode created the inheritance test policy")

    def updated(self) -> None:
        """Verify assignment changes, deletion and exact inherited intervals."""
        self.intervals()
        managed = self.read(f"CN=moleculereader,CN=Users,{self.base}")
        expect(managed, "msDS-ResultantPSO", [f"CN=molecule-managed,{self.policies}"])
        if self.read(f"CN=molecule-delete,{self.policies}") is not None:
            raise RuntimeError("The deleted password policy remains")
        policy = self.read(f"CN=molecule-managed,{self.policies}")
        expect(policy, "msDS-MinimumPasswordLength", ["18"])
        expect(policy, "msDS-PasswordSettingsPrecedence", ["5"])
        expect(policy, "msDS-PSOAppliesTo", [str(managed.dn)])
        inherited = self.read(f"CN=molecule-inherited,{self.policies}")
        expect(inherited, "msDS-MinimumPasswordAge", [DOMAIN_INTERVALS["minPwdAge"]])
        expect(inherited, "msDS-LockoutDuration", [DOMAIN_INTERVALS["lockoutDuration"]])
        expect(
            inherited,
            "msDS-LockoutObservationWindow",
            [DOMAIN_INTERVALS["lockOutObservationWindow"]],
        )
        expect(inherited, "msDS-MinimumPasswordLength", ["13"])
        expect(self.read(self.base), "minPwdLength", ["13"])


def main() -> None:
    """Seed or verify role-managed state without printing credentials."""
    module = AnsibleModule(
        argument_spec={
            **connection_argument_spec(),
            "phase": {
                "type": "str",
                "required": True,
                "choices": ["initial", "seed", "seeded", "updated"],
            },
        }
    )
    checks = PolicyChecks(connect_samdb(module))
    phase = module.params["phase"]
    try:
        if phase == "seed":
            checks.seed()
        elif phase == "updated":
            checks.updated()
        else:
            checks.initial(seeded=phase == "seeded")
            if phase == "initial":
                verify_password_settings(checks.samdb)
                with tempfile.TemporaryDirectory(
                    prefix="samba-ad-dc-tickets-"
                ) as temporary:
                    cache = str(Path(temporary) / "ccache")
                    ticket(
                        module, "Administrator", module.params["bind_password"], cache
                    )
                    ticket(module, "moleculereader", "Molecule-Only-Reader1!", cache)
    except (checks.ldb.LdbError, RuntimeError, OSError) as error:
        module.fail_json(msg=f"Password policy verification failed: {error}")
    else:
        module.exit_json(changed=phase == "seed")


if __name__ == "__main__":
    main()
