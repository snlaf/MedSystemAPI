from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from sqlalchemy import text
from config import Config

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    from models import Base, User, Patient, Doctor, Diagnosis, PatientDiagnosis, Measurement, Prescription, Complaint, \
        Consultation, Specialization, Department, SymptomCategory, Symptom
    from routes import bp
    app.register_blueprint(bp)

    with app.app_context():
        Base.metadata.create_all(bind=db.engine)
        init_db_business_logic()

    return app


def init_db_business_logic():
    tables = [
        "CREATE TABLE IF NOT EXISTS prescription_history (id INTEGER PRIMARY KEY AUTOINCREMENT, prescription_id INTEGER NOT NULL, patient_id INTEGER NOT NULL, doctor_id INTEGER NOT NULL, medication_name TEXT NOT NULL, quantity REAL NOT NULL, dose_unit TEXT NOT NULL, frequency TEXT NOT NULL, duration_days INTEGER NOT NULL, start_date DATETIME NOT NULL, end_date DATETIME, instructions TEXT, status TEXT NOT NULL, changed_at DATETIME NOT NULL)",
        "CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, type TEXT NOT NULL CHECK(type IN ('critical', 'warning', 'info', 'recommendation')), message TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, is_read BOOLEAN DEFAULT 0)"
    ]

    views = [
        "CREATE VIEW IF NOT EXISTS v_patient_measurements_avg AS SELECT patient_id, AVG(glucose) as avg_glucose, AVG(systolic_bp) as avg_systolic, AVG(diastolic_bp) as avg_diastolic, AVG(pulse) as avg_pulse, AVG(weight) as avg_weight FROM measurements GROUP BY patient_id",
        "CREATE VIEW IF NOT EXISTS v_patient_prescription_compliance AS SELECT patient_id, COUNT(CASE WHEN status = 'активно' THEN 1 END) * 100.0 / COUNT(*) as compliance_rate FROM prescriptions GROUP BY patient_id",
        "CREATE VIEW IF NOT EXISTS v_critical_measurements AS SELECT m.*, p.surname, p.name FROM measurements m JOIN patients p ON m.patient_id = p.id WHERE (m.systolic_bp > 180 OR m.systolic_bp < 90 OR m.diastolic_bp > 120 OR m.diastolic_bp < 60 OR m.glucose > 20 OR m.glucose < 2.5 OR m.pulse > 130 OR m.pulse < 40)",
        "CREATE VIEW IF NOT EXISTS v_patient_risk_score AS SELECT p.id, p.surname, p.name, COUNT(c.id) * 10 + SUM(CASE WHEN m.systolic_bp > 160 THEN 5 ELSE 0 END) as risk_score FROM patients p LEFT JOIN complaints c ON p.id = c.patient_id LEFT JOIN measurements m ON p.id = m.patient_id GROUP BY p.id, p.surname, p.name"
    ]

    triggers = [
        "CREATE TRIGGER IF NOT EXISTS trg_prescription_archive AFTER UPDATE ON prescriptions BEGIN INSERT INTO prescription_history (prescription_id, patient_id, doctor_id, medication_name, quantity, dose_unit, frequency, duration_days, start_date, end_date, instructions, status, changed_at) VALUES (OLD.id, OLD.patient_id, OLD.doctor_id, OLD.medication_name, OLD.quantity, OLD.dose_unit, OLD.frequency, OLD.duration_days, OLD.start_date, OLD.end_date, OLD.instructions, OLD.status, CURRENT_TIMESTAMP); END",
        "CREATE TRIGGER IF NOT EXISTS trg_measurement_validation BEFORE INSERT ON measurements BEGIN SELECT CASE WHEN NEW.systolic_bp < NEW.diastolic_bp THEN RAISE(ABORT, 'Systolic BP cannot be less than diastolic BP') WHEN NEW.glucose < 0 THEN RAISE(ABORT, 'Glucose cannot be negative') WHEN NEW.systolic_bp < 50 OR NEW.systolic_bp > 300 THEN RAISE(ABORT, 'Invalid systolic BP value') WHEN NEW.diastolic_bp < 30 OR NEW.diastolic_bp > 200 THEN RAISE(ABORT, 'Invalid diastolic BP value') WHEN NEW.pulse < 20 OR NEW.pulse > 250 THEN RAISE(ABORT, 'Invalid pulse value') WHEN NEW.weight < 10 OR NEW.weight > 500 THEN RAISE(ABORT, 'Invalid weight value') END; END"
    ]

    for stmt in tables:
        db.session.execute(text(stmt))
    db.session.commit()

    for stmt in views:
        db.session.execute(text(stmt))
    db.session.commit()

    for stmt in triggers:
        db.session.execute(text(stmt))
    db.session.commit()