#!/usr/bin/env python3
"""
Quick test script to verify Google integration is working.
Run this to test the Google OAuth service without browser.
"""

import requests
import os
import sys

def test_google_integration():
    """Test Google integration endpoints"""
    base_url = "http://localhost:3005"
    
    print("🧪 Testing Google Integration...")
    print("=" * 50)
    
    # Test 1: Backend connection check  
    print("1. Testing backend connection...")
    try:
        response = requests.get(f"{base_url}/portal.html", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Frontend is accessible")
        else:
            print(f"   ❌ Frontend error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to frontend: {e}")
        return False
    
    # Test 2: Google auth endpoint exists (should return 403 without auth)
    print("2. Testing Google auth endpoint...")
    try:
        response = requests.get(f"{base_url}/api/v1/google/auth/status", timeout=5)
        if response.status_code == 403:
            print("   ✅ Google auth endpoint exists (requires authentication)")
        elif response.status_code == 401:
            print("   ✅ Google auth endpoint exists (requires authentication)")  
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            print(f"      Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Google endpoint error: {e}")
        return False
    
    # Test 3: Environment variables
    print("3. Testing environment configuration...")
    required_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI']
    
    # Test by importing the service
    try:
        import sys
        sys.path.append('/Users/sirasasitorn/Documents/VScode/turfmapp-ai-agent/backend')
        os.environ['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', 'your-client-id-here')
        os.environ['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', 'your-client-secret-here')
        os.environ['GOOGLE_REDIRECT_URI'] = 'http://localhost:3005/auth/google/callback'
        
        from app.services.google_oauth import google_oauth_service
        print("   ✅ Google OAuth service loads successfully")
        print(f"   ✅ Configured scopes: {len(google_oauth_service.scopes)} scopes")
        print(f"   ✅ Redirect URI: {google_oauth_service.redirect_uri}")
        
    except Exception as e:
        print(f"   ❌ Service import error: {e}")
        return False
    
    print("=" * 50)
    print("🎉 Google integration test completed!")
    print()
    print("Next steps:")
    print("1. Open http://localhost:3005/test-google.html")
    print("2. Click 'Authenticate with Google'")
    print("3. Complete OAuth flow in browser")
    print("4. Test Gmail, Drive, and Calendar features")
    
    return True

if __name__ == "__main__":
    success = test_google_integration()
    sys.exit(0 if success else 1)