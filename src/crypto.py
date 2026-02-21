"""Encryption utilities for credentials and tokens."""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import config


class CryptoManager:
    """Handle encryption/decryption of sensitive data."""
    
    def __init__(self):
        self.master_key = config.MASTER_KEY.encode()
        self.salt = b'AutoXMail_v2_2026'
    
    def _derive_key(self, user_id: int) -> bytes:
        """Derive user-specific encryption key."""
        # Combine master key with user_id for per-user encryption
        combined = self.master_key + str(user_id).encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(combined))
        return key
    
    def encrypt(self, data: bytes, user_id: int) -> bytes:
        """Encrypt data for specific user."""
        key = self._derive_key(user_id)
        f = Fernet(key)
        return f.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes, user_id: int) -> bytes:
        """Decrypt data for specific user."""
        key = self._derive_key(user_id)
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    
    def encrypt_credentials(self, credentials_json: str, user_id: int) -> bytes:
        """Encrypt Gmail credentials JSON."""
        return self.encrypt(credentials_json.encode(), user_id)
    
    def decrypt_credentials(self, encrypted_data: bytes, user_id: int) -> str:
        """Decrypt Gmail credentials JSON."""
        return self.decrypt(encrypted_data, user_id).decode()
    
    def encrypt_token(self, token_json: str, user_id: int) -> bytes:
        """Encrypt Gmail token JSON."""
        return self.encrypt(token_json.encode(), user_id)
    
    def decrypt_token(self, encrypted_data: bytes, user_id: int) -> str:
        """Decrypt Gmail token JSON."""
        return self.decrypt(encrypted_data, user_id).decode()


# Global crypto instance
crypto = CryptoManager()
