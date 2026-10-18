"""Salted, memory-hard scrypt using the Python standard library."""
import hashlib
import hmac
import secrets
from threading import BoundedSemaphore

SCRYPT_N = 2 ** 17
SCRYPT_R = 8
SCRYPT_P = 1
_hash_slots = BoundedSemaphore(2)


class PasswordHashBusy(Exception):
    pass


def _derive(password: str, salt: bytes) -> bytes:
    if not _hash_slots.acquire(blocking=False):
        raise PasswordHashBusy("Authentication is busy. Please try again.")
    try:
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N,
                              r=SCRYPT_R, p=SCRYPT_P, maxmem=256 * 1024 * 1024, dklen=32)
    finally:
        _hash_slots.release()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${_derive(password, salt).hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = encoded.split("$")
        if (scheme, int(n), int(r), int(p)) != ("scrypt", SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        salt_bytes, expected_bytes = bytes.fromhex(salt), bytes.fromhex(expected)
        if len(salt_bytes) != 16 or len(expected_bytes) != 32:
            return False
        return hmac.compare_digest(_derive(password, salt_bytes), expected_bytes)
    except (ValueError, TypeError):
        return False


# Unknown accounts perform the same KDF work as known accounts.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))
