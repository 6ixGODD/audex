from __future__ import annotations

import argon2

argon2_hasher = argon2.PasswordHasher()


def argon2_hash(v: str, /) -> str:
    """Hash a string using Argon2.

    Args:
        v (str): The string to hash.

    Returns:
        str: The Argon2 hashed string.
    """
    return argon2_hasher.hash(v)


def argon2_verify(v: str, /, hashed: str) -> bool:
    """Verify a string against an Argon2 hash.

    Args:
        v (str): The string to verify.
        hashed (str): The hashed string.

    Returns:
        bool: True if the string matches the hash, False otherwise.
    """
    try:
        return argon2_hasher.verify(hashed, v)
    except argon2.exceptions.VerifyMismatchError:
        return False
