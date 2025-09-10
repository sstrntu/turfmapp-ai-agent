"""
Comprehensive tests for EncryptionService - Sensitive Data Encryption

This module provides complete test coverage for the EncryptionService
that handles AES encryption for OAuth tokens and other sensitive data.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
import os
import base64
from cryptography.fernet import Fernet

from app.services.encryption import EncryptionService, generate_encryption_key


class TestEncryptionServiceInitialization:
    """Test encryption service initialization scenarios."""
    
    def test_init_with_valid_fernet_key(self):
        """Test initialization with a valid Fernet key."""
        valid_key = Fernet.generate_key().decode()
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            service = EncryptionService()
            
            assert service._fernet is not None
    
    def test_init_with_password_key(self):
        """Test initialization with a password that needs derivation."""
        password_key = "my_secret_password_123"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': password_key}):
            service = EncryptionService()
            
            assert service._fernet is not None
    
    def test_init_without_encryption_key(self):
        """Test initialization when no encryption key is provided."""
        with patch.dict(os.environ, {}, clear=True):
            # Should generate a temporary key and log warnings
            service = EncryptionService()
            
            assert service._fernet is not None
    
    def test_init_with_empty_encryption_key(self):
        """Test initialization with empty encryption key."""
        with patch.dict(os.environ, {'ENCRYPTION_KEY': ''}):
            service = EncryptionService()
            
            assert service._fernet is not None  # Should generate temporary key
    
    def test_init_encryption_failure_handling(self):
        """Test handling of encryption initialization failures."""
        invalid_key = "not_a_valid_base64_key"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': invalid_key}), \
             patch('app.services.encryption.Fernet') as mock_fernet:
            
            mock_fernet.side_effect = Exception("Invalid key format")
            
            service = EncryptionService()
            
            # Should handle the error gracefully
            assert service._fernet is None


class TestEncryptDecryptBasic:
    """Test basic encryption and decryption operations."""
    
    def setup_method(self):
        """Set up encryption service for each test."""
        valid_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            self.service = EncryptionService()
    
    def test_encrypt_decrypt_success(self):
        """Test successful encryption and decryption."""
        plaintext = "This is sensitive data"
        
        encrypted = self.service.encrypt(plaintext)
        assert encrypted is not None
        assert encrypted != plaintext
        
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        plaintext = ""
        
        encrypted = self.service.encrypt(plaintext)
        assert encrypted is not None
        
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_unicode_data(self):
        """Test encrypting Unicode data."""
        plaintext = "Hello 世界! 🌍 Éñçrÿptïøñ tëst"
        
        encrypted = self.service.encrypt(plaintext)
        assert encrypted is not None
        
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_large_data(self):
        """Test encrypting large data."""
        plaintext = "A" * 10000  # 10KB of data
        
        encrypted = self.service.encrypt(plaintext)
        assert encrypted is not None
        
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_none_input(self):
        """Test encrypting None input."""
        result = self.service.encrypt(None)
        assert result is None
    
    def test_decrypt_none_input(self):
        """Test decrypting None input."""
        result = self.service.decrypt(None)
        assert result is None
    
    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        result = self.service.decrypt("")
        assert result is None
    
    def test_decrypt_invalid_data(self):
        """Test decrypting invalid encrypted data."""
        invalid_encrypted = "not_valid_encrypted_data"
        
        result = self.service.decrypt(invalid_encrypted)
        assert result is None
    
    def test_decrypt_corrupted_data(self):
        """Test decrypting corrupted base64 data."""
        # Valid base64 but not valid Fernet token
        corrupted = base64.urlsafe_b64encode(b"corrupted_data").decode()
        
        result = self.service.decrypt(corrupted)
        assert result is None


class TestTokenEncryption:
    """Test token-specific encryption methods."""
    
    def setup_method(self):
        """Set up encryption service for each test."""
        valid_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            self.service = EncryptionService()
    
    def test_encrypt_decrypt_token_success(self):
        """Test successful token encryption and decryption."""
        token = "ya29.a0ARrdaM-abc123def456..."
        
        encrypted = self.service.encrypt_token(token)
        assert encrypted is not None
        assert encrypted != token
        
        decrypted = self.service.decrypt_token(encrypted)
        assert decrypted == token
    
    def test_encrypt_token_oauth_format(self):
        """Test encrypting OAuth token format."""
        oauth_token = {
            "access_token": "ya29.a0ARrdaM-abc123",
            "refresh_token": "1//04abc123def456",
            "scope": "https://www.googleapis.com/auth/gmail.readonly",
            "token_type": "Bearer",
            "expires_in": 3599
        }
        
        token_str = str(oauth_token)
        
        encrypted = self.service.encrypt_token(token_str)
        assert encrypted is not None
        
        decrypted = self.service.decrypt_token(encrypted)
        assert decrypted == token_str
    
    def test_encrypt_token_none_input(self):
        """Test encrypting None token."""
        result = self.service.encrypt_token(None)
        assert result is None
    
    def test_decrypt_token_none_input(self):
        """Test decrypting None token."""
        result = self.service.decrypt_token(None)
        assert result is None
    
    def test_encrypt_token_empty_string(self):
        """Test encrypting empty token."""
        result = self.service.encrypt_token("")
        # Empty string should be handled (could be valid empty token)
        assert result is not None
        
        decrypted = self.service.decrypt_token(result)
        assert decrypted == ""
    
    def test_decrypt_token_invalid_format(self):
        """Test decrypting invalid token format."""
        invalid_token = "definitely_not_encrypted_token"
        
        result = self.service.decrypt_token(invalid_token)
        assert result is None


class TestEncryptionDetection:
    """Test encryption detection functionality."""
    
    def setup_method(self):
        """Set up encryption service for each test."""
        valid_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            self.service = EncryptionService()
    
    def test_is_encrypted_true(self):
        """Test detecting encrypted data."""
        plaintext = "This will be encrypted"
        encrypted = self.service.encrypt(plaintext)
        
        assert self.service.is_encrypted(encrypted) is True
    
    def test_is_encrypted_false_plaintext(self):
        """Test detecting plain text data."""
        plaintext = "This is just plain text"
        
        assert self.service.is_encrypted(plaintext) is False
    
    def test_is_encrypted_false_invalid_base64(self):
        """Test detecting invalid base64 data."""
        invalid_base64 = "not_valid_base64_data!"
        
        assert self.service.is_encrypted(invalid_base64) is False
    
    def test_is_encrypted_false_valid_base64_invalid_fernet(self):
        """Test detecting valid base64 but invalid Fernet token."""
        valid_base64 = base64.urlsafe_b64encode(b"just_some_data").decode()
        
        assert self.service.is_encrypted(valid_base64) is False
    
    def test_is_encrypted_none_input(self):
        """Test encryption detection with None input."""
        assert self.service.is_encrypted(None) is False
    
    def test_is_encrypted_empty_string(self):
        """Test encryption detection with empty string."""
        assert self.service.is_encrypted("") is False
    
    def test_is_encrypted_various_formats(self):
        """Test encryption detection with various data formats."""
        test_cases = [
            "regular_string",
            "123456",
            "user@example.com",
            "https://example.com/path",
            '{"key": "value"}',
            "<xml>data</xml>",
        ]
        
        for test_case in test_cases:
            assert self.service.is_encrypted(test_case) is False


class TestEncryptionWithoutService:
    """Test encryption operations when service is not properly initialized."""
    
    def test_encrypt_without_fernet(self):
        """Test encryption when Fernet is not initialized."""
        service = EncryptionService()
        service._fernet = None  # Simulate initialization failure
        
        result = service.encrypt("test data")
        assert result is None
    
    def test_decrypt_without_fernet(self):
        """Test decryption when Fernet is not initialized."""
        service = EncryptionService()
        service._fernet = None
        
        result = service.decrypt("encrypted_data")
        assert result is None
    
    def test_encrypt_token_without_fernet(self):
        """Test token encryption when Fernet is not initialized."""
        service = EncryptionService()
        service._fernet = None
        
        result = service.encrypt_token("test_token")
        assert result is None
    
    def test_decrypt_token_without_fernet(self):
        """Test token decryption when Fernet is not initialized."""
        service = EncryptionService()
        service._fernet = None
        
        result = service.decrypt_token("encrypted_token")
        assert result is None
    
    def test_is_encrypted_without_fernet(self):
        """Test encryption detection when Fernet is not initialized."""
        service = EncryptionService()
        service._fernet = None
        
        result = service.is_encrypted("some_data")
        assert result is False


class TestKeyGeneration:
    """Test encryption key generation utility."""
    
    def test_generate_encryption_key(self):
        """Test generating a new encryption key."""
        key = generate_encryption_key()
        
        assert isinstance(key, str)
        assert len(key) == 44  # Fernet key length
        assert key.endswith('=')  # Base64 padding
    
    def test_generate_multiple_keys_unique(self):
        """Test that generated keys are unique."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()
        
        assert key1 != key2
    
    def test_generated_key_is_valid(self):
        """Test that generated key works for encryption."""
        key = generate_encryption_key()
        
        # Test that the generated key can be used for encryption
        with patch.dict(os.environ, {'ENCRYPTION_KEY': key}):
            service = EncryptionService()
            
            plaintext = "Test data"
            encrypted = service.encrypt(plaintext)
            decrypted = service.decrypt(encrypted)
            
            assert decrypted == plaintext


class TestEncryptionEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up encryption service for each test."""
        valid_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            self.service = EncryptionService()
    
    def test_encrypt_very_long_string(self):
        """Test encrypting very long string."""
        # 1MB of data
        long_string = "A" * (1024 * 1024)
        
        encrypted = self.service.encrypt(long_string)
        assert encrypted is not None
        
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == long_string
    
    def test_encrypt_special_characters(self):
        """Test encrypting string with special characters."""
        special_chars = "!@#$%^&*()[]{}|;:,.<>?`~"
        
        encrypted = self.service.encrypt(special_chars)
        assert encrypted is not None
        
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == special_chars
    
    def test_encrypt_newlines_tabs(self):
        """Test encrypting string with newlines and tabs."""
        text_with_formatting = "Line 1\nLine 2\tTabbed\r\nWindows line ending"
        
        encrypted = self.service.encrypt(text_with_formatting)
        assert encrypted is not None
        
        decrypted = self.service.decrypt(encrypted)
        assert decrypted == text_with_formatting
    
    def test_multiple_encrypt_decrypt_cycles(self):
        """Test multiple encryption/decryption cycles."""
        original = "Original data"
        current = original
        
        # Encrypt and decrypt 10 times
        for i in range(10):
            encrypted = self.service.encrypt(current)
            current = self.service.decrypt(encrypted)
            
            assert current == original
    
    def test_concurrent_encryption(self):
        """Test concurrent encryption operations."""
        import threading
        
        results = []
        errors = []
        
        def encrypt_data(data, index):
            try:
                encrypted = self.service.encrypt(f"Data {index}: {data}")
                decrypted = self.service.decrypt(encrypted)
                results.append(decrypted)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=encrypt_data, args=("test data", i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        assert all("test data" in result for result in results)


class TestEncryptionIntegration:
    """Test integration scenarios and workflows."""
    
    def test_oauth_token_workflow(self):
        """Test complete OAuth token encryption workflow."""
        service = EncryptionService()
        
        # Simulate OAuth token received from Google
        oauth_response = {
            "access_token": "ya29.a0ARrdaM-example_access_token",
            "refresh_token": "1//04example_refresh_token",
            "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive.readonly",
            "token_type": "Bearer",
            "expires_in": 3599
        }
        
        # Convert to string for storage
        token_str = str(oauth_response)
        
        # Encrypt for database storage
        encrypted_token = service.encrypt_token(token_str)
        assert encrypted_token is not None
        assert service.is_encrypted(encrypted_token) is True
        
        # Later retrieve and decrypt
        decrypted_token = service.decrypt_token(encrypted_token)
        assert decrypted_token == token_str
    
    def test_password_derived_key_workflow(self):
        """Test workflow with password-derived encryption key."""
        password = "my_app_encryption_password_2024"
        
        with patch.dict(os.environ, {'ENCRYPTION_KEY': password}):
            service1 = EncryptionService()
            
            # Encrypt data
            sensitive_data = "User's sensitive information"
            encrypted = service1.encrypt(sensitive_data)
            
            # Create new service instance (simulating app restart)
            service2 = EncryptionService()
            
            # Should be able to decrypt with same password
            decrypted = service2.decrypt(encrypted)
            assert decrypted == sensitive_data
    
    def test_migration_scenario(self):
        """Test handling data encrypted with different keys."""
        # Old key
        old_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'ENCRYPTION_KEY': old_key}):
            old_service = EncryptionService()
            encrypted_with_old_key = old_service.encrypt("sensitive data")
        
        # New key (simulating key rotation)
        new_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'ENCRYPTION_KEY': new_key}):
            new_service = EncryptionService()
            
            # Should not be able to decrypt with new key
            result = new_service.decrypt(encrypted_with_old_key)
            assert result is None  # Decryption should fail gracefully
    
    def test_error_recovery_workflow(self):
        """Test error recovery in encryption workflow."""
        service = EncryptionService()
        
        # Valid encryption
        valid_data = "Valid data"
        encrypted = service.encrypt(valid_data)
        
        # Mix of valid and invalid decryption attempts
        test_cases = [
            (encrypted, valid_data),  # Valid case
            ("invalid_data", None),   # Invalid case
            ("", None),               # Empty case
            (None, None),             # None case
        ]
        
        for encrypted_input, expected in test_cases:
            result = service.decrypt(encrypted_input)
            assert result == expected
    
    def test_batch_encryption_workflow(self):
        """Test batch encryption operations."""
        service = EncryptionService()
        
        # Batch of sensitive data
        sensitive_items = [
            "user_token_1",
            "user_token_2", 
            "api_secret_key",
            "database_password",
            "oauth_refresh_token"
        ]
        
        # Encrypt all items
        encrypted_items = []
        for item in sensitive_items:
            encrypted = service.encrypt(item)
            assert encrypted is not None
            encrypted_items.append(encrypted)
        
        # Verify all are encrypted
        for encrypted in encrypted_items:
            assert service.is_encrypted(encrypted) is True
        
        # Decrypt all items
        decrypted_items = []
        for encrypted in encrypted_items:
            decrypted = service.decrypt(encrypted)
            assert decrypted is not None
            decrypted_items.append(decrypted)
        
        # Verify all decrypted correctly
        assert decrypted_items == sensitive_items


class TestEncryptionPerformance:
    """Test encryption performance characteristics."""
    
    def setup_method(self):
        """Set up encryption service for performance tests."""
        valid_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'ENCRYPTION_KEY': valid_key}):
            self.service = EncryptionService()
    
    def test_encryption_performance_small_data(self):
        """Test encryption performance with small data."""
        import time
        
        small_data = "Small data string"
        
        start_time = time.time()
        for _ in range(1000):
            encrypted = self.service.encrypt(small_data)
            decrypted = self.service.decrypt(encrypted)
            assert decrypted == small_data
        
        elapsed = time.time() - start_time
        # Should complete 1000 cycles in reasonable time (< 5 seconds)
        assert elapsed < 5.0
    
    def test_encryption_memory_usage(self):
        """Test that encryption doesn't cause memory leaks."""
        import gc
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform many encryption operations
        for i in range(100):
            data = f"Memory test data {i}"
            encrypted = self.service.encrypt(data)
            decrypted = self.service.decrypt(encrypted)
            assert decrypted == data
        
        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Should not have significant memory growth
        # Allow some growth for test infrastructure
        assert final_objects - initial_objects < 1000