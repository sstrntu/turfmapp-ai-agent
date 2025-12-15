
import json
import httpx
import asyncio

# Setup payload - Use a query that triggers web search
payload = {
    "message": "What is the latest news about OpenAI?",
    "conversation_id": None,
    "model": "gpt-4o",
    "temperature": 0.7,
    "include_memory": True
}

if __name__ == "__main__":
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.v1 import chat
    import uuid
    
    # Patch auth with a consistent UUID so we can check DB if needed (or just output)
    user_id = str(uuid.uuid4())
    app.dependency_overrides[chat.get_current_user_from_token] = lambda: {"id": user_id}
    client = TestClient(app)
    
    print("Initiating stream request with Web Search query...")
    with client.stream("POST", "/api/v2/chat/stream", json=payload) as response:
        print(f"Status: {response.status_code}")
        for line in response.iter_lines():
            if line:
                # We want to see the 'done' event to check metadata
                try:
                    if line.startswith(b"data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "done":
                            print("\n✅ DONE Event Received!")
                            sources = data.get("sources", [])
                            print(f"Top-level sources: {len(sources)}")
                            
                            asst_msg = data.get("assistant_message", {})
                            meta = asst_msg.get("metadata", {})
                            meta_sources = meta.get("sources", [])
                            print(f"Metadata sources: {len(meta_sources)}")
                            
                            if len(sources) > 0 and len(meta_sources) > 0:
                                print("✅ SUCCESS: Sources are present in both top-level and metadata!")
                            elif len(sources) > 0:
                                print("⚠️ PARTIAL: Sources in top-level but MISSING in metadata (Fix failed?)")
                            else:
                                print("ℹ️ No sources found (Maybe search tool wasn't used?)")
                                # Print tools used to verify
                                print(f"Tools used: {meta.get('tools_used')}")
                        elif data.get("type") == "tool_call":
                            print(f"🔨 Tool Call: {data.get('tool')}")
                except Exception as e:
                    pass
                # print(f"EVENT: {line}") # Reduced noise
