"""Database metadata helpers.

Importing this module imports every model so autogenerate sees the full schema.
"""

from app.models import *  # noqa: F401,F403
from app.models import Base  # noqa: F401  (re-exported for Alembic/tests)

metadata = Base.metadata

__all__ = ["Base", "metadata"]
