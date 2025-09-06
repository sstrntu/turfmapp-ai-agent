#!/usr/bin/env python3
"""
Test script for Google OAuth token encryption

This script tests the encryption service to ensure tokens are properly encrypted and decrypted.
"""

import os
import sys

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend.app.services.encryption import encryption_service, generate_encryption_key
    print("✅ Successfully imported encryption service")
except ImportError as e:
    print(f"❌ Failed to import encryption service: {e}")
    print("Make sure to install dependencies: pip install -r backend/requirements.txt")
    sys.exit(1)

def test_basic_encryption():
    """Test basic encryption/decryption functionality."""
    print("\n🧪 Testing Basic Encryption/Decryption...")
    
    test_data = "This is a test access token: ya29.a0ARrdaM..."
    
    # Encrypt
    encrypted = encryption_service.encrypt(test_data)
    if not encrypted:
        print("❌ Failed to encrypt test data")
        return False
    
    print(f"📝 Original: {test_data[:20]}...")
    print(f"🔐 Encrypted: {encrypted[:20]}...")
    
    # Decrypt
    decrypted = encryption_service.decrypt(encrypted)
    if not decrypted:
        print("❌ Failed to decrypt test data")
        return False
    
    print(f"🔓 Decrypted: {decrypted[:20]}...")
    
    # Verify
    if test_data == decrypted:
        print("✅ Encryption/Decryption successful!")
        return True
    else:
        print("❌ Encryption/Decryption failed - data mismatch")
        return False

def test_token_encryption():
    """Test OAuth token specific encryption."""
    print("\n🧪 Testing OAuth Token Encryption...")
    
    # Simulate real Google tokens
    access_token = "ya29.a0ARrdaM-xGH7YQHbWp4J7k2V3N8X9ZqR2P1M4K5L6A7B8C9D0E1F2G3H4I5J6K7L8M9N0O1P2Q3R4S5T6U7V8W9X0Y1Z2"
    refresh_token = "1//04d2Z8QJ0X9GHF4J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y0Z1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9C0D1E2F3G4H5I6J7K8L9M0N1O2P3Q4R5S6T7U8V9W0X1Y2Z3"
    
    # Test access token encryption
    encrypted_access = encryption_service.encrypt_token(access_token)
    if not encrypted_access:
        print("❌ Failed to encrypt access token")
        return False
    
    decrypted_access = encryption_service.decrypt_token(encrypted_access)
    if access_token != decrypted_access:
        print("❌ Access token encryption failed")
        return False
    
    # Test refresh token encryption
    encrypted_refresh = encryption_service.encrypt_token(refresh_token)
    if not encrypted_refresh:
        print("❌ Failed to encrypt refresh token")
        return False
    
    decrypted_refresh = encryption_service.decrypt_token(encrypted_refresh)
    if refresh_token != decrypted_refresh:
        print("❌ Refresh token encryption failed")
        return False
    
    print("✅ OAuth token encryption successful!")
    print(f"📝 Access Token: {access_token[:20]}...")
    print(f"🔐 Encrypted: {encrypted_access[:30]}...")
    print(f"📝 Refresh Token: {refresh_token[:20]}...")
    print(f"🔐 Encrypted: {encrypted_refresh[:30]}...")
    
    return True

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases...")
    
    # Test empty string
    encrypted_empty = encryption_service.encrypt("")
    if encrypted_empty is not None:
        print("❌ Empty string should return None")
        return False
    
    # Test None
    encrypted_none = encryption_service.encrypt(None)
    if encrypted_none is not None:
        print("❌ None should return None")
        return False
    
    # Test invalid encrypted data
    decrypted_invalid = encryption_service.decrypt("invalid_encrypted_data")
    if decrypted_invalid is not None:
        print("❌ Invalid encrypted data should return None")
        return False
    
    print("✅ Edge cases handled correctly!")
    return True

def main():
    """Run all encryption tests."""
    print("🔐 Google OAuth Token Encryption Test Suite")
    print("=" * 50)
    
    # Check if encryption key is set
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if encryption_key:
        print(f"🔑 Using encryption key from environment (length: {len(encryption_key)})")
    else:
        print("⚠️  No ENCRYPTION_KEY found - using auto-generated key for testing")
    
    # Run tests
    tests = [
        ("Basic Encryption", test_basic_encryption),
        ("OAuth Token Encryption", test_token_encryption),
        ("Edge Cases", test_edge_cases)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Encryption is working correctly.")
        
        # Show key generation info
        print("\n🔑 For production, generate a new encryption key:")
        print(f"ENCRYPTION_KEY={generate_encryption_key()}")
        print("\n⚠️  Keep this key secure and backed up!")
        
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)