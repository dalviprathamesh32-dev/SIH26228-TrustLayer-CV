import hashlib
from pathlib import Path
from typing import Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.core.config import PRIVATE_KEY_PATH, PUBLIC_KEY_PATH
from app.core.canonical import canonical_bytes

def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 digest of raw bytes as lower-case hex."""
    return hashlib.sha256(data).hexdigest()

def sha256_canonical(obj: Any) -> str:
    """Compute SHA-256 digest of canonicalized JSON representation."""
    return sha256_bytes(canonical_bytes(obj))

def sha256_file(filepath: Path | str) -> str:
    """Compute SHA-256 digest of file contents on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

class Ed25519KeyManager:
    _instance = None

    def __init__(self):
        self.private_key: ed25519.Ed25519PrivateKey
        self.public_key: ed25519.Ed25519PublicKey
        self._load_or_generate_keys()

    @classmethod
    def get_instance(cls) -> "Ed25519KeyManager":
        if cls._instance is None:
            cls._instance = Ed25519KeyManager()
        return cls._instance

    def _load_or_generate_keys(self):
        if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
            with open(PRIVATE_KEY_PATH, "rb") as f:
                self.private_key = serialization.load_pem_private_key(f.read(), password=None)
            with open(PUBLIC_KEY_PATH, "rb") as f:
                self.public_key = serialization.load_pem_public_key(f.read())
        else:
            # Generate new pair once inside ./secrets
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            self.public_key = self.private_key.public_key()

            pem_private = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            pem_public = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            with open(PRIVATE_KEY_PATH, "wb") as f:
                f.write(pem_private)
            with open(PUBLIC_KEY_PATH, "wb") as f:
                f.write(pem_public)

    def get_public_key_raw(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def get_public_key_hex(self) -> str:
        return self.get_public_key_raw().hex()

    def sign_bytes(self, message: bytes) -> str:
        """Sign raw message bytes using Ed25519 and return hex signature."""
        sig = self.private_key.sign(message)
        return sig.hex()

    def sign_canonical(self, obj: Any) -> str:
        """Sign canonical JSON bytes of an object."""
        return self.sign_bytes(canonical_bytes(obj))

    def verify_bytes(self, message: bytes, signature_hex: str, public_key_hex: str | None = None) -> bool:
        """Verify Ed25519 signature against provided or current public key."""
        try:
            sig_bytes = bytes.fromhex(signature_hex)
            if public_key_hex:
                pub_bytes = bytes.fromhex(public_key_hex)
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            else:
                pub_key = self.public_key
            pub_key.verify(sig_bytes, message)
            return True
        except Exception:
            return False

    def verify_canonical(self, obj: Any, signature_hex: str, public_key_hex: str | None = None) -> bool:
        """Verify canonical JSON representation of object."""
        return self.verify_bytes(canonical_bytes(obj), signature_hex, public_key_hex)

# Global helpers
def get_key_manager() -> Ed25519KeyManager:
    return Ed25519KeyManager.get_instance()

def sign_canonical_payload(payload: Any) -> str:
    return get_key_manager().sign_canonical(payload)

def verify_canonical_payload(payload: Any, signature_hex: str, public_key_hex: str | None = None) -> bool:
    return get_key_manager().verify_canonical(payload, signature_hex, public_key_hex)
