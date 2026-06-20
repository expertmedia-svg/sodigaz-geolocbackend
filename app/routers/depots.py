from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Depot, LocatorSession, Location, User
from app.schemas import DepotResponse, DepotCreate, DepotUpdate, DepotMapResponse, DepotMapFilters, LocatorStatsResponse, LocatorSessionResponse, LocationHistoryResponse
from app.auth import get_current_user, get_current_user_optional
import io
import csv

admin_router = APIRouter(prefix="/admin/depots", tags=["admin-depots"])
public_router = APIRouter(prefix="/user/public/depots", tags=["public-depots"])
locator_router = APIRouter(prefix="/locator", tags=["locator-tracking"])

# --- PUBLIC ROUTER (Used by Flutter App & Public Map) ---

@public_router.get("/map", response_model=DepotMapResponse)
def get_depots_map(
    city: Optional[str] = Query(default=None),
    quartier: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Retrieve all active depots for the geographic map with filters."""
    q = db.query(Depot).filter(Depot.is_active == True)
    
    if city:
        q = q.filter(Depot.city.ilike(f"%{city}%"))
    if quartier:
        q = q.filter(Depot.quartier.ilike(f"%{quartier}%"))
    if query:
        search = f"%{query}%"
        q = q.filter(
            (Depot.name.ilike(search)) | 
            (Depot.address.ilike(search)) | 
            (Depot.plv_code.ilike(search)) |
            (Depot.description.ilike(search))
        )
        
    items = q.all()
    
    # Extract unique filter values from all active depots
    all_depots = db.query(Depot).filter(Depot.is_active == True).all()
    cities = sorted(list(set(d.city for d in all_depots if d.city)))
    quartiers = sorted(list(set(d.quartier for d in all_depots if d.quartier)))
    
    return {
        "items": items,
        "filters": {
            "cities": cities,
            "quartiers": quartiers
        }
    }

@public_router.get("/{depot_id}", response_model=DepotResponse)
def get_depot_public(depot_id: int, db: Session = Depends(get_db)):
    """Get single depot details."""
    depot = db.query(Depot).filter(Depot.id == depot_id, Depot.is_active == True).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
    return depot


# --- ADMIN ROUTER (Used by Locator Admin Dashboard for CRUD) ---

@admin_router.get("", response_model=List[DepotResponse])
def get_all_depots_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all depots including inactive ones (Admin only)."""
    return db.query(Depot).all()

@admin_router.post("", response_model=DepotResponse)
def create_depot_admin(
    data: DepotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new depot (Admin only)."""
    # Check uniqueness of PLV Code if provided
    if data.plv_code:
        exists = db.query(Depot).filter(Depot.plv_code == data.plv_code).first()
        if exists:
            raise HTTPException(status_code=400, detail="PLV Code already registered")
            
    # Check uniqueness of Name
    exists = db.query(Depot).filter(Depot.name.ilike(data.name)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Depot name already registered")
        
    depot = Depot(**data.dict())
    depot.is_active = (depot.status == "Actif")
    db.add(depot)
    db.commit()
    db.refresh(depot)
    return depot

@admin_router.put("/{depot_id}", response_model=DepotResponse)
def update_depot_admin(
    depot_id: int,
    data: DepotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a depot's info or inventory (Admin only)."""
    depot = db.query(Depot).filter(Depot.id == depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
        
    for key, value in data.dict(exclude_unset=True).items():
        setattr(depot, key, value)
        
    depot.is_active = (depot.status == "Actif")
    db.commit()
    db.refresh(depot)
    return depot

@admin_router.delete("/{depot_id}")
def delete_depot_admin(
    depot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a depot permanently (Admin only)."""
    depot = db.query(Depot).filter(Depot.id == depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
        
    db.delete(depot)
    db.commit()
    return {"message": f"Depot '{depot.name}' deleted successfully"}


class BulkDeleteRequest(BaseModel):
    ids: List[int]

@admin_router.post("/bulk-delete")
def bulk_delete_depots(
    data: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk delete depots (Admin / Network Team)."""
    if not data.ids:
        raise HTTPException(status_code=400, detail="No IDs provided for deletion")
    
    deleted_count = db.query(Depot).filter(Depot.id.in_(data.ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Successfully deleted {deleted_count} depots"}


@admin_router.post("/import-csv")
async def import_depots_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk import depots from uploaded CSV file."""
    try:
        contents = await file.read()
        text = contents.decode("utf-8", errors="replace")
        
        # Import logic using our imported utility
        from import_locator_csv import import_depots_csv_text
        created, updated, skipped, detected_format = import_depots_csv_text(text, db)
        
        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "format": detected_format
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=f"Erreur lors de l'importation du fichier CSV : {str(e)}"
        )


@admin_router.post("/import-json")
async def import_depots_json(
    depots_list: List[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk import depots from JSON payload."""
    try:
        from import_locator_csv import _upsert_depot_from_record, _parse_float, _parse_int, _clean
        created = 0
        updated = 0
        skipped = 0
        
        existing_names = {depot.name.lower() for depot in db.query(Depot).all()}
        
        for record in depots_list:
            name = _clean(record.get('name') or record.get('nom') or record.get('title'))
            latitude = _parse_float(record.get('latitude') or record.get('lat'))
            longitude = _parse_float(record.get('longitude') or record.get('lng'))
            if not name or latitude is None or longitude is None:
                skipped += 1
                continue
                
            result = _upsert_depot_from_record(
                db,
                existing_names,
                name=name,
                latitude=latitude,
                longitude=longitude,
                address=_clean(record.get('address') or record.get('adresse')) or name,
                city=_clean(record.get('city') or record.get('ville')) or 'Ouagadougou',
                quartier=_clean(record.get('quartier')),
                plv_code=_clean(record.get('plv_code') or record.get('code_plv')),
                maps_url=_clean(record.get('maps_url') or record.get('google_maps')),
                phone=_clean(record.get('phone') or record.get('telephone') or record.get('tel')) or '',
                capacity_6kg=_parse_int(record.get('capacity_6kg')),
                capacity_12kg=_parse_int(record.get('capacity_12kg')),
                status=_clean(record.get('status') or record.get('statut')) or 'Actif',
                comments=_clean(record.get('comments') or record.get('commentaires')),
            )
            if result == 'created':
                created += 1
            else:
                updated += 1
                
        db.commit()
        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "skipped": skipped
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=f"Erreur lors de l'importation du JSON : {str(e)}"
        )


# --- LOCATOR TRACKING ROUTER (Used by Flutter App for GPS / Sessions) ---

@locator_router.get("/stats", response_model=LocatorStatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall tracking statistics for dashboard."""
    total_depots = db.query(Depot).filter(Depot.is_active == True).count()
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_usage = db.query(LocatorSession).filter(LocatorSession.created_at >= today_start).count()
    active_sessions = db.query(LocatorSession).filter(LocatorSession.is_active == True).count()
    total_locations = db.query(Location).count()
    
    # Generate simple usage trend for last 7 days
    usage_trend = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = db.query(LocatorSession).filter(
            LocatorSession.created_at >= day_start,
            LocatorSession.created_at <= day_end
        ).count()
        usage_trend.append({"date": day.strftime("%d/%m"), "sessions": count})
        
    # Top 5 most active depots (most sessions)
    top_depots = []
    from sqlalchemy import func
    top_results = db.query(
        LocatorSession.depot_id, 
        func.count(LocatorSession.id).label("count")
    ).group_by(LocatorSession.depot_id).order_by(func.count(LocatorSession.id).desc()).limit(5).all()
    
    for depot_id, count in top_results:
        depot = db.query(Depot).filter(Depot.id == depot_id).first()
        if depot:
            top_depots.append({"name": depot.name, "sessions": count})
            
    return {
        "total_depots": total_depots,
        "today_usage": today_usage,
        "active_sessions": active_sessions,
        "total_locations": total_locations,
        "usage_trend": usage_trend,
        "top_depots": top_depots
    }

@locator_router.post("/sessions")
def start_session(
    depot_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Log the initiation of a tracking map viewing session (either anonymous or logged-in)."""
    depot = db.query(Depot).filter(Depot.id == depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
        
    session = LocatorSession(
        depot_id=depot_id,
        user_id=current_user.id if current_user else None,
        is_active=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "message": "Session started"}

@locator_router.post("/sessions/{session_id}/end")
def end_session(session_id: int, db: Session = Depends(get_db)):
    """Mark a tracking session as ended."""
    session = db.query(LocatorSession).filter(LocatorSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session.is_active = False
    session.ended_at = datetime.utcnow()
    db.commit()
    return {"message": "Session ended successfully"}

@locator_router.post("/locations")
def log_gps_location(
    depot_id: int,
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Log an active client location query (anonymous tracking)."""
    depot = db.query(Depot).filter(Depot.id == depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")
        
    location = Location(
        depot_id=depot_id,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy
    )
    db.add(location)
    db.commit()
    return {"status": "logged"}

@locator_router.get("/sessions", response_model=List[LocatorSessionResponse])
def get_all_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all user sessions for tracking usage."""
    sessions = db.query(LocatorSession).order_by(LocatorSession.created_at.desc()).limit(100).all()
    results = []
    for s in sessions:
        results.append({
            "id": s.id,
            "depot_id": s.depot_id,
            "depot_name": s.depot.name if s.depot else "Unknown Depot",
            "username": s.user.username if s.user else "Anonyme",
            "is_active": s.is_active,
            "created_at": s.created_at,
            "ended_at": s.ended_at
        })
    return results

@locator_router.get("/history", response_model=List[LocationHistoryResponse])
def get_location_history(
    depot_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all location logging records (Admin only)."""
    q = db.query(Location)
    if depot_id:
        q = q.filter(Location.depot_id == depot_id)
        
    locations = q.order_by(Location.timestamp.desc()).limit(limit).all()
    results = []
    for l in locations:
        results.append({
            "id": l.id,
            "depot_id": l.depot_id,
            "depot_name": l.depot.name if l.depot else "Unknown Depot",
            "latitude": l.latitude,
            "longitude": l.longitude,
            "accuracy": l.accuracy,
            "timestamp": l.timestamp
        })
    return results
