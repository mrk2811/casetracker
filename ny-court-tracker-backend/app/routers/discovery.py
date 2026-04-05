"""
Case discovery API endpoints.

Handles weekly case detection settings, discovered case listing,
and accept/dismiss actions for discovered cases.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.schemas import (
    DiscoverySettingsUpdate,
    DiscoverySettingsOut,
    DiscoveredCaseOut,
    DiscoveryAcceptResponse,
    DiscoveryDismissResponse,
    DiscoveryRunResponse,
)
from app.discovery.engine import (
    get_discovery_settings,
    create_or_update_discovery_settings,
    get_pending_discoveries,
    get_all_discoveries,
    accept_discovered_case,
    dismiss_discovered_case,
    run_discovery_for_user,
)

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


# ─── Discovery Settings ───

@router.get("/settings", response_model=DiscoverySettingsOut)
async def get_settings(user_id: int = Depends(get_current_user_id)):
    """Get discovery settings for the current user."""
    settings = get_discovery_settings(user_id)
    if not settings:
        # Auto-create default settings using user's attorney info
        from app.database import get_db
        with get_db() as conn:
            user = conn.execute(
                "SELECT first_name, last_name, attorney_reg_number FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

        attorney_name = None
        attorney_reg = None
        if user:
            attorney_name = f"{user['first_name']} {user['last_name']}"
            attorney_reg = user["attorney_reg_number"]

        settings = create_or_update_discovery_settings(
            user_id=user_id,
            enabled=True,
            attorney_name=attorney_name,
            attorney_reg_number=attorney_reg,
        )

    return DiscoverySettingsOut(
        id=settings["id"],
        user_id=settings["user_id"],
        enabled=bool(settings["enabled"]),
        attorney_name=settings.get("attorney_name"),
        attorney_reg_number=settings.get("attorney_reg_number"),
        search_courts=settings.get("search_courts") or "ny_webcivil,ny_webcrimin",
        search_county=settings.get("search_county"),
        last_run_at=settings.get("last_run_at"),
        next_run_at=settings.get("next_run_at"),
    )


@router.put("/settings", response_model=DiscoverySettingsOut)
async def update_settings(
    data: DiscoverySettingsUpdate, user_id: int = Depends(get_current_user_id)
):
    """Update discovery settings for the current user."""
    settings = create_or_update_discovery_settings(
        user_id=user_id,
        enabled=data.enabled if data.enabled is not None else True,
        attorney_name=data.attorney_name,
        attorney_reg_number=data.attorney_reg_number,
        search_courts=data.search_courts,
        search_county=data.search_county,
    )

    return DiscoverySettingsOut(
        id=settings["id"],
        user_id=settings["user_id"],
        enabled=bool(settings["enabled"]),
        attorney_name=settings.get("attorney_name"),
        attorney_reg_number=settings.get("attorney_reg_number"),
        search_courts=settings.get("search_courts") or "ny_webcivil,ny_webcrimin",
        search_county=settings.get("search_county"),
        last_run_at=settings.get("last_run_at"),
        next_run_at=settings.get("next_run_at"),
    )


# ─── Discovered Cases ───

@router.get("", response_model=list[DiscoveredCaseOut])
async def list_discoveries(
    status: Optional[str] = None,
    limit: int = 50,
    user_id: int = Depends(get_current_user_id),
):
    """
    List discovered cases with optional status filter.

    - status: 'pending', 'accepted', or 'dismissed'
    - limit: max number to return (default 50)
    """
    if status and status not in ("pending", "accepted", "dismissed"):
        raise HTTPException(status_code=400, detail="status must be 'pending', 'accepted', or 'dismissed'")

    discoveries = get_all_discoveries(user_id, status=status, limit=limit)

    return [
        DiscoveredCaseOut(
            id=d["id"],
            user_id=d["user_id"],
            index_number=d["index_number"],
            court_type=d["court_type"],
            county=d.get("county"),
            court_system=d.get("court_system"),
            plaintiff=d.get("plaintiff"),
            defendant=d.get("defendant"),
            case_status=d.get("case_status"),
            last_action=d.get("last_action"),
            last_action_date=d.get("last_action_date"),
            source_adapter=d.get("source_adapter"),
            status=d["status"],
            notification_id=d.get("notification_id"),
            discovered_at=d["discovered_at"],
            resolved_at=d.get("resolved_at"),
        )
        for d in discoveries
    ]


@router.get("/pending-count")
async def get_pending_count(user_id: int = Depends(get_current_user_id)):
    """Get the count of pending discovered cases."""
    pending = get_pending_discoveries(user_id)
    return {"count": len(pending)}


@router.post("/{discovery_id}/accept", response_model=DiscoveryAcceptResponse)
async def accept_discovery(discovery_id: int, user_id: int = Depends(get_current_user_id)):
    """
    Accept a discovered case — adds it to the user's tracked cases.
    """
    result = accept_discovered_case(discovery_id, user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return DiscoveryAcceptResponse(
        status=result["status"],
        case_id=result.get("case_id"),
        message=result["message"],
    )


@router.post("/{discovery_id}/dismiss", response_model=DiscoveryDismissResponse)
async def dismiss_discovery(discovery_id: int, user_id: int = Depends(get_current_user_id)):
    """
    Dismiss a discovered case — user doesn't want to track it.
    """
    result = dismiss_discovered_case(discovery_id, user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return DiscoveryDismissResponse(
        status=result["status"],
        message=result["message"],
    )


# ─── Manual Trigger ───

@router.post("/trigger", response_model=DiscoveryRunResponse)
async def trigger_discovery(user_id: int = Depends(get_current_user_id)):
    """
    Manually trigger case discovery for the current user.
    Useful for testing or immediate scanning.
    """
    settings = get_discovery_settings(user_id)
    if not settings:
        raise HTTPException(status_code=400, detail="Discovery settings not configured. Set up your attorney name first.")

    if not settings.get("attorney_name"):
        raise HTTPException(status_code=400, detail="Attorney name required for case discovery.")

    result = await run_discovery_for_user(user_id, settings)

    return DiscoveryRunResponse(
        users_checked=1,
        total_discoveries=result["new_discoveries"],
        errors=len(result.get("errors", [])),
    )
