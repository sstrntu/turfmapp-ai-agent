from __future__ import annotations

import os
import asyncio
import json
import re
from typing import List, Literal, Optional
from urllib.parse import urlparse, urljoin

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()


def _stringify_text(value) -> str:
    """Best-effort conversion of Responses API text payloads to a plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Common shapes: {"text": "..."} or {"text": {"value": "..."}} or {"value": "..."}
        text_field = value.get("text")
        if isinstance(text_field, str):
            return text_field
        if isinstance(text_field, dict):
            inner_val = text_field.get("value")
            if isinstance(inner_val, str):
                return inner_val
        value_field = value.get("value")
        if isinstance(value_field, str):
            return value_field
        # Fallthrough: serialize the dict
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            parts.append(_stringify_text(item))
        return "".join(parts)
    # Fallback: JSON-serialize
    return json.dumps(value, ensure_ascii=False)


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
    sources: Optional[List[dict]] = None


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
            "max_completion_tokens": 1500,  # Reduced for faster processing
            "temperature": 0.7,
            "top_p": 0.9,  # Nucleus sampling for faster generation
            "frequency_penalty": 0.1,  # Slight penalty for repetition
        }
        
        # Add tools if provided with optimizations
        if req.tools:
            # Limit number of tools for faster processing
            payload["tools"] = req.tools[:5]  # Limit to 5 tools max
            payload["tool_choice"] = "auto"
            # Optimize for speed when using tools
            payload["stream"] = False
            payload["parallel_tool_calls"] = True
            # Add tool-specific optimizations
            payload["tool_timeout"] = 30  # 30 second timeout per tool

        # Add instructions (system-like context) when provided
        system_instructions = ""
        if req.developer_instructions:
            system_instructions += req.developer_instructions
        if req.assistant_context:
            if system_instructions:
                system_instructions += "\n\n"
            system_instructions += req.assistant_context
        if system_instructions:
            payload["instructions"] = system_instructions
            
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
        
        # Use optimized timeout configuration
        timeout_config = httpx.Timeout(
            timeout=60.0 if use_responses_api else 30.0,  # Shorter timeout for chat completions
            connect=10.0,
            read=45.0 if use_responses_api else 25.0,
            write=10.0
        )
        
        async with httpx.AsyncClient(timeout=timeout_config, limits=httpx.Limits(max_connections=10)) as client:
            # Initial request with timeout handling and optimization headers
            try:
                # Add request optimization headers for faster processing
                if use_responses_api:
                    headers["X-Request-Priority"] = "high"
                    headers["X-Processing-Mode"] = "fast"
                
                resp = await client.post(url, json=payload, headers=headers)
            except (httpx.ReadTimeout, httpx.TimeoutException) as e:
                # Enhanced fallback with better logging
                if use_responses_api and url.endswith("/responses"):
                    print(f"⚠️  Responses API timed out after {timeout_config.timeout}s: {e}")
                    fallback_messages = []
                    system_content = ""
                    if req.developer_instructions:
                        system_content += req.developer_instructions + "\n\n"
                    if req.assistant_context:
                        system_content += req.assistant_context
                    if system_content:
                        fallback_messages.append({"role": "system", "content": system_content})
                    fallback_messages.extend([m.model_dump() for m in req.messages])
                    fallback_payload = {
                        "model": model,
                        "messages": fallback_messages,
                        "temperature": 0.7,
                    }
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=fallback_payload,
                        headers=headers,
                    )
                else:
                    raise HTTPException(status_code=504, detail="Upstream timeout from OpenAI")

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
                    reasoning = None
                    
                    return ChatReply(ok=True, message=content, reasoning=reasoning)
                else:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)

            data = resp.json()

            content = ""
            reasoning: Optional[str] = None
            sources: Optional[List[dict]] = None

            if use_responses_api and url.endswith("/responses"):
                # For Responses API, poll until the run is completed if needed
                status = data.get("status")
                response_id = data.get("id")
                try:
                    attempts_remaining = 15  # ~3.75s at 0.25s intervals for faster polling
                    while status in {"in_progress", "queued"} and attempts_remaining > 0 and response_id:
                        await asyncio.sleep(0.25)  # Faster polling
                        poll = await client.get(f"https://api.openai.com/v1/responses/{response_id}", headers=headers)
                        if poll.status_code != 200:
                            break
                        data = poll.json()
                        status = data.get("status")
                        attempts_remaining -= 1
                except Exception:
                    # If polling fails, continue with whatever we have
                    pass

                # Parse Responses API output - do NOT use top-level "text" (it's config)
                content = _stringify_text(data.get("output_text") or "")

                if not content:
                    # Aggregate from structured output if needed
                    output_items = data.get("output", [])
                    if isinstance(output_items, list):
                        parts: List[str] = []
                        for item in output_items:
                            if not isinstance(item, dict):
                                continue
                            item_type = item.get("type")
                            # Direct output_text item
                            if item_type == "output_text":
                                parts.append(_stringify_text(item.get("text")))
                                continue
                            # Message container with content blocks
                            if item_type == "message":
                                for block in item.get("content", []) or []:
                                    if not isinstance(block, dict):
                                        continue
                                    block_type = block.get("type")
                                    if block_type == "output_text":
                                        parts.append(_stringify_text(block.get("text")))
                        content = "".join(parts)

                # Extract reasoning if available
                if req.include_reasoning or req.reasoning_summary != "never":
                    reasoning_data = data.get("reasoning", {})
                    if isinstance(reasoning_data, dict):
                        reasoning = reasoning_data.get("summary", "")

                # If still nothing, log the structure
                if not content:
                    print(
                        f"No output_text/text found. Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
                    )
                    content = (
                        "I received your message but couldn't generate a proper response. Please try again."
                    )
                else:
                    # Ensure final value is a plain string
                    content = _stringify_text(content)
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

            # Extract sources from content (URLs)
            try:
                sources = []
                if isinstance(content, str) and content:
                    # Find URLs and clean trailing punctuation
                    raw_urls = re.findall(r"https?://[^\s)]+", content)
                    seen = set()
                    for u in raw_urls:
                        cleaned = u.rstrip('.,);]')
                        if cleaned in seen:
                            continue
                        seen.add(cleaned)
                        try:
                            parsed = urlparse(cleaned)
                            if parsed.scheme in {"http", "https"} and parsed.netloc:
                                sources.append({
                                    "url": cleaned,
                                    "site": parsed.netloc,
                                    "favicon": f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64",
                                })
                        except Exception:
                            continue
                    if sources:
                        sources = sources[:8]
                    else:
                        sources = None
            except Exception:
                sources = None

            # Try to enrich sources with thumbnails (Open Graph images)
            if sources:
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.5)) as _client:
                        sem = asyncio.Semaphore(3)
                        async def enrich(s: dict) -> None:
                            try:
                                async with sem:
                                    r = await _client.get(s["url"], follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
                                if r.status_code >= 200 and r.status_code < 400:
                                    html = r.text[:120000]
                                    import re as _re
                                    t = _re.search(r"<title[^>]*>([\s\S]*?)</title>", html, _re.IGNORECASE)
                                    if t:
                                        title_val = _re.sub(r"\s+", " ", t.group(1).strip())
                                        s["title"] = title_val
                                    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                                    if not m:
                                        m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                                    if m:
                                        img_url = m.group(1)
                                        if img_url:
                                            if img_url.startswith('//'):
                                                img_url = f"https:{img_url}"
                                            elif img_url.startswith('/'):
                                                img_url = urljoin(s["url"], img_url)
                                            s["thumbnail"] = img_url
                            except Exception:
                                return
                        await asyncio.gather(*(enrich(s) for s in sources[:3]))
                except Exception:
                    pass

            return ChatReply(ok=True, message=content, reasoning=reasoning, sources=sources)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error in chat endpoint: {exc}")
        import traceback
        traceback.print_exc()
        
        # No fallbacks - respect the user's model choice
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")


