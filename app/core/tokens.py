import hashlib
import secrets


def generate_token() -> str:
    """Generate a cryptographically secure URL-safe random token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token. Only hashes are stored in the DB."""
    return hashlib.sha256(token.encode()).hexdigest()
