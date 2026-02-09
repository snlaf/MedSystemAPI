from sqlalchemy import Column, String, Date, Float, Integer, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
from .enums import GenderEnum


class Patient(Base, BaseModel):
    __tablename__ = "patients"

    surname = Column(String(50), nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    patronim = Column(String(50), nullable=True)
    gender = Column(SQLEnum(GenderEnum), nullable=False)
    birth_date = Column(Date, nullable=False, index=True)
    city = Column(String(100), nullable=True)
    street = Column(String(100), nullable=True)
    building = Column(String(20), nullable=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)

    user = relationship("User", back_populates="patient", uselist=False)
    complaints = relationship("Complaint", back_populates="patient", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="patient", cascade="all, delete-orphan")
    measurements = relationship("Measurement", back_populates="patient", cascade="all, delete-orphan")
    consultations_as_patient = relationship("Consultation", foreign_keys="[Consultation.patient_id]",
                                            back_populates="patient", cascade="all, delete-orphan")
    diagnoses = relationship("PatientDiagnosis", back_populates="patient", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_patients_full_name', 'surname', 'name', 'patronim'),
        Index('idx_patients_birth_date', 'birth_date'),
    )