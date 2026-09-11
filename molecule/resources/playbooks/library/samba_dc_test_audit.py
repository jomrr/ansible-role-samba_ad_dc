#!/usr/bin/python
"""Verify the audit events produced by the Molecule domain controller fixture."""

import importlib
import json
import re
from pathlib import Path

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
module: samba_dc_test_audit
short_description: Verify Samba DC audit coverage
description:
  - Checks share operations, Windows ACLs, directory changes and authentication.
  - Reads the Samba logs after the Molecule playbook generates the test events.
author:
  - Jonas Mauer (@jomrr)
"""

EXAMPLES = r"""
- name: SAMBA_DC | Verify share directory and authentication audit coverage
  become: true
  become_user: root
  samba_dc_test_audit:
"""

LOG_DIR = Path("/var/log/samba")


def verify_shares() -> None:
    """Check successful operations, denied writes and Windows ACL descriptors."""
    audit = (LOG_DIR / "sysvol_audit.log").read_text(encoding="utf-8")
    for share in ("sysvol", "netlogon"):
        for operation in (
            "pwrite(?:_send|_recv)?|write",
            "pread(?:_send|_recv)?|read|sendfile",
            "renameat",
            "unlinkat",
        ):
            pattern = rf"VOLUME={share}\|(?:{operation})\|ok\|[^\n]*molecule-audit"
            if not re.search(pattern, audit):
                raise RuntimeError(f"Missing successful {operation} audit for {share}")
        if not re.search(
            rf"PROTOCOL=SMB3_11\|VOLUME={share}\|create_file\|ok\|", audit
        ):
            raise RuntimeError(f"Missing SMB 3.1.1 file-open audit for {share}")
        denied = rf"VOLUME={share}\|create_file\|fail[^|]*\|[^\n]*molecule-denied"
        if not re.search(denied, audit):
            raise RuntimeError(f"Missing denied file creation audit for {share}")
        acl = rf"VOLUME={share}\|fset_nt_acl\|ok\|[^\n]*molecule-acl.txt \[[^\n]*D:"
        if not re.search(acl, audit):
            raise RuntimeError(f"Missing Windows ACL change and SDDL for {share}")


def verify_directory() -> None:
    """Check directory, password, group and transaction audit destinations."""
    expected = {
        "dsdb_json_audit.log": ("moleculereader",),
        "dsdb_password_json_audit.log": ("moleculereader",),
        "dsdb_group_json_audit.log": ("molecule-audit-group", "moleculereader"),
        "dsdb_transaction_json_audit.log": ("commit",),
        "dns.log": ("Update not allowed for unsigned packet",),
    }
    for filename, markers in expected.items():
        content = (LOG_DIR / filename).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in content:
                raise RuntimeError(f"Missing {marker} audit in {filename}")


def verify_authentication() -> None:
    """Check accepted, rejected, anonymous and Kerberos authentication events."""
    content = (LOG_DIR / "auth_json_audit.log").read_text(encoding="utf-8")
    events = [
        json.loads(line)
        for line in content.splitlines()
        if line.lstrip().startswith("{")
    ]
    if not any(
        event.get("Authorization", {}).get("account") == "Administrator"
        for event in events
    ):
        raise RuntimeError("Missing successful Administrator authorization audit")
    authentication = [event.get("Authentication", {}) for event in events]
    if not any(
        event.get("clientAccount") == "moleculereader"
        and event.get("status") == "NT_STATUS_WRONG_PASSWORD"
        for event in authentication
    ):
        raise RuntimeError("Missing failed password authentication audit")
    if not any(event.get("clientAccount") == "" for event in authentication):
        raise RuntimeError("Missing anonymous authentication audit")
    if not importlib.import_module("samba").is_heimdal_built():
        content = (LOG_DIR / "mit_kdc.log").read_text(encoding="utf-8")
    if "molecule-kdc-missing" not in content:
        raise RuntimeError("Missing rejected Kerberos principal audit")


def main() -> None:
    """Report missing audit events without returning log contents."""
    module = AnsibleModule(argument_spec={}, supports_check_mode=True)
    try:
        verify_shares()
        verify_directory()
        verify_authentication()
    except (OSError, RuntimeError, ValueError) as error:
        module.fail_json(msg=f"Samba audit verification failed: {error}")
    else:
        module.exit_json(changed=False)


if __name__ == "__main__":
    main()
