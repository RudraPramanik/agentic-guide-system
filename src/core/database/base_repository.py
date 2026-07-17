"""Generic async repository base — soft-delete aware, flush-only writes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import func, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from src.core.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.core.pagination import PageParams

ModelT = TypeVar("ModelT", bound=DeclarativeBase)
IDT = TypeVar("IDT")


class BaseRepository(Generic[ModelT, IDT]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Model class resolution ──

    @property
    def model_class(self) -> type[ModelT]:
        """Resolve the concrete model class from Generic[ModelT, IDT] type parameters."""
        import typing

        orig = getattr(self.__class__, "__orig_bases__", [])
        for base in orig:
            args = typing.get_args(base)
            if args:
                return args[0]
        raise TypeError(f"Cannot resolve model_class for {self.__class__.__name__}")

    def _soft_delete_filter(self):
        """WHERE deleted_at IS NULL if SoftDeleteMixin; otherwise no-op (true())."""
        if hasattr(self.model_class, "deleted_at"):
            return self.model_class.deleted_at.is_(None)
        return true()

    # ── Read ──

    async def get_by_id(self, id: IDT) -> ModelT | None:
        """Return model by primary key, or None if not found or soft-deleted."""
        stmt = select(self.model_class).where(
            self.model_class.id == id,
            self._soft_delete_filter(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, id: IDT) -> ModelT:
        """Return model by primary key or raise NotFoundError (404)."""
        obj = await self.get_by_id(id)
        if obj is None:
            raise NotFoundError(
                message=f"{self.model_class.__name__} not found",
                details={"id": str(id)},
            )
        return obj

    async def exists(self, **kwargs: Any) -> bool:
        """Return True if any non-deleted record matches all kwargs as equality filters."""
        stmt = select(self.model_class.id).where(
            self._soft_delete_filter(),
            *[getattr(self.model_class, k) == v for k, v in kwargs.items()],
        )
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def list_paginated(
        self,
        filters: dict[str, Any],
        params: PageParams,
        order_by_col: Any = None,
        order_desc: bool = True,
    ) -> tuple[list[ModelT], int]:
        """Return (page items, total count). Equality filters only; excludes soft-deleted."""
        base_stmt = select(self.model_class).where(self._soft_delete_filter())

        for col_name, value in filters.items():
            col = getattr(self.model_class, col_name)
            base_stmt = base_stmt.where(col == value)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total: int = (await self.session.execute(count_stmt)).scalar_one()

        if order_by_col is None:
            order_by_col = getattr(self.model_class, "created_at", self.model_class.id)

        ordered = base_stmt.order_by(
            order_by_col.desc() if order_desc else order_by_col.asc()
        )
        paginated = ordered.offset(params.offset).limit(params.size)
        items = list((await self.session.execute(paginated)).scalars().all())

        return items, total

    # ── Write ──

    async def create(self, data: dict[str, Any]) -> ModelT:
        """Insert a new record. Flushes but does NOT commit."""
        obj = self.model_class(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: IDT, data: dict[str, Any]) -> ModelT:
        """Update fields on an existing non-deleted record. Flushes but does NOT commit."""
        obj = await self.get_by_id_or_raise(id)
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, id: IDT) -> None:
        """Set deleted_at = now(). Flushes but does NOT commit."""
        if not hasattr(self.model_class, "deleted_at"):
            raise AttributeError(
                f"{self.model_class.__name__} does not support soft delete "
                f"(no deleted_at column)"
            )
        obj = await self.get_by_id_or_raise(id)
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
