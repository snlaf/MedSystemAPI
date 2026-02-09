from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.measurement import Measurement
from models.prescription import Prescription
from models.complaint import Complaint
from models.consultation import Consultation
from models.diagnosis import PatientDiagnosis
from datetime import datetime

bp = Blueprint('api', __name__)


@bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400

    user = User(
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role=data['role']
    )

    if data['role'] == 'patient':
        patient = Patient(
            surname=data['surname'],
            name=data['name'],
            patronim=data.get('patronim'),
            gender=data['gender'],
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d'),
            height=data.get('height'),
            weight=data.get('weight')
        )
        db.session.add(patient)
        db.session.flush()
        user.patient_id = patient.id

    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201


@bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 403

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'role': user.role.value
    }), 200


@bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': access_token}), 200


@bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200


@bp.route('/patient/profile', methods=['GET'])
@jwt_required()
def get_patient_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403

    patient = user.patient
    return jsonify({
        'id': patient.id,
        'surname': patient.surname,
        'name': patient.name,
        'patronim': patient.patronim,
        'gender': patient.gender.value,
        'birth_date': patient.birth_date.isoformat(),
        'height': patient.height,
        'weight': patient.weight,
        'email': patient.email,
        'phone': patient.phone
    }), 200


@bp.route('/patient/measurements', methods=['GET', 'POST'])
@jwt_required()
def handle_measurements():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'POST':
        data = request.get_json()
        measurement = Measurement(
            patient_id=user.patient.id,
            glucose=data.get('glucose'),
            systolic_bp=data.get('systolic_bp'),
            diastolic_bp=data.get('diastolic_bp'),
            pulse=data.get('pulse'),
            weight=data.get('weight'),
            measured_at=datetime.fromisoformat(data.get('measured_at', datetime.utcnow().isoformat()))
        )
        db.session.add(measurement)
        db.session.commit()
        return jsonify({'message': 'Measurement added', 'id': measurement.id}), 201

    measurements = Measurement.query.filter_by(patient_id=user.patient.id).order_by(
        Measurement.measured_at.desc()).limit(100).all()
    return jsonify([{
        'id': m.id,
        'glucose': m.glucose,
        'systolic_bp': m.systolic_bp,
        'diastolic_bp': m.diastolic_bp,
        'pulse': m.pulse,
        'weight': m.weight,
        'measured_at': m.measured_at.isoformat()
    } for m in measurements]), 200


@bp.route('/patient/prescriptions', methods=['GET'])
@jwt_required()
def get_prescriptions():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403

    prescriptions = Prescription.query.filter_by(patient_id=user.patient.id, status='active').all()
    return jsonify([{
        'id': p.id,
        'medication_name': p.medication_name,
        'quantity': p.quantity,
        'dose_unit': p.dose_unit,
        'frequency': p.frequency,
        'duration_days': p.duration_days,
        'start_date': p.start_date.isoformat(),
        'end_date': p.end_date.isoformat() if p.end_date else None,
        'instructions': p.instructions,
        'status': p.status.value
    } for p in prescriptions]), 200


@bp.route('/patient/complaints', methods=['GET', 'POST'])
@jwt_required()
def handle_complaints():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'POST':
        data = request.get_json()
        complaint = Complaint(
            patient_id=user.patient.id,
            symptom_id=data['symptom_id'],
            complaint_date=datetime.fromisoformat(data.get('complaint_date', datetime.utcnow().isoformat())),
            severity=data['severity'],
            description=data.get('description')
        )
        db.session.add(complaint)
        db.session.commit()
        return jsonify({'message': 'Complaint added', 'id': complaint.id}), 201

    complaints = Complaint.query.filter_by(patient_id=user.patient.id).order_by(Complaint.complaint_date.desc()).all()
    return jsonify([{
        'id': c.id,
        'symptom_id': c.symptom_id,
        'complaint_date': c.complaint_date.isoformat(),
        'severity': c.severity,
        'description': c.description
    } for c in complaints]), 200


