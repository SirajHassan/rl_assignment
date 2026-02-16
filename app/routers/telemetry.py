from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from db.database import get_db
from db.models import Telemetry, TelemetryStatus





# Pydantic Models
class TelemetryCreate(BaseModel):
    satelliteId: str = Field(..., description="Satellite ID", max_length=64)
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of telemetry data")
    altitude: float = Field(..., gt=0, description="Altitude in kilometers (km); must be a positive number")
    velocity: float = Field(..., gt=0, description="Velocity in kilometers per second (km/s); must be a positive number")
    status: TelemetryStatus = Field(
        ...,
        description="Health status of the satellite"
    )
    # Example value for Docs
    model_config = {
        "json_schema_extra": {
            "example": {
                "satelliteId": "sattelite-1",
                "timestamp": "2026-02-14T10:00:00",
                "altitude": 550.0,
                "velocity": 7.6,
                "status": "healthy"
            }
        }
    }

class TelemetryResponse(BaseModel):
    id: int
    satelliteId: str
    timestamp: datetime
    altitude: float
    velocity: float
    status: TelemetryStatus
    created: datetime
    updated: datetime
    
    # Example value for Docs
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "satelliteId": "sattelite-1",
                "timestamp": "2026-02-14T10:00:00",
                "altitude": 550.0,
                "velocity": 7.6,
                "status": "healthy",
                "created": "2026-02-15T12:30:00",
                "updated": "2026-02-15T12:30:00"
            }
        }
    }


class DeleteResponse(BaseModel):
    id: int
    message: str
    
    # Example value for Docs    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "message": "Telemetry record deleted successfully"
            }
        }
    }



# API Endpoints 
router = APIRouter(prefix="/telemetry", tags=["telemetry"])

@router.get("", response_model=Page[TelemetryResponse])
def list_satellites(
    satelliteId: Optional[str] = Query(
        default=None,
        description="Filter telemetry by satellite ID",
        max_length=64
    ),
    status: Optional[TelemetryStatus] = Query(
        default=None,
        description="Filter telemetry by health status",
    ),
    db: Session = Depends(get_db)
):
    """Return paginated telemetry data filtered by query params and ordered by timestamp descending"""

    query = db.query(Telemetry)

    if satelliteId and status:
        query = query.filter(Telemetry.satelliteId == satelliteId, Telemetry.status == status)
    elif satelliteId:
        query = query.filter(Telemetry.satelliteId == satelliteId)
    elif status:
        query = query.filter(Telemetry.status == status)

    query = query.order_by(Telemetry.timestamp.desc())

    return paginate(query)


@router.post("", response_model=TelemetryResponse)
def create_telemetry(telemetry: TelemetryCreate, db: Session = Depends(get_db)):
    """Create new telemetry record in database"""
    db_telemetry = Telemetry(**telemetry.model_dump())
    db.add(db_telemetry)
    db.commit()
    db.refresh(db_telemetry)
    return db_telemetry


@router.get("/{id}", response_model=TelemetryResponse)
def get_telemetry(id: int, db: Session = Depends(get_db)):
    """Retrieve a specific telemetry record by id"""
    telemetry = db.query(Telemetry).filter(Telemetry.id == id).first()
    if telemetry is None:
        raise HTTPException(status_code=404, detail="Telemetry record not found")
    return telemetry


@router.delete("/{id}", response_model=DeleteResponse)
def delete_telemetry(id: int, db: Session = Depends(get_db)):
    """Delete a specific telemetry record by id"""
    rows_deleted = db.query(Telemetry).filter(Telemetry.id == id).delete()
    db.commit()

    if rows_deleted == 0:
        raise HTTPException(status_code=404, detail="Telemetry record not found")

    return DeleteResponse(id=id, message="Telemetry record deleted successfully")
