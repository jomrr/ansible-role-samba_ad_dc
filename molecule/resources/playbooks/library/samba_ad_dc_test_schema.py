#!/usr/bin/python
"""Verify OpenSSH key storage and LDAP compatibility through Kerberos LDAP."""

DOCUMENTATION = r"""
module: samba_ad_dc_test_schema
short_description: Verify the SSH and LDAP compatibility schema on the test DC
description:
  - Writes and reads OpenSSH keys on a temporary user and deletes it afterwards.
  - Checks the LDAP compatibility attributes and their auxiliary class.
extends_documentation_fragment:
  - jomrr.samba.connection
author:
  - Jonas Mauer (@jomrr)
"""

EXAMPLES = r"""
- name: SAMBA_AD_DC | Verify SSH keys and LDAP compatibility schema
  samba_ad_dc_test_schema:
    server: dc1.ad.example.test
    bind_username: Administrator
    bind_password: "{{ samba_ad_dc_admin_password }}"
"""

RETURN = r"""{}"""

# Ansible requires module documentation before the normal import block.
# pylint: disable=wrong-import-position
import importlib
from typing import Any
from uuid import uuid4

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.jomrr.samba.plugins.module_utils.samba_conn import (
    connect_samdb,
    connection_argument_spec,
)

# pylint: enable=wrong-import-position


def verify_ldap_compatibility(directory: Any) -> None:
    """Check both LDAP compatibility attributes and their auxiliary class."""
    ldb = importlib.import_module("ldb")
    for name in ("entryUUID", "nsUniqueId"):
        entries = directory.search(
            base=directory.get_schema_basedn(),
            scope=ldb.SCOPE_ONELEVEL,
            expression=f"(&(objectClass=attributeSchema)(lDAPDisplayName={name}))",
            attrs=["lDAPDisplayName"],
        )
        if len(entries) != 1:
            raise RuntimeError(f"LDAP compatibility attribute is missing: {name}")
    classes = directory.search(
        base=directory.get_schema_basedn(),
        scope=ldb.SCOPE_ONELEVEL,
        expression="(&(objectClass=classSchema)(lDAPDisplayName=ldapCompatPerson))",
        attrs=["mayContain", "objectClassCategory"],
    )
    if len(classes) != 1:
        raise RuntimeError("LDAP compatibility class ldapCompatPerson is missing")
    attributes = {bytes(value).lower() for value in classes[0].get("mayContain", [])}
    if not {b"entryuuid", b"nsuniqueid"}.issubset(attributes):
        raise RuntimeError("ldapCompatPerson does not allow both LDAP compatibility attributes")
    if list(classes[0].get("objectClassCategory", [])) != [b"3"]:
        raise RuntimeError("ldapCompatPerson is not an auxiliary class")


def verify_ssh_keys(directory: Any) -> None:
    """Round-trip multiple OpenSSH keys on an ordinary user, then remove it."""
    ldb = importlib.import_module("ldb")
    account = f"molecule-{uuid4().hex[:10]}"
    user_dn = f"CN={account},CN=Users,{directory.domain_dn()}"
    keys = [
        b"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHRlc3Qta2V5LWZvci1tb2xlY3VsZS1vbmx5 first",
        b"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHRlc3Qta2V5LWZvci1tb2xlY3VsZS1vbmx5 second",
    ]
    directory.add(
        {
            "dn": user_dn,
            "objectClass": "user",
            "sAMAccountName": account,
            "userAccountControl": "514",
            "sshPublicKey": keys,
        }
    )
    try:
        stored = directory.search(
            base=user_dn, scope=ldb.SCOPE_BASE, attrs=["sshPublicKey"]
        )[0]
        if set(stored.get("sshPublicKey", [])) != set(keys):
            raise RuntimeError("OpenSSH public key round trip failed")
    finally:
        directory.delete(user_dn)


def main() -> None:
    """Run the schema checks without leaving a user fixture behind."""
    module = AnsibleModule(argument_spec=connection_argument_spec())
    ldb = importlib.import_module("ldb")
    try:
        directory = connect_samdb(module)
        verify_ldap_compatibility(directory)
        verify_ssh_keys(directory)
    except (ldb.LdbError, RuntimeError) as error:
        module.fail_json(msg=f"Schema extension verification failed: {error}")
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
