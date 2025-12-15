
import json
import httpx
import asyncio

# Setup payload
payload = {
    "message": "What is the time?",
    "conversation_id": None,
    "model": "gpt-4o",
    "temperature": 0.7,
    "include_memory": True
}

async def stream_chat():
    print(f"Connecting to stream...")
    # NOTE: We need to bypass auth or use a valid token.
    # Since we can't easily get a real token, we will rely on the app running in docker with 
    # NO_AUTH or similar if possible? No, the code checks `current_user`.
    #
    # Accessing the code directly via `TestClient` is better because we can patch the auth dependency.
    
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.v1 import chat
    
    import uuid
    # Patch auth
    app.dependency_overrides[chat.get_current_user_from_token] = lambda: {"id": str(uuid.uuid4())}
    
    client = TestClient(app)
    
    with client.stream("POST", "/api/v2/chat/stream", json=payload) as response:
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            print(response.text)
            return

        for line in response.iter_lines():
            if line:
                print(f"Received: {line}")

if __name__ == "__main__":
    # We need to run this with python inside the container to have access to app modules
    # OR we can try to use httpx against localhost if we had a token.
    # We'll stick to the internal import method as it worked for 422 debug.
    import asyncio
    # TestClient is synchronous but the endpoint is async. TestClient handles it.
    
    # Just run the synchronous TestClient wrapper
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.v1 import chat
    
    import uuid
    app.dependency_overrides[chat.get_current_user_from_token] = lambda: {"id": str(uuid.uuid4())}
    client = TestClient(app)
    
    print("Initiating stream request...")
    with client.stream("POST", "/api/v2/chat/stream", json=payload) as response:
        print(f"Status: {response.status_code}")
        for line in response.iter_lines():
            if line:
                print(f"EVENT: {line}")