@bp.route('/doctor/patients', methods=['GET'])
@jwt_required()
def get_patients():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'doctor' or not user.doctor:
        return jsonify({'error': 'Access denied'}), 403

    patients = Patient.query.join(Consultation).filter(Consultation.doctor_id == user.doctor.id).distinct().all()
    return jsonify([{
        'id': p.id,
        'surname': p.surname,
        'name': p.name,
        'patronim': p.patronim,
        'birth_date': p.birth_date.isoformat(),
        'gender': p.gender.value
    } for p in patients]), 200


@bp.route('/doctor/patient/<int:patient_id>/card', methods=['GET'])
@jwt_required()
def get_patient_card(patient_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'doctor' or not user.doctor:
        return jsonify({'error': 'Access denied'}), 403

    patient = Patient.query.get_or_404(patient_id)

    measurements = Measurement.query.filter_by(patient_id=patient_id).order_by(Measurement.measured_at.desc()).limit(
        20).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id).order_by(Prescription.start_date.desc()).limit(
        20).all()
    complaints = Complaint.query.filter_by(patient_id=patient_id).order_by(Complaint.complaint_date.desc()).limit(
        20).all()
    consultations = Consultation.query.filter_by(patient_id=patient_id).order_by(
        Consultation.consultation_date.desc()).limit(20).all()

    return jsonify({
        'patient': {
            'id': patient.id,
            'surname': patient.surname,
            'name': patient.name,
            'patronim': patient.patronim,
            'birth_date': patient.birth_date.isoformat(),
            'gender': patient.gender.value,
            'height': patient.height,
            'weight': patient.weight
        },
        'measurements': [{
            'id': m.id,
            'glucose': m.glucose,
            'systolic_bp': m.systolic_bp,
            'diastolic_bp': m.diastolic_bp,
            'pulse': m.pulse,
            'weight': m.weight,
            'measured_at': m.measured_at.isoformat()
        } for m in measurements],
        'prescriptions': [{
            'id': p.id,
            'medication_name': p.medication_name,
            'quantity': p.quantity,
            'dose_unit': p.dose_unit,
            'frequency': p.frequency,
            'duration_days': p.duration_days,
            'start_date': p.start_date.isoformat(),
            'end_date': p.end_date.isoformat() if p.end_date else None,
            'status': p.status.value
        } for p in prescriptions],
        'complaints': [{
            'id': c.id,
            'symptom_id': c.symptom_id,
            'complaint_date': c.complaint_date.isoformat(),
            'severity': c.severity,
            'description': c.description
        } for c in complaints],
        'consultations': [{
            'id': c.id,
            'doctor_id': c.doctor_id,
            'consultation_date': c.consultation_date.isoformat(),
            'notes': c.notes
        } for c in consultations]
    }), 200


@bp.route('/doctor/prescriptions', methods=['POST'])
@jwt_required()
def create_prescription():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'doctor' or not user.doctor:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    prescription = Prescription(
        patient_id=data['patient_id'],
        doctor_id=user.doctor.id,
        medication_name=data['medication_name'],
        quantity=data['quantity'],
        dose_unit=data['dose_unit'],
        frequency=data['frequency'],
        duration_days=data['duration_days'],
        start_date=datetime.fromisoformat(data['start_date']),
        end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
        instructions=data.get('instructions'),
        status=data.get('status', 'active')
    )
    db.session.add(prescription)
    db.session.commit()

    return jsonify({'message': 'Prescription created', 'id': prescription.id}), 201


@bp.route('/doctor/consultations', methods=['POST'])
@jwt_required()
def create_consultation():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'doctor' or not user.doctor:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    consultation = Consultation(
        patient_id=data['patient_id'],
        doctor_id=user.doctor.id,
        consultation_date=datetime.fromisoformat(data.get('consultation_date', datetime.utcnow().isoformat())),
        notes=data.get('notes')
    )
    db.session.add(consultation)
    db.session.commit()

    return jsonify({'message': 'Consultation created', 'id': consultation.id}), 201


@bp.route('/import/data', methods=['POST'])
@jwt_required()
def import_data():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    for item in data.get('patients', []):
        patient = Patient(**item)
        db.session.add(patient)
    db.session.commit()

    return jsonify({'message': 'Data imported successfully'}), 200