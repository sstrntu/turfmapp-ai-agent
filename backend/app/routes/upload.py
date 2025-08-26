from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()

# Configure upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {
    'image': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'},
    'video': {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'},
    'audio': {'.mp3', '.wav', '.ogg', '.m4a', '.flac'},
    'document': {'.pdf', '.doc', '.docx', '.txt', '.rtf'},
    'data': {'.json', '.csv', '.xml', '.xlsx'}
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class UploadResponse(BaseModel):
    ok: bool
    file_id: str
    filename: str
    file_type: str
    file_size: int
    url: str


def get_file_type(filename: str) -> str:
    """Determine file type based on extension"""
    suffix = Path(filename).suffix.lower()
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if suffix in extensions:
            return file_type
    return 'unknown'


@router.post("/", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """Upload a file and return file information"""
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    # Check file type
    file_type = get_file_type(file.filename)
    if file_type == 'unknown':
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    unique_filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Return file information
    return UploadResponse(
        ok=True,
        file_id=file_id,
        filename=file.filename,
        file_type=file_type,
        file_size=len(contents),
        url=f"/api/uploads/{file_id}{file_extension}"
    )


@router.get("/{file_id}")
async def get_file(file_id: str):
    """Serve uploaded files"""
    # Find file with this ID
    matching_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = matching_files[0]
    
    # Return file content
    try:
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type='application/octet-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve file: {str(e)}")


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete an uploaded file"""
    # Find file with this ID
    matching_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = matching_files[0]
    
    try:
        os.remove(file_path)
        return {"ok": True, "message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")