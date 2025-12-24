"""Repository for problem type operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.problem_type import ProblemType
from api.database.repositories.base import BaseRepository


class ProblemTypeRepository(BaseRepository[ProblemType]):
    """Repository for problem type CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ProblemType)

    async def get_all_active(self) -> List[ProblemType]:
        """Get all active problem types ordered by sort_order."""
        result = await self.session.execute(
            select(ProblemType)
            .where(ProblemType.is_active == True)
            .order_by(ProblemType.sort_order, ProblemType.name)
        )
        return list(result.scalars().all())

    async def get_all_ordered(self) -> List[ProblemType]:
        """Get all problem types (including inactive) ordered by sort_order."""
        result = await self.session.execute(
            select(ProblemType)
            .order_by(ProblemType.sort_order, ProblemType.name)
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional[ProblemType]:
        """Get a problem type by name."""
        result = await self.session.execute(
            select(ProblemType).where(ProblemType.name == name)
        )
        return result.scalar_one_or_none()

    async def create_type(
        self,
        name: str,
        description: Optional[str] = None,
        sort_order: int = 0,
    ) -> ProblemType:
        """Create a new problem type."""
        problem_type = ProblemType(
            name=name,
            description=description,
            sort_order=sort_order,
        )
        return await self.create(problem_type)

    async def update_type(
        self,
        id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_order: Optional[int] = None,
    ) -> Optional[ProblemType]:
        """Update a problem type."""
        problem_type = await self.get_by_id(id)
        if not problem_type:
            return None

        if name is not None:
            problem_type.name = name
        if description is not None:
            problem_type.description = description
        if is_active is not None:
            problem_type.is_active = is_active
        if sort_order is not None:
            problem_type.sort_order = sort_order

        return await self.update(problem_type)

    async def soft_delete(self, id: UUID) -> bool:
        """Soft delete a problem type (set is_active=False)."""
        problem_type = await self.get_by_id(id)
        if not problem_type:
            return False

        problem_type.is_active = False
        await self.update(problem_type)
        return True
