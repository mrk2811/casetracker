"""
Adapter registry for managing court system adapters.

Provides a central registry to look up adapters by court system identifier.
New court systems are registered here as they are implemented.
"""

from typing import Optional

from app.adapters.base import CourtAdapter, CourtSystem
from app.adapters.ny_webcivil import NYWebCivilAdapter
from app.adapters.ny_webcrimin import NYWebCriminAdapter


_ADAPTERS: dict[str, type[CourtAdapter]] = {
    CourtSystem.NY_WEBCIVIL.value: NYWebCivilAdapter,
    CourtSystem.NY_WEBCRIMIN.value: NYWebCriminAdapter,
}

# Singleton instances (created on first use)
_instances: dict[str, CourtAdapter] = {}


def get_adapter(court_system: str) -> Optional[CourtAdapter]:
    """Get an adapter instance for the given court system."""
    if court_system not in _ADAPTERS:
        return None
    if court_system not in _instances:
        _instances[court_system] = _ADAPTERS[court_system]()
    return _instances[court_system]


def list_adapters() -> list[dict]:
    """List all registered court system adapters."""
    result = []
    for system_id, adapter_cls in _ADAPTERS.items():
        adapter = get_adapter(system_id)
        if adapter:
            result.append({
                "court_system": system_id,
                "display_name": adapter.display_name,
                "state": adapter.state,
            })
    return result
