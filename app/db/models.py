from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, CheckConstraint
from db.database import Base
from datetime import datetime

class TelemetryStatus(str, Enum):
    HEALTHY = "healthy"
    CRITICAL = "critical"

class Telemetry(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True, index=True)
    satelliteId = Column(String(64), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    # altitude is kilometers, use float for precision
    altitude = Column(Float)
    # velocity is in kilometers per second, use float for precision 
    velocity = Column(Float)
    # assume default status of a satellite is healthy
    status = Column(SQLEnum(TelemetryStatus), default=TelemetryStatus.HEALTHY)
    # track creation in database versus timestamp of telemetry data
    created = Column(DateTime, default=datetime.utcnow)
    # updated timestamp incase a UPDATE API operation comes later
    updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('length(satelliteId) <= 64', name='check_satelliteid_length'),
        CheckConstraint('altitude >= 0', name='check_altitude_positive'),
        CheckConstraint('velocity >= 0', name='check_velocity_positive'),
    )

    