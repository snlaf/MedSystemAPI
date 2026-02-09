from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
from datetime import datetime


class Complaint(Base, BaseModel):
    __tablename__ = "complaints"

    patient_id = Column(ForeignKey('patients.id'), nullable=False, index=True)
    symptom_id = Column(ForeignKey('symptoms.id'), nullable=False, index=True)
    complaint_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(String(500), nullable=True)

    patient = relationship("Patient", back_populates="complaints")
    symptom = relationship("Symptom")

    __table_args__ = (
        Index('idx_complaints_patient_date', 'patient_id', 'complaint_date'),
    )