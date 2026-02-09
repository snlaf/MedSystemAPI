from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, BaseModel


class Diagnosis(Base, BaseModel):
    __tablename__ = "diagnoses"

    mkb10_code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)


class PatientDiagnosis(Base, BaseModel):
    __tablename__ = "patient_diagnoses"

    patient_id = Column(ForeignKey('patients.id'), nullable=False, index=True)
    diagnosis_id = Column(ForeignKey('diagnoses.id'), nullable=False, index=True)
    diagnosed_at = Column(BaseModel.updated_at.type, nullable=False)
    notes = Column(String(500), nullable=True)

    patient = relationship("Patient", back_populates="diagnoses")
    diagnosis = relationship("Diagnosis")