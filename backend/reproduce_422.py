import sys
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.api.v1 import chat

# Patch auth to bypass logic
app.dependency_overrides[chat.get_current_user_from_token] = lambda: {"id": "test_user_repro"}

client = TestClient(app)

payloads = [
    ("Standard", {
        "message": "Hello",
        "conversation_id": None,
        "model": "gpt-4o",
        "temperature": 0.7,
        "include_memory": True
    }),
    ("Null Model", {
        "message": "Hello",
        "conversation_id": None,
        "model": None,
        "temperature": 0.7,
        "include_memory": True
    }),
    ("Missing Model", {
        "message": "Hello",
        "conversation_id": None,
        "temperature": 0.7,
        "include_memory": True
    }),
    ("Empty Conv ID", {
        "message": "Hello",
        "conversation_id": "",
        "temperature": 0.7,
        "include_memory": True
    }),
    ("Null Conv ID", {
        "message": "Hello",
        "conversation_id": None,
        "temperature": 0.7,
        "include_memory": True
    }),
]

print("="*50)
print("Testing Payloads for 422")
print("="*50)

for name, payload in payloads:
    print(f"\nTesting Payload: {name}")
    try:
        # Note: /stream endpoint returns a stream, but TestClient handles it.
        # We only care about validation, so subsequent internal errors (like db connection) are fine, 
        # as long as it's not 422.
        response = client.post("/api/v2/chat/stream", json=payload)
        
        if response.status_code == 422:
            print(f"❌ 422 Unprocessable Entity")
            print(f"Details: {response.json()}")
        elif response.status_code == 200:
            print(f"✅ 200 OK (Stream started)")
        else:
            print(f"ℹ️ Status: {response.status_code}")
            # If it's a 500 because of missing DB, that implies validation passed!
            if response.status_code == 500:
                 print("✅ Validation PASSED (failed later at DB/Logic)")
            else:
                 print(response.text)
                 
    except Exception as e:
        print(f"Server Error: {e}")

