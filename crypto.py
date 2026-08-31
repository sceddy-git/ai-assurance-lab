"""
Encryption and decryption utilities for storing sensitive tokens.
Uses Fernet symmetric encryption with user email as contextual salt.
"""

import os
import logging
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
from base64 import urlsafe_b64encode
import hashlib

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom exception for encryption/decryption errors."""
    pass


def get_encryption_key():
    """
    Retrieve the Fernet encryption key from environment.
    
    Returns:
        bytes: The encryption key in Fernet format
        
    Raises:
        EncryptionError: If key is not configured or invalid
    """
    key_str = os.getenv('ENCRYPTION_KEY')
    
    if not key_str:
        raise EncryptionError(
            "ENCRYPTION_KEY not configured. "
            "Generate with: python3 -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    
    try:
        key = key_str.encode() if isinstance(key_str, str) else key_str
        # Validate that it's a valid Fernet key by attempting to create a cipher
        Fernet(key)
        return key
    except Exception as e:
        raise EncryptionError(f"Invalid ENCRYPTION_KEY format: {str(e)}")


def _derive_context_key(base_key: bytes, user_email: str) -> bytes:
    """
    Derive a user-specific encryption key using HMAC.
    This prevents tokens encrypted for one user from being decrypted by another.
    
    Args:
        base_key: The base Fernet key
        user_email: The user's email address (used as context)
        
    Returns:
        bytes: A derived Fernet key unique to this user
    """
    # Use HMAC-SHA256 to derive a context-specific key
    context_hash = hashlib.sha256(
        f"{user_email}:{base_key.decode()}".encode()
    ).digest()
    
    # Return first 32 bytes as base64 for Fernet
    derived_key = urlsafe_b64encode(context_hash)
    return derived_key


def encrypt_token(token: str, user_email: str) -> str:
    """
    Encrypt a token (API key) for storage.
    The encryption is user-specific, preventing token reuse across users.
    
    Args:
        token: The plaintext token/API key to encrypt
        user_email: The user's email address (used as context)
        
    Returns:
        str: Base64-encoded encrypted token
        
    Raises:
        EncryptionError: If encryption fails
    """
    if not token or not isinstance(token, str):
        raise EncryptionError("Token must be a non-empty string")
    
    if not user_email or not isinstance(user_email, str):
        raise EncryptionError("User email must be a non-empty string")
    
    try:
        base_key = get_encryption_key()
        context_key = _derive_context_key(base_key, user_email)
        cipher = Fernet(context_key)
        
        token_bytes = token.encode('utf-8')
        encrypted = cipher.encrypt(token_bytes)
        
        # Return as base64 string for safe storage
        return encrypted.decode('utf-8')
    
    except EncryptionError:
        raise
    except Exception as e:
        logger.error(f"Encryption failed for user {user_email}: {type(e).__name__}")
        raise EncryptionError(f"Failed to encrypt token: {type(e).__name__}")


def decrypt_token(encrypted_token: str, user_email: str) -> str:
    """
    Decrypt a stored token (API key).
    Will only succeed if the same user_email is provided.
    
    Args:
        encrypted_token: The encrypted token from storage
        user_email: The user's email address (must match encryption context)
        
    Returns:
        str: The decrypted plaintext token
        
    Raises:
        EncryptionError: If decryption fails or context doesn't match
    """
    if not encrypted_token or not isinstance(encrypted_token, str):
        raise EncryptionError("Encrypted token must be a non-empty string")
    
    if not user_email or not isinstance(user_email, str):
        raise EncryptionError("User email must be a non-empty string")
    
    try:
        base_key = get_encryption_key()
        context_key = _derive_context_key(base_key, user_email)
        cipher = Fernet(context_key)
        
        encrypted_bytes = encrypted_token.encode('utf-8')
        decrypted = cipher.decrypt(encrypted_bytes)
        
        return decrypted.decode('utf-8')
    
    except (InvalidToken, InvalidSignature):
        logger.error(f"Decryption failed - invalid token or wrong user context for {user_email}")
        raise EncryptionError(
            "Failed to decrypt token. Token may be invalid or user context mismatch."
        )
    except EncryptionError:
        raise
    except Exception as e:
        logger.error(f"Decryption failed for user {user_email}: {type(e).__name__}")
        raise EncryptionError(f"Failed to decrypt token: {type(e).__name__}")


def test_encryption():
    """
    Simple test to verify encryption/decryption works.
    Useful for debugging key configuration.
    """
    try:
        test_token = "test_api_key_12345"
        test_email = "test@example.com"
        
        encrypted = encrypt_token(test_token, test_email)
        decrypted = decrypt_token(encrypted, test_email)
        
        assert decrypted == test_token, "Decrypted token doesn't match original"
        print("✓ Encryption test passed")
        
        # Verify that different user can't decrypt
        try:
            decrypt_token(encrypted, "different@example.com")
            print("✗ Security test failed - different user could decrypt")
            return False
        except EncryptionError:
            print("✓ Security test passed - token isolation working")
            return True
    
    except Exception as e:
        print(f"✗ Encryption test failed: {e}")
        return False


if __name__ == "__main__":
    # For testing: set a test key in environment
    os.environ['ENCRYPTION_KEY'] = Fernet.generate_key().decode()
    test_encryption()
