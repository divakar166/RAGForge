"""Tests for security / auth utilities."""

from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hashing():
    hashed = hash_password("testpass123")
    assert verify_password("testpass123", hashed)
    assert not verify_password("wrongpass", hashed)


def test_access_token_creation_and_verification():
    token = create_access_token("user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_invalid_token_returns_empty():
    payload = decode_token("invalid.token.here")
    assert payload == {}
