#!/usr/bin/python
# Copyright: (c) 2026, Jonas Mauer
# SPDX-License-Identifier: MIT
"""Manage a fine-grained password settings object."""

from __future__ import annotations

DOCUMENTATION = r"""
module: samba_dc_password_settings
short_description: Manage a fine-grained password settings object
extends_documentation_fragment: [jomrr.samba.connection, samba_dc_password_policy]
description:
- Manage a fine-grained password settings object through the native Samba LDAP bindings.
author: [Jonas Mauer (@jomrr)]
requirements:
- Samba Python bindings on the execution host.
attributes:
  check_mode:
    support: full
    description: Predict changes without modifying the directory.
options:
  name:
    description: PSO name within the Password Settings Container.
    type: str
    required: true
  precedence:
    description: Policy priority; smaller values take precedence. Required when O(state=present).
    type: int
  applies_to:
    description:
    - Exact set of users or global security groups assigned to the PSO.
    - Accepts account names or distinguished names. An empty list removes all assignments.
    type: list
    elements: str
    default: []
  state:
    description: Whether the PSO exists.
    type: str
    choices:
    - present
    - absent
    default: present
notes:
- When creating a PSO, unspecified settings are copied from the current domain policy.
- On updates, unspecified settings keep their existing PSO values.
- A PSO applies to users and global security groups, not to organizational units.
"""

EXAMPLES = r"""
- name: Manage a fine-grained password settings object
  samba_dc_password_settings:
    server: dc1.ad.example.com
    realm: AD.EXAMPLE.COM
    bind_username: Administrator
    bind_password: '{{ vault_samba_password }}'
    name: domain_admins
    precedence: 10
    applies_to:
    - Domain Admins
    settings:
      minimum_length: 16
      complexity: true
      reversible_encryption: false
"""

RETURN = r"""
dn:
  description: Distinguished name of the password settings object.
  returned: success
  type: str
settings:
  description: Password and lockout values of the PSO.
  returned: when state is present
  type: dict
state:
  description: Whether the PSO exists.
  returned: success
  type: str
precedence:
  description: Resulting policy priority.
  returned: when present
  type: int
applies_to:
  description: Distinguished names assigned to the PSO.
  returned: when present
  type: list
  elements: str
"""


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.samba_dc_password_policy import (
    reconcile_pso,
    run_module,
    settings_argument_spec,
)
from ansible_collections.jomrr.samba.plugins.module_utils.samba_conn import (
    connection_argument_spec,
)


def main() -> None:
    """Reconcile the policy using the collection's authenticated connection."""
    arguments = {
        **connection_argument_spec(),
        "name": {"type": "str", "required": True},
        "precedence": {"type": "int"},
        "applies_to": {"type": "list", "elements": "str", "default": []},
        "state": {
            "type": "str",
            "choices": ["present", "absent"],
            "default": "present",
        },
        "settings": {
            "type": "dict",
            "default": {},
            "options": settings_argument_spec(),
        },
    }
    module = AnsibleModule(
        argument_spec=arguments,
        supports_check_mode=True,
        required_if=[("state", "present", ["precedence"])],
    )
    run_module(module, reconcile_pso)


if __name__ == "__main__":
    main()
