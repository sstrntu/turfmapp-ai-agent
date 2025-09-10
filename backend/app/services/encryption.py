"""
Encryption Service for Sensitive Data

Provides AES encryption for sensitive data like OAuth tokens.
Uses environment-specific encryption keys.
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with key from environment."""
        try:
            # Get encryption key from environment
            encryption_key = os.getenv('ENCRYPTION_KEY')
            
            if not encryption_key:
                # Generate a key for development (NOT for production!)
                logger.warning("No ENCRYPTION_KEY found in environment. Generating temporary key for development.")
                encryption_key = Fernet.generate_key().decode()
                logger.warning(f"Generated temporary encryption key: {encryption_key}")
                logger.warning("⚠️  Set ENCRYPTION_KEY in production environment!")
            
            # If key is not in proper format, derive it
            if len(encryption_key) != 44 or not encryption_key.endswith('='):
                # Derive key from password/string
                password = encryption_key.encode()
                salt = b'turfmapp_salt_2024'  # Use a proper random salt in production
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                encryption_key = key.decode()
            
            self._fernet = Fernet(encryption_key.encode())
            logger.info("Encryption service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise RuntimeError(f"Encryption initialization failed: {e}")
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64-encoded encrypted data, or None if encryption fails
        """
        if not plaintext:
            return None
            
        try:
            plaintext_bytes = plaintext.encode('utf-8')
            encrypted_bytes = self._fernet.encrypt(plaintext_bytes)
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt encrypted data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted plaintext string, or None if decryption fails
        """
        if not encrypted_data:
            return None
            
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            plaintext = decrypted_bytes.decode('utf-8')
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_token(self, token: str) -> Optional[str]:
        """
        Encrypt an OAuth token.
        
        Args:
            token: The OAuth token to encrypt
            
        Returns:
            Encrypted token or None if encryption fails
        """
        if not token:
            return None
        return self.encrypt(token)
    
    def decrypt_token(self, encrypted_token: str) -> Optional[str]:
        """
        Decrypt an OAuth token.
        
        Args:
            encrypted_token: The encrypted token
            
        Returns:
            Decrypted token or None if decryption fails
        """
        if not encrypted_token:
            return None
        return self.decrypt(encrypted_token)
    
    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted (basic heuristic).
        
        Args:
            data: Data to check
            
        Returns:
            True if data appears encrypted, False otherwise
        """
        if not data:
            return False
            
        try:
            # Encrypted data should be base64 and not look like plaintext
            base64.b64decode(data)
            # If it decodes and doesn't contain typical token patterns, likely encrypted
            return not (data.startswith('ya29.') or data.startswith('1//') or 'access_token' in data.lower())
        except:
            return False


# Global encryption service instance
encryption_service = EncryptionService()


def generate_encryption_key() -> str:
    """Generate a new encryption key for production use."""
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    # Utility to generate encryption key for production
    key = generate_encryption_key()
    print(f"Generated encryption key for production:")
    print(f"ENCRYPTION_KEY={key}")
    print("\n⚠️  Store this key securely and set it in your production environment!")
    print("⚠️  Keep this key secret and backed up - losing it makes data unrecoverable!")