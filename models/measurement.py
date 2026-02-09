from sqlalchemy import Column, Float, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
from datetime import datetime


class Measurement(Base, BaseModel):
    __tablename__ = "measurements"

    patient_id = Column(ForeignKey('patients.id'), nullable=False, index=True)
    glucose = Column(Float, nullable=True)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    pulse = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    measured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient = relationship("Patient", back_populates="measurements")

    __table_args__ = (
        Index('idx_measurements_patient_date', 'patient_id', 'measured_at'),
    )