#!/usr/bin/python
# Copyright: (c) 2026, Jonas Mauer
# SPDX-License-Identifier: MIT
"""Manage the domain password policy."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.samba_dc_password_policy import (
    reconcile_domain,
    run_module,
    settings_argument_spec,
)

from ansible_collections.jomrr.samba.plugins.module_utils.samba_conn import (
    connection_argument_spec,
)

DOCUMENTATION = r"""
module: samba_dc_password_policy
short_description: Manage the domain password policy
extends_documentation_fragment:
- jomrr.samba.connection
- samba_dc_password_policy
description:
- Manage the domain password policy through the native Samba LDAP bindings.
- Supports idempotent updates and check mode.
author:
- Jonas Mauer (@jomrr)
requirements:
- The Samba Python bindings must be installed on the execution host.
notes:
- Other bits in the domain password-properties attribute are preserved.
"""

EXAMPLES = r"""
- name: Manage the domain password policy
  samba_dc_password_policy:
    server: dc1.ad.example.com
    realm: AD.EXAMPLE.COM
    bind_username: Administrator
    bind_password: '{{ vault_samba_password }}'
    settings:
      minimum_length: 12
      complexity: true
      reversible_encryption: false
"""

RETURN = r"""
dn:
  description: Distinguished name of the managed policy.
  returned: success
  type: str
settings:
  description: Resulting password settings.
  returned: when the policy is present
  type: dict
"""


def main() -> None:
    """Reconcile the policy using the collection's authenticated connection."""
    arguments = {
        **connection_argument_spec(),
        "settings": {
            "type": "dict",
            "default": {},
            "options": settings_argument_spec(),
        },
    }
    module = AnsibleModule(argument_spec=arguments, supports_check_mode=True)
    run_module(module, reconcile_domain)


if __name__ == "__main__":
    main()
