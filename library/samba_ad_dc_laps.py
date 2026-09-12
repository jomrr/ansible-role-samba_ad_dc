#!/usr/bin/python
"""Prepare the Windows LAPS schema through Samba's local database bindings."""

from __future__ import annotations

import importlib
from typing import Any
from uuid import UUID

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
module: samba_ad_dc_laps
short_description: Prepare the Windows LAPS schema on a Samba AD DC
description:
  - Creates and reconciles the Windows LAPS attributes and encrypted-password property set.
  - Adds the attributes to the computer class without removing existing attributes.
  - Runs locally as root on the schema master using the installed Samba Python bindings.
  - Schema extensions persist permanently; OU permissions and client GPOs are managed separately.
options:
  configfile:
    description: Path to the domain controller configuration.
    type: path
    required: true
attributes:
  check_mode:
    support: full
author:
  - Jonas Mauer (@jomrr)
"""

EXAMPLES = r"""
- name: SAMBA_AD_DC | Prepare the Windows LAPS schema
  samba_ad_dc_laps:
    configfile: /etc/samba/smb.conf
"""

RETURN = r"""
changed:
  description: Whether the directory schema changed or would change in check mode.
  type: bool
  returned: always
"""

PROPERTY_SET = "f3531ec6-6330-4f8e-8d39-7a671fbac605"
ATTRIBUTES = (
    ("PasswordExpirationTime", "2.5.5.16", "65", "TRUE", "0"),
    ("Password", "2.5.5.5", "19", "TRUE", "904"),
    ("EncryptedPassword", "2.5.5.10", "4", "TRUE", "904"),
    ("EncryptedPasswordHistory", "2.5.5.10", "4", "FALSE", "904"),
    ("EncryptedDSRMPassword", "2.5.5.10", "4", "TRUE", "904"),
    ("EncryptedDSRMPasswordHistory", "2.5.5.10", "4", "FALSE", "904"),
    ("CurrentPasswordVersion", "2.5.5.10", "4", "TRUE", "904"),
)


def attribute_values(index: int, definition: tuple[str, ...]) -> dict[str, bytes]:
    """Describe the interoperable attribute syntax and password protection flags."""
    suffix, syntax, om_syntax, single, flags = definition
    values = {
        "ldapDisplayName": f"msLAPS-{suffix}".encode(),
        "attributeId": f"1.2.840.113556.1.6.44.1.{index}".encode(),
        "attributeSyntax": syntax.encode(),
        "oMSyntax": om_syntax.encode(),
        "isSingleValued": single.encode(),
        "systemOnly": b"FALSE",
        "searchFlags": flags.encode(),
        "isMemberOfPartialAttributeSet": b"FALSE",
    }
    if index >= 3:
        values["attributeSecurityGUID"] = UUID(PROPERTY_SET).bytes_le
    if suffix == "CurrentPasswordVersion":
        values.update(rangeLower=b"16", rangeUpper=b"16")
    return values


def entry_change(
    database: Any, base: Any, expression: str, entry: dict[str, Any]
) -> tuple[str, Any] | None:
    """Build a native add or modification for one desired directory entry."""
    ldb = importlib.import_module("ldb")
    values = {
        name: value
        for name, value in entry.items()
        if name not in {"dn", "objectClass"}
    }
    entries = database.search(
        base=base, scope=ldb.SCOPE_ONELEVEL, expression=expression, attrs=list(values)
    )
    if not entries:
        return "add", entry
    if len(entries) != 1:
        raise ValueError(f"Ambiguous Windows LAPS schema entry: {expression}")
    current = entries[0]
    message = ldb.Message()
    message.dn = current.dn
    for name, value in values.items():
        if list(current.get(name, [])) != [value]:
            message[name] = ldb.MessageElement(value, ldb.FLAG_MOD_REPLACE, name)
    if len(message):
        return "modify", message
    return None


def apply_changes(database: Any, changes: list[tuple[str, Any]]) -> None:
    """Commit one schema phase through the database's native transaction API."""
    database.transaction_start()
    try:
        for operation, entry in changes:
            getattr(database, operation)(entry)
        database.transaction_commit()
    except Exception:
        database.transaction_cancel()
        raise


