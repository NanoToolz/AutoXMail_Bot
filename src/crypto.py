"""Encryption utilities using Fernet AES-128."""
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import config


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2.
    
    Args:
        password: Master password
        salt: 16-byte salt
        
    Returns:
        32-byte key for Fernet
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,  # 100k iterations for security
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def generate_salt() -> bytes:
    """Generate random 16-byte salt."""
    return os.urandom(16)


def encrypt(data: bytes, password: str, salt: bytes) -> bytes:
    """Encrypt data using Fernet AES-128.
    
    Args:
        data: Data to encrypt
        password: Master password
        salt: 16-byte salt
        
    Returns:
        Encrypted data
    """
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.encrypt(data)


def decrypt(encrypted_data: bytes, password: str, salt: bytes) -> bytes:
    """Decrypt data using Fernet AES-128.
    
    Args:
        encrypted_data: Encrypted data
        password: Master password
        salt: 16-byte salt
        
    Returns:
        Decrypted data
    """
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(encrypted_data)


def encrypt_credentials(credentials_json: str, user_id: int) -> tuple[bytes, bytes]:
    """Encrypt Gmail credentials.
    
    Args:
        credentials_json: JSON string of credentials
        user_id: User ID for salt generation
        
    Returns:
        Tuple of (encrypted_data, salt)
    """
    # Generate per-user salt
    salt = hashlib.sha256(f"{user_id}{config.MASTER_KEY}".encode()).digest()[:16]
    
    # Encrypt
    encrypted = encrypt(credentials_json.encode(), config.MASTER_KEY, salt)
    
    return encrypted, salt


def decrypt_credentials(encrypted_data: bytes, user_id: int) -> str:
    """Decrypt Gmail credentials.
    
    Args:
        encrypted_data: Encrypted credentials
        user_id: User ID for salt generation
        
    Returns:
        Decrypted JSON string
    """
    # Regenerate salt
    salt = hashlib.sha256(f"{user_id}{config.MASTER_KEY}".encode()).digest()[:16]
    
    # Decrypt
    decrypted = decrypt(encrypted_data, config.MASTER_KEY, salt)
    
    return decrypted.decode()


def encrypt_token(token_json: str, user_id: int) -> bytes:
    """Encrypt OAuth token.
    
    Args:
        token_json: JSON string of token
        user_id: User ID for salt generation
        
    Returns:
        Encrypted token
    """
    salt = hashlib.sha256(f"{user_id}{config.MASTER_KEY}token".encode()).digest()[:16]
    return encrypt(token_json.encode(), config.MASTER_KEY, salt)


def decrypt_token(encrypted_token: bytes, user_id: int) -> str:
    """Decrypt OAuth token.
    
    Args:
        encrypted_token: Encrypted token
        user_id: User ID for salt generation
        
    Returns:
        Decrypted JSON string
    """
    salt = hashlib.sha256(f"{user_id}{config.MASTER_KEY}token".encode()).digest()[:16]
    return decrypt(encrypted_token, config.MASTER_KEY, salt).decode()
