from __future__ import annotations

import logging

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent directory .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Union

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Tool configurations - easy to extend for new tools
TOOL_CONFIGS = {
    "sound-effects": {
        "name": "Sound Effects Generator",
        "description": "Generate high-quality sound effects from text descriptions",
        "endpoint": "https://fal.run/cassetteai/sound-effects-generator",
        "icon": "🎵",
        "parameters": [
            {
                "name": "prompt",
                "type": "string",
                "required": True,
                "prompt": "🎵 Describe the sound effect you want to generate:",
                "placeholder": "e.g., thunderstorm with heavy rain, dog barking, car engine starting",
            },
            {
                "name": "duration",
                "type": "integer",
                "min": 1,
                "max": 30,
                "default": 5,
                "prompt": "Duration in seconds (1-30, default 5):",
                "placeholder": "Enter number between 1-30",
            },
        ],
        "output_type": "audio",
    }
}


# Request/Response models
class ToolParameter(BaseModel):
    name: str
    type: str
    required: bool = False
    prompt: str
    placeholder: str = ""
    min: Optional[int] = None
    max: Optional[int] = None
    default: Optional[Union[str, int, float]] = None
    choices: Optional[List[str]] = None


class ToolConfig(BaseModel):
    name: str
    description: str
    endpoint: str
    icon: str
    parameters: List[ToolParameter]
    output_type: str


class SoundEffectRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    duration: int = Field(ge=1, le=30, default=5)


class ToolResult(BaseModel):
    success: bool
    tool_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None


# FAL API client
class FALClient:
    def __init__(self):
        self.api_key = os.getenv("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY not found in environment variables")

        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    async def call_api(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make async API call to fal.ai endpoint"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    endpoint, json=payload, headers=self.headers
                )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"FAL API error: {response.text}",
                    )

                return response.json()

            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="FAL API timeout")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"FAL API error: {str(e)}")


# Initialize FAL client at runtime
fal_client = None


def get_fal_client():
    global fal_client
    if fal_client is None:
        fal_client = FALClient()
    return fal_client


# Create media directory for storing results
MEDIA_DIR = Path("fal_media")
MEDIA_DIR.mkdir(exist_ok=True)


async def download_and_store_media(url: str, file_extension: str = ".wav") -> str:
    """Download media file from fal.ai and store locally"""
    file_id = str(uuid.uuid4())
    local_filename = f"{file_id}{file_extension}"
    local_path = MEDIA_DIR / local_filename

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(response.content)

    return local_filename


@router.get("/available")
async def get_available_tools() -> Dict[str, ToolConfig]:
    """Get list of available fal.ai tools and their configurations"""
    return {tool_id: ToolConfig(**config) for tool_id, config in TOOL_CONFIGS.items()}


@router.post("/sound-effects")
async def generate_sound_effect(
    request: SoundEffectRequest, background_tasks: BackgroundTasks
) -> ToolResult:
    """Generate sound effect using fal.ai cassette AI model"""
    import time

    start_time = time.time()

    try:
        # Prepare payload for fal.ai API
        payload = {"prompt": request.prompt, "duration": request.duration}

        logger.info(f"Calling fal.ai with payload: {payload}")

        # Call fal.ai API
        client = get_fal_client()
        fal_response = await client.call_api(
            TOOL_CONFIGS["sound-effects"]["endpoint"], payload
        )

        logger.info(f"FAL API response: {fal_response}")

        # Extract audio URL from response
        if "audio_file" in fal_response and "url" in fal_response["audio_file"]:
            audio_url = fal_response["audio_file"]["url"]

            # Download and store the audio file locally
            local_filename = await download_and_store_media(audio_url, ".wav")

            processing_time = time.time() - start_time

            return ToolResult(
                success=True,
                tool_id="sound-effects",
                result={
                    "audio_file": f"/api/v1/fal-tools/media/{local_filename}",
                    "original_url": audio_url,
                    "prompt": request.prompt,
                    "duration": request.duration,
                    "filename": local_filename,
                },
                processing_time=round(processing_time, 2),
            )
        else:
            raise HTTPException(
                status_code=500, detail="Invalid response from fal.ai API"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Error generating sound effect: {e}")
        return ToolResult(
            success=False,
            tool_id="sound-effects",
            error=str(e),
            processing_time=round(time.time() - start_time, 2),
        )


@router.get("/media/{filename}")
async def serve_media_file(filename: str):
    """Serve downloaded media files"""
    file_path = MEDIA_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    from fastapi.responses import FileResponse

    # Determine content type based on extension
    content_type = "application/octet-stream"
    if filename.endswith(".wav"):
        content_type = "audio/wav"
    elif filename.endswith(".mp3"):
        content_type = "audio/mpeg"
    elif filename.endswith(".png"):
        content_type = "image/png"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        content_type = "image/jpeg"

    return FileResponse(path=str(file_path), media_type=content_type, filename=filename)


# Cleanup task to remove old media files
async def cleanup_old_media():
    """Remove media files older than 24 hours"""
    import time

    current_time = time.time()

    for file_path in MEDIA_DIR.glob("*"):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            # Remove files older than 24 hours (86400 seconds)
            if file_age > 86400:
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up old media file: {file_path.name}")
                except Exception as e:
                    logger.info(f"Error cleaning up file {file_path.name}: {e}")