def schema_changes(database: Any) -> list[tuple[str, Any]]:
    """Plan the Windows LAPS attribute and property-set entries."""
    schema_dn = database.get_schema_basedn()
    changes = []
    for index, definition in enumerate(ATTRIBUTES, start=1):
        suffix = definition[0]
        change = entry_change(
            database,
            schema_dn,
            f"(ldapDisplayName=msLAPS-{suffix})",
            {
                "dn": f"CN=ms-LAPS-{suffix},{schema_dn}",
                "objectClass": "attributeSchema",
                **attribute_values(index, definition),
            },
        )
        if change is not None:
            changes.append(change)
    rights_dn = f"CN=Extended-Rights,{database.get_config_basedn()}"
    change = entry_change(
        database,
        rights_dn,
        f"(rightsGuid={PROPERTY_SET})",
        {
            "dn": f"CN=ms-LAPS-Encrypted-Password-Attributes,{rights_dn}",
            "objectClass": "controlAccessRight",
            "displayName": b"ms-LAPS-Encrypted-Password-Attributes",
            "rightsGuid": PROPERTY_SET.encode(),
            "validAccesses": b"48",
        },
    )
    if change is not None:
        changes.append(change)
    return changes


def computer_change(database: Any) -> Any:
    """Plan only the missing attributes on the existing computer class."""
    ldb = importlib.import_module("ldb")
    computer = database.search(
        base=database.get_schema_basedn(),
        scope=ldb.SCOPE_ONELEVEL,
        expression="(ldapDisplayName=computer)",
        attrs=["mayContain", "systemMayContain"],
    )[0]
    allowed = {
        bytes(value).lower()
        for field in ("mayContain", "systemMayContain")
        for value in computer.get(field, [])
    }
    missing = [
        f"msLAPS-{definition[0]}".encode()
        for definition in ATTRIBUTES
        if f"msLAPS-{definition[0]}".encode().lower() not in allowed
    ]
    if not missing:
        return None
    message = ldb.Message()
    message.dn = computer.dn
    message["mayContain"] = ldb.MessageElement(missing, ldb.FLAG_MOD_ADD, "mayContain")
    return message


def prepare_schema(configfile: str, check_mode: bool) -> bool:
    """Reconcile attributes before allowing their use on computer objects."""
    ldb = importlib.import_module("ldb")
    parameters = importlib.import_module("samba.param").LoadParm()
    parameters.load(configfile)
    parameters.set("dsdb:schema update allowed", "yes")
    database = importlib.import_module("samba.samdb").SamDB(
        url=parameters.private_path("sam.ldb"),
        lp=parameters,
        session_info=importlib.import_module("samba.auth").system_session(),
    )
    schema = database.search(
        base=database.get_schema_basedn(), scope=ldb.SCOPE_BASE, attrs=["fSMORoleOwner"]
    )[0]
    owner = ldb.Dn(database, schema["fSMORoleOwner"][0].decode())
    if owner != ldb.Dn(database, database.get_dsServiceName()):
        raise ValueError(
            "Windows LAPS schema changes must run on the schema FSMO owner"
        )
    changes = schema_changes(database)
    computer = computer_change(database)
    changed = bool(changes or computer is not None)
    if check_mode:
        return changed
    if changes:
        apply_changes(database, changes)
        database.set_schema_update_now()
    if computer is not None:
        apply_changes(database, [("modify", computer)])
    return changed


def main() -> None:
    """Execute the role-local Ansible module."""
    module = AnsibleModule(
        argument_spec={"configfile": {"type": "path", "required": True}},
        supports_check_mode=True,
    )
    try:
        ldb = importlib.import_module("ldb")
    except ImportError as error:
        module.fail_json(msg=f"The Samba LDB Python bindings are required: {error}")
        return
    try:
        changed = prepare_schema(module.params["configfile"], module.check_mode)
    except (ldb.LdbError, ImportError, OSError, RuntimeError, ValueError) as error:
        module.fail_json(msg=f"Windows LAPS schema preparation failed: {error}")
    else:
        module.exit_json(changed=changed)


if __name__ == "__main__":
    main()
