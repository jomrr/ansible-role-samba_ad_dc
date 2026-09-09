#!/usr/bin/python
"""Verify LAPS attribute storage and confidential reads through Kerberos LDAP."""

import importlib
import json
from typing import Any

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
module: samba_dc_test_laps
short_description: Verify the Windows LAPS schema on the test DC
description:
  - Writes and reads the LAPS attributes on a temporary computer object.
  - Checks that the ordinary test account cannot read password attributes.
  - Deletes the temporary computer object after verification.
options:
  server:
    description: Domain controller DNS name.
    type: str
    required: true
  password:
    description: Password of the test domain Administrator.
    type: str
    required: true
author:
  - Jonas Mauer (@jomrr)
"""

EXAMPLES = r"""
- name: SAMBA_DC | Verify Windows LAPS password storage and access restrictions
  samba_dc_test_laps:
    server: dc1.ad.example.test
    password: "{{ samba_dc_admin_password }}"
"""


def connect(server: str, username: str, password: str) -> Any:
    """Open the test directory with Kerberos authentication."""
    credentials_module = importlib.import_module("samba.credentials")
    parameters = importlib.import_module("samba.param").LoadParm()
    parameters.load_default()
    credentials = credentials_module.Credentials()
    credentials.guess(parameters)
    credentials.set_username(username)
    credentials.set_password(password)
    credentials.set_kerberos_state(credentials_module.MUST_USE_KERBEROS)
    return importlib.import_module("samba.samdb").SamDB(
        url=f"ldap://{server}", credentials=credentials, lp=parameters
    )


def verify(server: str, password: str) -> None:
    """Round-trip the schema attributes as Administrator and an ordinary reader."""
    ldb = importlib.import_module("ldb")
    administrator = connect(server, "Administrator", password)
    reader = connect(server, "moleculereader", "Molecule-Only-Reader1!")
    computer_dn = f"CN=molecule-laps,CN=Computers,{administrator.domain_dn()}"
    expiration = b"134400000000000000"
    values = {
        "msLAPS-PasswordExpirationTime": [expiration],
        "msLAPS-Password": [
            json.dumps(
                {
                    "n": "Administrator",
                    "t": "1dd7e5398090000",
                    "p": "Molecule-LAPS-Secret-Only1!",
                }
            ).encode()
        ],
        "msLAPS-EncryptedPassword": [b"schema-test-current"],
        "msLAPS-EncryptedPasswordHistory": [b"schema-test-old-1", b"schema-test-old-2"],
        "msLAPS-EncryptedDSRMPassword": [b"schema-test-dsrm"],
        "msLAPS-EncryptedDSRMPasswordHistory": [
            b"schema-test-dsrm-1",
            b"schema-test-dsrm-2",
        ],
        "msLAPS-CurrentPasswordVersion": [bytes(range(16))],
    }
    administrator.add(
        {
            "dn": computer_dn,
            "objectClass": "computer",
            "sAMAccountName": "molecule-laps$",
            "userAccountControl": "4096",
            **values,
        }
    )
    try:
        stored = administrator.search(
            base=computer_dn, scope=ldb.SCOPE_BASE, attrs=list(values)
        )[0]
        for attribute, expected in values.items():
            if set(stored.get(attribute, [])) != set(expected):
                raise RuntimeError(f"LAPS attribute round trip failed: {attribute}")
        visible = reader.search(
            base=computer_dn, scope=ldb.SCOPE_BASE, attrs=list(values)
        )[0]
        if list(visible.get("msLAPS-PasswordExpirationTime", [])) != [expiration]:
            raise RuntimeError("Ordinary reader cannot read LAPS expiration time")
        for attribute in values:
            if attribute != "msLAPS-PasswordExpirationTime" and attribute in visible:
                raise RuntimeError(f"Ordinary reader can read confidential {attribute}")
    finally:
        administrator.delete(computer_dn)


def main() -> None:
    """Run the functional check, leaving no computer fixture behind."""
    module = AnsibleModule(
        argument_spec={
            "server": {"type": "str", "required": True},
            "password": {"type": "str", "required": True, "no_log": True},
        }
    )
    ldb = importlib.import_module("ldb")
    try:
        verify(**module.params)
    except (ldb.LdbError, RuntimeError) as error:
        module.fail_json(msg=f"Windows LAPS verification failed: {error}")
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
