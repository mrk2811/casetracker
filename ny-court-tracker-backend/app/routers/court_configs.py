from fastapi import APIRouter, Depends
from app.database import get_db
from app.auth import get_current_user_id
from app.schemas import CourtConfigOut
from app.adapters.registry import list_adapters

router = APIRouter(prefix="/api/court-configs", tags=["court_configs"])


@router.get("", response_model=list[CourtConfigOut])
async def get_court_configs(user_id: int = Depends(get_current_user_id)):
    """List all available court system configurations."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM court_configs WHERE enabled = 1 ORDER BY state, display_name"
        ).fetchall()

    return [
        CourtConfigOut(
            id=row["id"],
            state=row["state"],
            court_system=row["court_system"],
            display_name=row["display_name"],
            base_url=row["base_url"],
            adapter_class=row["adapter_class"],
            enabled=bool(row["enabled"]),
        )
        for row in rows
    ]


@router.get("/adapters")
async def get_available_adapters(user_id: int = Depends(get_current_user_id)):
    """List all registered court system adapters and their status."""
    return list_adapters()
