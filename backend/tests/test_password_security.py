import pytest

from app.core.password_security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)


def test_password_hashing():
    password = "BankKey-Test-Password-2026!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed)


def test_wrong_password_is_rejected():
    hashed = hash_password("CorrectPassword123!")

    assert not verify_password(
        "WrongPassword123!",
        hashed,
    )


def test_salt_produces_unique_hashes():
    password = "BankKey-Unique-Salt-Test!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_invalid_hash_is_rejected():
    assert not verify_password(
        "Password123!",
        "invalid-hash",
    )


def test_password_does_not_need_rehash():
    hashed = hash_password("BankKey-Rehash-Test!")

    assert not password_needs_rehash(hashed)


def test_empty_password_is_rejected():
    with pytest.raises(ValueError):
        hash_password("")
