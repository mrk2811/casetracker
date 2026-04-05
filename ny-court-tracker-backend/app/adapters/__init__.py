"""
Court adapters package.

Provides abstract interfaces for court system integration and
concrete adapter implementations for NY courts.
"""

from app.adapters.base import CourtAdapter, DataSource, CaseSource, CourtRecord, AppearanceRecord

__all__ = [
    "CourtAdapter",
    "DataSource",
    "CaseSource",
    "CourtRecord",
    "AppearanceRecord",
]
