#!/usr/bin/env python3
"""
Test script for RAG (Retrieval-Augmented Generation) endpoints

This script demonstrates how to:
1. Upload a document
2. Query the document using RAG
3. List uploaded documents
4. Get RAG statistics
5. Delete a document

Usage:
    python test_rag.py --token YOUR_JWT_TOKEN
"""

import requests
import argparse
import json
import os

BASE_URL = "http://localhost:8000"


def upload_document(token: str, file_path: str):
    """Upload a document to the RAG system"""
    print(f"\n📤 Uploading document: {file_path}")

    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'text/plain')}
        headers = {'Authorization': f'Bearer {token}'}

        response = requests.post(
            f"{BASE_URL}/api/v1/rag/upload",
            files=files,
            headers=headers
        )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Document uploaded successfully!")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Filename: {result['filename']}")
        print(f"   Chunk count: {result['chunk_count']}")
        print(f"   Status: {result['status']}")
        return result['document_id']
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def query_documents(token: str, question: str, top_k: int = 5):
    """Query the RAG system"""
    print(f"\n🔍 Querying: {question}")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "question": question,
        "top_k": top_k,
        "include_sources": True
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/rag/query",
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n💬 Answer:")
        print(f"   {result['answer']}\n")
        print(f"📊 Chunks found: {result['chunks_found']}")

        if result.get('sources'):
            print(f"\n📚 Sources:")
            for source in result['sources']:
                print(f"   [{source['source_number']}] {source['filename']} (similarity: {source['similarity']:.3f})")
                print(f"       Preview: {source['preview'][:100]}...")
        return result
    else:
        print(f"❌ Query failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def list_documents(token: str):
    """List all uploaded documents"""
    print(f"\n📄 Listing documents...")

    headers = {'Authorization': f'Bearer {token}'}

    response = requests.get(
        f"{BASE_URL}/api/v1/rag/documents",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Total documents: {result['total']}")

        for doc in result['documents']:
            print(f"\n   📝 {doc['filename']}")
            print(f"      ID: {doc['id']}")
            print(f"      Type: {doc['file_type']}")
            print(f"      Chunks: {doc.get('chunk_count', 'N/A')}")
            print(f"      Status: {doc['status']}")
            print(f"      Uploaded: {doc['created_at']}")
        return result
    else:
        print(f"❌ Failed to list documents: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def get_stats(token: str):
    """Get RAG statistics"""
    print(f"\n📊 Getting RAG statistics...")

    headers = {'Authorization': f'Bearer {token}'}

    response = requests.get(
        f"{BASE_URL}/api/v1/rag/stats",
        headers=headers
    )

    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Statistics:")
        print(f"   Total documents: {stats.get('total_documents', 0)}")
        print(f"   Total chunks: {stats.get('total_chunks', 0)}")
        print(f"   Chunks with embeddings: {stats.get('chunks_with_embeddings', 0)}")
        print(f"   Average chunk length: {stats.get('avg_chunk_length', 0):.1f} chars")
        print(f"   Embedding coverage: {stats.get('embedding_coverage', 0):.1%}")
        return stats
    else:
        print(f"❌ Failed to get stats: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def delete_document(token: str, document_id: str):
    """Delete a document"""
    print(f"\n🗑️  Deleting document: {document_id}")

    headers = {'Authorization': f'Bearer {token}'}

    response = requests.delete(
        f"{BASE_URL}/api/v1/rag/documents/{document_id}",
        headers=headers
    )

    if response.status_code == 200:
        print(f"✅ Document deleted successfully")
        return True
    else:
        print(f"❌ Failed to delete document: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test RAG endpoints')
    parser.add_argument('--token', required=True, help='JWT authentication token')
    parser.add_argument('--file', default='test_document.txt', help='File to upload')
    parser.add_argument('--skip-upload', action='store_true', help='Skip document upload')

    args = parser.parse_args()

    print("=" * 60)
    print("🧪 TurfMapp RAG System Test")
    print("=" * 60)

    # Step 1: Upload document (if not skipped)
    document_id = None
    if not args.skip_upload and os.path.exists(args.file):
        document_id = upload_document(args.token, args.file)

        if not document_id:
            print("\n⚠️  Upload failed. Cannot proceed with testing.")
            return

        # Wait a moment for embeddings to be generated
        print("\n⏳ Waiting for embeddings to be generated...")
        import time
        time.sleep(3)

    # Step 2: Query documents
    print("\n" + "=" * 60)
    print("Testing RAG Queries")
    print("=" * 60)

    test_questions = [
        "What is TurfMapp?",
        "What database does TurfMapp use?",
        "How does the RAG system work?",
        "What file formats are supported for document upload?",
        "What is account-level memory?"
    ]

    for question in test_questions:
        query_documents(args.token, question, top_k=3)
        print("\n" + "-" * 60)

    # Step 3: List documents
    list_documents(args.token)

    # Step 4: Get statistics
    get_stats(args.token)

    # Step 5: Cleanup (optional)
    if document_id:
        print("\n" + "=" * 60)
        response = input(f"\n🗑️  Delete test document {document_id}? (y/n): ")
        if response.lower() == 'y':
            delete_document(args.token, document_id)

    print("\n" + "=" * 60)
    print("✅ Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
