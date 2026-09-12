# Copyright: (c) 2026, Jonas Mauer
# SPDX-License-Identifier: MIT
"""Shared password-policy option documentation."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class ModuleDocFragment:
    """Password and lockout settings."""

    DOCUMENTATION: ClassVar[str] = r"""
options:
  settings:
    description:
    - Password and lockout settings to manage.
    - Unspecified settings remain unchanged.
    type: dict
    default: {}
    suboptions:
      minimum_length:
        type: int
        description: Minimum password length in characters.
      history_length:
        type: int
        description: Number of previous passwords that cannot be reused.
      minimum_age_days:
        type: int
        description: Minimum password age in days; 0 permits immediate changes.
      maximum_age_days:
        type: int
        description: Maximum password age in days; 0 disables expiration.
      lockout_threshold:
        type: int
        description: Failed sign-ins before account lockout; 0 disables lockout.
      lockout_duration_minutes:
        type: int
        description: Account lockout duration in minutes; 0 requires administrator
          unlock.
      lockout_window_minutes:
        type: int
        description: Minutes before the failed sign-in counter is reset.
      complexity:
        type: bool
        description: Require password complexity.
      reversible_encryption:
        type: bool
        description: Store passwords using reversible encryption.
"""
