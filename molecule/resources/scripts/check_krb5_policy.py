"""Compare the system libkrb5 enctype list with the distribution's active policy."""

import ctypes
import os
import re
from pathlib import Path


def permitted_enctypes() -> list[int]:
    """Read the ordered list the MIT Kerberos client library permits."""
    lib = ctypes.CDLL("libkrb5.so.3")
    context = ctypes.c_void_p()
    enctypes = ctypes.POINTER(ctypes.c_int32)()
    code = lib.krb5_init_context(ctypes.byref(context))
    if code:
        raise RuntimeError(f"krb5_init_context returned {code}")
    try:
        code = lib.krb5_get_permitted_enctypes(context, ctypes.byref(enctypes))
        if code:
            raise RuntimeError(f"krb5_get_permitted_enctypes returned {code}")
        try:
            result: list[int] = []
            while enctype := enctypes[len(result)]:
                result.append(enctype)
            return result
        finally:
            lib.krb5_free_enctypes(context, enctypes)
    finally:
        lib.krb5_free_context(context)


def main() -> None:
    """Use a fresh Kerberos context for each configuration."""
    policy = Path("/etc/krb5.conf.d/crypto-policies")
    settings = policy.read_text(encoding="utf-8")
    if not re.search(r"^\s*permitted_enctypes\s*=\s*\S", settings, re.MULTILINE):
        raise ValueError(f"No permitted_enctypes setting in {policy}")
    os.environ.pop("KRB5_CONFIG", None)
    actual = permitted_enctypes()
    os.environ["KRB5_CONFIG"] = str(policy)
    expected = permitted_enctypes()
    if actual != expected:
        raise ValueError(f"System permitted_enctypes {actual} differ from policy {expected}")


if __name__ == "__main__":
    main()
