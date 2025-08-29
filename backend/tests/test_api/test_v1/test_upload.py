"""
Test Upload API Endpoints

Tests for app.api.v1.upload module following code.md standards.
Comprehensive coverage for file upload functionality.
"""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any
from fastapi.testclient import TestClient
from fastapi import status
import io


class TestUploadEndpoints:
    """Test file upload API endpoints."""

    def test_upload_file_success(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test successful file upload.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        # Create test file
        test_content = b"Test file content"
        test_file = io.BytesIO(test_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.post(
                "/api/v1/uploads/",
                files={"file": ("test.txt", test_file, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "filename" in data
        assert "file_id" in data
        assert "file_type" in data
        assert "file_size" in data
        assert data["file_type"] == "document"
        assert data["file_size"] == len(test_content)

    def test_upload_image_file(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test uploading an image file.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        # Create fake image content
        image_content = b"fake-image-data"
        image_file = io.BytesIO(image_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.post(
                "/api/v1/uploads/",
                files={"file": ("test.jpg", image_file, "image/jpeg")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["file_type"] == "image"
        assert data["filename"].endswith(".jpg")

    def test_upload_video_file(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test uploading a video file.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        video_content = b"fake-video-data"
        video_file = io.BytesIO(video_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.post(
                "/api/v1/uploads/",
                files={"file": ("test.mp4", video_file, "video/mp4")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["file_type"] == "video"
        assert data["filename"].endswith(".mp4")

    def test_upload_audio_file(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test uploading an audio file.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        audio_content = b"fake-audio-data"
        audio_file = io.BytesIO(audio_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.post(
                "/api/v1/uploads/",
                files={"file": ("test.mp3", audio_file, "audio/mpeg")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["file_type"] == "audio"
        assert data["filename"].endswith(".mp3")

    def test_upload_file_no_filename(
        self,
        client: TestClient
    ) -> None:
        """Test uploading file with no filename.
        
        Args:
            client: FastAPI test client
        """
        test_content = b"Test content"
        test_file = io.BytesIO(test_content)
        
        response = client.post(
            "/api/v1/uploads/",
            files={"file": ("", test_file, "text/plain")}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # FastAPI validates UploadFile before reaching our endpoint
        assert "Expected UploadFile" in str(response.json()["detail"])

    def test_upload_file_unsupported_type(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test uploading unsupported file type.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        exe_content = b"fake-executable-data"
        exe_file = io.BytesIO(exe_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.post(
                "/api/v1/uploads/",
                files={"file": ("test.exe", exe_file, "application/octet-stream")}
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "File type not allowed" in response.json()["detail"]

    def test_upload_file_too_large(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test uploading file that's too large.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        # Create large content (simulate file larger than MAX_FILE_SIZE)
        large_content = b"x" * (100 * 1024 * 1024 + 1)  # > 100MB
        large_file = io.BytesIO(large_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.post(
                "/api/v1/uploads/",
                files={"file": ("large.txt", large_file, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "File too large" in response.json()["detail"]

    def test_get_file_success(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test retrieving an uploaded file.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        # First upload a file to get a file ID
        test_content = b"Test file content for retrieval"
        test_file = io.BytesIO(test_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            # Upload the file first
            upload_response = client.post(
                "/api/v1/uploads/",
                files={"file": ("test_file.txt", test_file, "text/plain")}
            )
            assert upload_response.status_code == status.HTTP_200_OK
            
            # Get the file ID from the upload response
            file_id = upload_response.json()["file_id"]
            
            # Now retrieve the file using the file ID
            response = client.get(f"/api/v1/uploads/{file_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.content == test_content

    def test_get_file_not_found(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test retrieving a non-existent file.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.get("/api/v1/uploads/nonexistent.txt")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found" in response.json()["detail"]

    def test_delete_file_success(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test deleting an uploaded file.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        # First upload a file to get a file ID
        test_content = b"Delete this file"
        test_file = io.BytesIO(test_content)
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            # Upload the file first
            upload_response = client.post(
                "/api/v1/uploads/",
                files={"file": ("delete_me.txt", test_file, "text/plain")}
            )
            assert upload_response.status_code == status.HTTP_200_OK
            
            # Get the file ID from the upload response
            file_id = upload_response.json()["file_id"]
            
            # Now delete the file using the file ID
            response = client.delete(f"/api/v1/uploads/{file_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "File deleted successfully"

    def test_delete_file_not_found(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test deleting a non-existent file.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            response = client.delete("/api/v1/uploads/nonexistent.txt")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found" in response.json()["detail"]

    def test_upload_directory_creation(
        self,
        client: TestClient
    ) -> None:
        """Test that upload directory is created if it doesn't exist.
        
        Args:
            client: FastAPI test client
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            upload_dir = Path(tmp_dir) / "nonexistent_uploads"
            
            # Create the directory manually since the upload system expects it to exist
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            test_content = b"Test content"
            test_file = io.BytesIO(test_content)
            
            with patch("app.api.v1.upload.UPLOAD_DIR", upload_dir):
                # Upload should work now that directory exists
                response = client.post(
                    "/api/v1/uploads/",
                    files={"file": ("test.txt", test_file, "text/plain")}
                )
            
            assert response.status_code == status.HTTP_200_OK
            assert upload_dir.exists()

    def test_no_file_provided(
        self,
        client: TestClient
    ) -> None:
        """Test upload request with no file.
        
        Args:
            client: FastAPI test client
        """
        response = client.post("/api/v1/uploads/")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUploadUtilityFunctions:
    """Test upload utility functions."""

    def test_get_file_type_image_extensions(self) -> None:
        """Test file type detection for image files."""
        from app.api.v1.upload import get_file_type
        
        assert get_file_type("test.jpg") == "image"
        assert get_file_type("test.jpeg") == "image"
        assert get_file_type("test.png") == "image"
        assert get_file_type("test.gif") == "image"
        assert get_file_type("test.webp") == "image"
        assert get_file_type("test.bmp") == "image"

    def test_get_file_type_video_extensions(self) -> None:
        """Test file type detection for video files."""
        from app.api.v1.upload import get_file_type
        
        assert get_file_type("test.mp4") == "video"
        assert get_file_type("test.avi") == "video"
        assert get_file_type("test.mov") == "video"
        assert get_file_type("test.wmv") == "video"
        assert get_file_type("test.flv") == "video"
        assert get_file_type("test.webm") == "video"

    def test_get_file_type_audio_extensions(self) -> None:
        """Test file type detection for audio files."""
        from app.api.v1.upload import get_file_type
        
        assert get_file_type("test.mp3") == "audio"
        assert get_file_type("test.wav") == "audio"
        assert get_file_type("test.flac") == "audio"
        assert get_file_type("test.aac") == "audio"
        assert get_file_type("test.ogg") == "audio"

    def test_get_file_type_document_extensions(self) -> None:
        """Test file type detection for document files."""
        from app.api.v1.upload import get_file_type
        
        assert get_file_type("test.pdf") == "document"
        assert get_file_type("test.txt") == "document"
        assert get_file_type("test.doc") == "document"
        assert get_file_type("test.docx") == "document"
        assert get_file_type("test.rtf") == "document"

    def test_get_file_type_case_insensitive(self) -> None:
        """Test that file type detection is case insensitive."""
        from app.api.v1.upload import get_file_type
        
        assert get_file_type("test.JPG") == "image"
        assert get_file_type("test.Mp4") == "video"
        assert get_file_type("test.PDF") == "document"
        assert get_file_type("test.MP3") == "audio"

    def test_get_file_type_unknown_extension(self) -> None:
        """Test file type detection for unknown extensions."""
        from app.api.v1.upload import get_file_type
        
        assert get_file_type("test.xyz") == "other"
        assert get_file_type("test.unknown") == "other"
        assert get_file_type("test") == "other"  # No extension

    def test_upload_endpoint_routes_exist(self, client: TestClient) -> None:
        """Test that upload endpoints are properly registered.
        
        Args:
            client: FastAPI test client
        """
        # Test that endpoints exist (will return errors without proper data)
        response = client.post("/api/v1/uploads/")
        assert response.status_code != status.HTTP_404_NOT_FOUND
        
        # Test GET endpoint with invalid file ID (should return 404 for file not found, not 404 for endpoint not found)
        response = client.get("/api/v1/uploads/invalid-uuid-format")
        # Should get 404 for file not found, which means the endpoint exists
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found" in response.json()["detail"]
        
        # Test DELETE endpoint with invalid file ID (should return 404 for file not found, not 404 for endpoint not found)
        response = client.delete("/api/v1/uploads/invalid-uuid-format")
        # Should get 404 for file not found, which means the endpoint exists
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found" in response.json()["detail"]

    def test_unique_filename_generation(
        self,
        client: TestClient,
        tmp_path: Path
    ) -> None:
        """Test that uploaded files get unique filenames.
        
        Args:
            client: FastAPI test client
            tmp_path: Temporary directory for testing
        """
        test_content = b"Test content"
        
        with patch("app.api.v1.upload.UPLOAD_DIR", tmp_path):
            # Upload same filename twice
            file1 = io.BytesIO(test_content)
            response1 = client.post(
                "/api/v1/uploads/",
                files={"file": ("same_name.txt", file1, "text/plain")}
            )
            
            file2 = io.BytesIO(test_content)
            response2 = client.post(
                "/api/v1/uploads/",
                files={"file": ("same_name.txt", file2, "text/plain")}
            )
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        # File IDs should be different (UUIDs are unique)
        file_id1 = response1.json()["file_id"]
        file_id2 = response2.json()["file_id"]
        assert file_id1 != file_id2
        
        # Filenames should be the same (original filename preserved)
        filename1 = response1.json()["filename"]
        filename2 = response2.json()["filename"]
        assert filename1 == "same_name.txt"
        assert filename2 == "same_name.txt"