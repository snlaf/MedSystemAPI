from sqlalchemy import Column, String, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, BaseModel


class Doctor(Base, BaseModel):
    __tablename__ = "doctors"

    surname = Column(String(50), nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    patronim = Column(String(50), nullable=True)
    specialization_id = Column(ForeignKey('specializations.id'), nullable=False, index=True)
    department_id = Column(ForeignKey('departments.id'), nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)

    user = relationship("User", back_populates="doctor", uselist=False)
    specialization = relationship("Specialization", back_populates="doctors")
    department = relationship("Department", back_populates="doctors")
    consultations_as_doctor = relationship("Consultation", foreign_keys="[Consultation.doctor_id]",
                                           back_populates="doctor", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="doctor", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_doctors_full_name', 'surname', 'name', 'patronim'),
    )