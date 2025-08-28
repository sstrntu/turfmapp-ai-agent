"""Models package.

Avoid importing heavy ORM-based modules at package import time.
Submodules should be imported directly, e.g. `from app.models.auth import PublicUser`.
"""

__all__ = []