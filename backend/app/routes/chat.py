from __future__ import annotations

import os
from typing import List, Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()


Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(min_length=1)
    model: Optional[str] = None
    include_reasoning: bool = False
    developer_instructions: Optional[str] = None
    assistant_context: Optional[str] = None
    text_format: Optional[str] = "text"
    text_verbosity: Optional[str] = "medium"
    reasoning_effort: Optional[str] = "medium"
    reasoning_summary: Optional[str] = "auto"
    tools: Optional[List[dict]] = None
    store: bool = True
    attachments: Optional[List[dict]] = None


class ChatReply(BaseModel):
    ok: bool
    message: str
    reasoning: Optional[str] = None


@router.post("/", response_model=ChatReply)
async def chat(req: ChatRequest) -> ChatReply:
    """Proxy chat completion to OpenAI using server-side API key.

    Requires OPENAI_API_KEY in environment. Optional OPENAI_MODEL (defaults
    to gpt-4o-mini if not provided by request).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    # Fall back to default if env var is unset or blank
    env_model = os.getenv("OPENAI_MODEL")
    model = req.model or (env_model if env_model else "gpt-4o-mini")

    # Check if web search is requested in tools
    has_web_search = req.tools and any(tool.get("type") == "web_search_preview" for tool in req.tools)
    
    # Don't modify the selected model - use exactly what the user chose
    
    # Use Responses API for gpt-5 models or when advanced features are requested
    use_responses_api = (
        model.lower().startswith("gpt-5") or 
        req.tools is not None or 
        req.developer_instructions or 
        req.assistant_context
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if use_responses_api:
        # Simple Responses API format like your example
        # Convert messages to simple input text
        user_input = ""
        for m in req.messages:
            if m.role == "user":
                user_input = m.content
                break
        
        payload = {
            "model": model,
            "input": user_input,
        }
        
        # Add tools if provided
        if req.tools:
            payload["tools"] = req.tools
            
        url = "https://api.openai.com/v1/responses"
    else:
        # Construct payload for Chat Completions API
        messages = [m.model_dump() for m in req.messages]
        if req.include_reasoning:
            system_prefix = (
                "Respond in compact JSON with keys 'answer' and 'reason'. "
                "Keep 'reason' to 1-3 short bullet points or sentences; "
                "do not include internal chain-of-thought."
            )
            messages = (
                [{"role": "system", "content": system_prefix}] + messages
            )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
        }
        url = "https://api.openai.com/v1/chat/completions"
    try:
        print(f"Making request to: {url}")
        print(f"Payload: {payload}")
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)

            # If the selected model is not available or request invalid, retry once with
            # a safe default model via chat completions.
            if resp.status_code == 400:
                try:
                    err = resp.json()
                    msg = str(err)
                except Exception:
                    msg = resp.text
                if ("model" in msg.lower() and ("not" in msg.lower() or "found" in msg.lower())) or ("provide a model" in msg.lower()):
                    fallback_model = "gpt-4o-mini"
                    # Build fallback payload for chat completions
                    fb_messages = [m.model_dump() for m in req.messages]
                    if req.include_reasoning:
                        fb_messages = (
                            [
                                {
                                    "role": "system",
                                    "content": (
                                        "Respond in compact JSON with keys 'answer' and 'reason'. "
                                        "Keep 'reason' to 1-3 short bullet points or sentences; "
                                        "do not include internal chain-of-thought."
                                    ),
                                }
                            ]
                            + fb_messages
                        )
                    fb_payload = {
                        "model": fallback_model,
                        "messages": fb_messages,
                        "temperature": 0.7,
                    }
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=fb_payload,
                        headers=headers,
                    )

            if resp.status_code != 200:
                print(f"API Error - Status: {resp.status_code}, Response: {resp.text}")
                
                # If Responses API fails, try falling back to Chat Completions
                if use_responses_api and url.endswith("/responses"):
                    print("Responses API failed, falling back to Chat Completions API")
                    # Build fallback request using chat completions
                    fallback_messages = []
                    
                    # Add system message combining developer instructions and assistant context
                    system_content = ""
                    if req.developer_instructions:
                        system_content += req.developer_instructions + "\n\n"
                    if req.assistant_context:
                        system_content += req.assistant_context
                    
                    if system_content:
                        fallback_messages.append({"role": "system", "content": system_content})
                    
                    # Add user messages
                    fallback_messages.extend([m.model_dump() for m in req.messages])
                    
                    fallback_payload = {
                        "model": model,
                        "messages": fallback_messages,
                        "temperature": 0.7,
                    }
                    
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=fallback_payload,
                        headers=headers
                    )
                    
                    if resp.status_code != 200:
                        raise HTTPException(status_code=resp.status_code, detail=resp.text)
                    
                    # Parse as chat completions response
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    ) or ""
                    
                    return ChatReply(ok=True, message=content, reasoning=reasoning)
                else:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)

            data = resp.json()

            content = ""
            reasoning: Optional[str] = None

            if use_responses_api and url.endswith("/responses"):
                # Parse Responses API format - expecting direct output_text field
                content = data.get("output_text", "")
                
                # Extract reasoning if available  
                if req.include_reasoning or req.reasoning_summary != "never":
                    reasoning_data = data.get("reasoning", {})
                    if isinstance(reasoning_data, dict):
                        reasoning = reasoning_data.get("summary", "")
                
                # If no output_text, log the response structure for debugging
                if not content:
                    print(f"No output_text found. Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    content = "I received your message but couldn't generate a proper response. Please try again."
            else:
                # Chat Completions API
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                ) or ""
                if req.include_reasoning:
                    try:
                        import json as _json
                        parsed = _json.loads(content)
                        if isinstance(parsed, dict):
                            maybe = str(parsed.get("reason", ""))
                            if maybe:
                                reasoning = maybe
                            content = str(parsed.get("answer", content))
                    except Exception:
                        pass

            return ChatReply(ok=True, message=content, reasoning=reasoning)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error in chat endpoint: {exc}")
        import traceback
        traceback.print_exc()
        
        # No fallbacks - respect the user's model choice
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")


