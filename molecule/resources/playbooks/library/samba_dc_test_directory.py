#!/usr/bin/python
"""Exercise reserved DNS names, Kerberos tickets and effective password rules."""

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
module: samba_dc_test_directory
short_description: Verify the domain security settings in the Molecule fixture
description:
  - Checks the reserved DNS names and refuses authenticated client updates.
  - Obtains and inspects AES Kerberos tickets.
  - Exercises the administrator PSO with a temporary user.
extends_documentation_fragment:
  - jomrr.samba.connection
author:
  - Jonas Mauer (@jomrr)
"""

EXAMPLES = r"""
- name: SAMBA_DC | Verify DNS reservations Kerberos and password rules
  samba_dc_test_directory:
    server: dc1.ad.example.test
    realm: AD.EXAMPLE.TEST
    bind_username: Administrator
    bind_password: "{{ samba_dc_admin_password }}"
"""


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


def verify_dns(module: Any, cache: str) -> None:
    """Verify reservations and attempt changes with an ordinary user's ticket."""
    domain = module.params["realm"].lower()
    for name in ("wpad", "isatap"):
        _, records, _ = module.run_command(
            ["dig", "@127.0.0.1", f"{name}.{domain}", "A", "+short"], check_rc=True
        )
        if records.strip() != "127.0.0.1":
            raise RuntimeError(f"DNS name {name} is not reserved at 127.0.0.1")
        status, output, error = module.run_command(
            ["nsupdate", "-g", "-v"],
            data=(
                f"server {module.params['server']}\nzone {domain}\n"
                f"update add {name}.{domain} 60 A 192.0.2.123\nsend\n"
            ),
            environ_update={"KRB5CCNAME": f"FILE:{cache}"},
        )
        if status == 0 or "REFUSED" not in output + error:
            raise RuntimeError(
                f"Reserved DNS name {name} did not refuse the client update"
            )


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


def main() -> None:
    """Run functional checks using only disposable credentials and objects."""
    module = AnsibleModule(argument_spec=connection_argument_spec())
    samdb = connect_samdb(module)
    ldb = importlib.import_module("ldb")
    try:
        verify_password_settings(samdb)
        with tempfile.TemporaryDirectory(prefix="samba-dc-tickets-") as temporary:
            cache = str(Path(temporary) / "ccache")
            ticket(module, "Administrator", module.params["bind_password"], cache)
            ticket(module, "moleculereader", "Molecule-Only-Reader1!", cache)
            verify_dns(module, cache)
    except (ldb.LdbError, RuntimeError, OSError) as error:
        module.fail_json(msg=f"Domain security verification failed: {error}")
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
