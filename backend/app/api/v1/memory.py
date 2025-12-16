from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core.jwt_auth import get_current_user_from_token
from ...database import get_db_pool
from ...llamaindex.memory.user_memory import UserMemory


class MemoryFact(BaseModel):
    key: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)


class MemoryApprovalRequest(BaseModel):
    facts: List[MemoryFact]
    conversation_id: Optional[str] = None


router = APIRouter()


@router.post("/approve", summary="Approve saving extracted user facts")
async def approve_memory(
    request: MemoryApprovalRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    if not request.facts:
        raise HTTPException(status_code=400, detail="No facts provided")

    user_id = current_user["id"]

    user_memory = UserMemory(user_id=user_id, db_pool=await get_db_pool())
    await user_memory.load_from_database()

    saved = 0
    for fact in request.facts:
        await user_memory.save_fact(
            key=fact.key.lower().replace(" ", "_"),
            value=fact.value,
            confidence=0.9,
            source_conversation_id=request.conversation_id,
        )
        saved += 1

    return {"status": "ok", "saved": saved}
