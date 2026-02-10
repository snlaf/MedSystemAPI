from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Patient, Doctor, Measurement, Prescription, Complaint, Consultation, Symptom

bp = Blueprint('api', __name__)


@bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if db.session.query(User).filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400

    user = User(
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role=data['role']
    )

    if data['role'] == 'patient':
        from datetime import datetime
        patient = Patient(
            surname=data['surname'],
            name=data['name'],
            patronim=data.get('patronim'),
            gender=data['gender'],
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d').date(),
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
    user = db.session.query(User).filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 403

    # Преобразуем user.id в строку для JWT
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
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


@bp.route('/patient/profile', methods=['GET'])
@jwt_required()
def get_patient_profile():
    current_user_id = get_jwt_identity()
    # Преобразуем обратно в число
    user = db.session.query(User).get(int(current_user_id))
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403
    p = user.patient
    return jsonify({
        'id': p.id,
        'surname': p.surname,
        'name': p.name,
        'patronim': p.patronim,
        'gender': p.gender.value,
        'birth_date': p.birth_date.isoformat(),
        'height': p.height,
        'weight': p.weight,
        'email': p.email,
        'phone': p.phone
    }), 200


@bp.route('/patient/measurements', methods=['GET', 'POST'])
@jwt_required()
def handle_measurements():
    current_user_id = get_jwt_identity()
    user = db.session.query(User).get(int(current_user_id))
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'POST':
        data = request.get_json()
        from datetime import datetime
        m = Measurement(
            patient_id=user.patient.id,
            glucose=data.get('glucose'),
            systolic_bp=data.get('systolic_bp'),
            diastolic_bp=data.get('diastolic_bp'),
            pulse=data.get('pulse'),
            weight=data.get('weight'),
            measured_at=datetime.fromisoformat(data.get('measured_at', datetime.utcnow().isoformat()))
        )
        db.session.add(m)
        db.session.commit()
        return jsonify({'message': 'Measurement added', 'id': m.id}), 201

    measurements = db.session.query(Measurement).filter_by(patient_id=user.patient.id).order_by(
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
    current_user_id = get_jwt_identity()
    user = db.session.query(User).get(int(current_user_id))
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403

    prescriptions = db.session.query(Prescription).filter_by(patient_id=user.patient.id, status='активно').all()
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
        'status': p.status
    } for p in prescriptions]), 200


@bp.route('/patient/complaints', methods=['GET', 'POST'])
@jwt_required()
def handle_complaints():
    current_user_id = get_jwt_identity()
    user = db.session.query(User).get(int(current_user_id))
    if user.role != 'patient' or not user.patient:
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'POST':
        data = request.get_json()
        from datetime import datetime
        c = Complaint(
            patient_id=user.patient.id,
            symptom_id=data['symptom_id'],
            complaint_date=datetime.fromisoformat(data.get('complaint_date', datetime.utcnow().isoformat())),
            severity=data['severity'],
            description=data.get('description')
        )
        db.session.add(c)
        db.session.commit()
        return jsonify({'message': 'Complaint added', 'id': c.id}), 201

    complaints = db.session.query(Complaint).filter_by(patient_id=user.patient.id).order_by(
        Complaint.complaint_date.desc()).all()
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
    current_user_id = get_jwt_identity()
    user = db.session.query(User).get(int(current_user_id))
    if user.role != 'doctor' or not user.doctor:
        return jsonify({'error': 'Access denied'}), 403

    patients = db.session.query(Patient).join(Consultation).filter(
        Consultation.doctor_id == user.doctor.id).distinct().all()
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
    current_user_id = get_jwt_identity()
    user = db.session.query(User).get(int(current_user_id))
    if user.role != 'doctor' or not user.doctor:
        return jsonify({'error': 'Access denied'}), 403

    patient = db.session.query(Patient).get_or_404(patient_id)

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
        } for m in db.session.query(Measurement).filter_by(patient_id=patient_id).order_by(
            Measurement.measured_at.desc()).limit(20).all()],
        'prescriptions': [{
            'id': p.id,
            'medication_name': p.medication_name,
            'quantity': p.quantity,
            'dose_unit': p.dose_unit,
            'frequency': p.frequency,
            'duration_days': p.duration_days,
            'start_date': p.start_date.isoformat(),
            'end_date': p.end_date.isoformat() if p.end_date else None,
            'status': p.status
        } for p in db.session.query(Prescription).filter_by(patient_id=patient_id).order_by(
            Prescription.start_date.desc()).limit(20).all()],
        'complaints': [{
            'id': c.id,
            'symptom_id': c.symptom_id,
            'complaint_date': c.complaint_date.isoformat(),
            'severity': c.severity,
            'description': c.description
        } for c in db.session.query(Complaint).filter_by(patient_id=patient_id).order_by(
            Complaint.complaint_date.desc()).limit(20).all()]
    }), 200


@bp.route('/doctor/prescriptions', methods=['POST'])
@jwt_required()
def create_prescription():
    current_user_id = get_jwt_identity()
    user = db.session.query(User).get(int(current_user_id))
    if user.role != 'doctor' or not user.doctor:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    from datetime import datetime
    p = Prescription(
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
        status=data.get('status', 'активно')
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'message': 'Prescription created', 'id': p.id}), 201