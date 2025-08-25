from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.auth import PublicUser, User


router = APIRouter()


def require_admin(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")) -> None:
    expected = os.getenv("ADMIN_TOKEN")
    if not expected:
        # Default for development only. Set ADMIN_TOKEN in production.
        expected = "dev-admin"
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@router.get("/users", response_model=List[PublicUser], dependencies=[Depends(require_admin)])
def list_users(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> List[PublicUser]:
    stmt = (
        select(User)
        .order_by(desc(User.last_login_at.nullslast()))
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).scalars().all()
    return [
        PublicUser(
            id=u.id,
            email=u.email,
            name=u.name,
            avatar_url=u.avatar_url,
            last_login_at=u.last_login_at,
        )
        for u in rows
    ]


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
def delete_user(user_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"ok": True}


