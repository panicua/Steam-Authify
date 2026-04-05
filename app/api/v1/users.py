from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Actor, get_current_actor, require_admin
from app.core.audit import record_audit
from app.database import get_session
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    if not actor.is_admin:
        stmt = select(User).where(User.id == actor.user_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    stmt = select(User).order_by(User.id).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(get_current_actor),
):
    if not actor.is_admin and user_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_admin),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await record_audit(
        session,
        actor_type=actor.type,
        actor_id=actor.id_str,
        entity_type="user",
        entity_id=user_id,
        action="update",
        payload=data.model_dump(exclude_unset=True),
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_admin),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    await record_audit(
        session,
        actor_type=actor.type,
        actor_id=actor.id_str,
        entity_type="user",
        entity_id=user_id,
        action="delete",
        payload={"username": user.username},
    )
    await session.delete(user)
    await session.commit()
