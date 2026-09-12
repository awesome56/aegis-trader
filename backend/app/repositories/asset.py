"""Asset repository: normalised symbol lookups and creation."""

from __future__ import annotations

from sqlalchemy import func, select

from app.market.domain.models import AssetSearchResult
from app.models.asset import Asset
from app.models.enums import AssetClass
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    async def get_by_symbol(self, symbol: str) -> Asset | None:
        normalized = symbol.strip().upper()
        stmt = select(Asset).where(Asset.symbol == normalized).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, *, limit: int = 25) -> list[Asset]:
        term = f"%{query.strip().upper()}%"
        stmt = (
            select(Asset)
            .where(func.upper(Asset.symbol).like(term))
            .order_by(Asset.symbol)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_from_result(self, result: AssetSearchResult) -> Asset:
        """Create or return the asset for a provider search result.

        Symbols are stored upper-cased so ``aapl`` and ``AAPL`` cannot become
        separate assets.
        """
        existing = await self.get_by_symbol(result.symbol)
        if existing is not None:
            return existing
        asset = Asset(
            symbol=result.symbol.strip().upper(),
            name=result.name,
            asset_class=result.asset_class or AssetClass.EQUITY,
            exchange=result.exchange,
            currency=result.currency or "USD",
        )
        return await self.add(asset)
