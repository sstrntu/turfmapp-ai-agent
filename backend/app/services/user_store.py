from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.auth import User, PublicUser


def upsert_user(db: Session, *, id: str, email: str, name: str | None, avatar_url: str | None) -> PublicUser:
    user = db.get(User, id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user is None:
        user = User(
            id=id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            last_login_at=now,
        )
        db.add(user)
    else:
        user.email = email
        user.name = name
        user.avatar_url = avatar_url
        user.last_login_at = now
    db.commit()
    db.refresh(user)
    return PublicUser(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        last_login_at=user.last_login_at,
    )


def get_public_user_by_id(db: Session, id: str) -> Optional[PublicUser]:
    user = db.get(User, id)
    if not user:
        return None
    return PublicUser(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        last_login_at=user.last_login_at,
    )


