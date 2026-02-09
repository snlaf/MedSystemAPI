import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash
from app import create_app, db
from models import *


def safe_str(value):
    if pd.isna(value) or value is None or str(value).strip().lower() in ['nan', 'none', '']:
        return None
    return str(value).strip()


def parse_date(date_str):
    if not date_str or pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d.%m.%y', '%y.%m.%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None


def parse_datetime(dt_str):
    if not dt_str or pd.isna(dt_str):
        return None
    dt_str = str(dt_str).strip()
    try:
        return datetime.fromisoformat(dt_str)
    except:
        return None


def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    session.add(instance)
    return instance


def import_symptom_categories():
    df = pd.read_csv('symptom_categories.csv', sep=';', encoding='cp1251')
    for _, row in df.iterrows():
        get_or_create(db.session, SymptomCategory, name=safe_str(row['Name']))


def import_symptoms():
    df = pd.read_csv('symptoms.csv', sep=',', encoding='cp1251')
    for _, row in df.iterrows():
        category = db.session.query(SymptomCategory).filter_by(name=safe_str(row['CategoryName'])).first()
        if category:
            get_or_create(db.session, Symptom,
                          name=safe_str(row['Name']),
                          category_id=category.id,
                          description=safe_str(row.get('Description'))
                          )


def import_diagnoses():
    df = pd.read_csv('diagnoses.csv', sep=';', encoding='cp1251')
    for _, row in df.iterrows():
        get_or_create(db.session, Diagnosis,
                      mkb10_code=safe_str(row['Код МКБ-10']),
                      name=safe_str(row['Название диагноза']),
                      category=safe_str(row['Категория'])
                      )


def import_specializations_departments():
    df = pd.read_csv('doctors.csv', sep=',', encoding='cp1251', header=None, skiprows=1)
    df.columns = ['surname', 'name', 'patronim', 'specialization', 'department', 'email', 'phone']

    for spec in df['specialization'].dropna().unique():
        get_or_create(db.session, Specialization, name=safe_str(spec))
    for dept in df['department'].dropna().unique():
        get_or_create(db.session, Department, name=safe_str(dept))


def import_doctors():
    df = pd.read_csv('doctors.csv', sep=',', encoding='cp1251', header=None, skiprows=1)
    df.columns = ['surname', 'name', 'patronim', 'specialization', 'department', 'email', 'phone']

    for _, row in df.iterrows():
        spec = db.session.query(Specialization).filter_by(name=safe_str(row['specialization'])).first()
        dept = db.session.query(Department).filter_by(name=safe_str(row['department'])).first()
        if spec and dept:
            doctor = get_or_create(db.session, Doctor,
                                   surname=safe_str(row['surname']),
                                   name=safe_str(row['name']),
                                   patronim=safe_str(row['patronim']),
                                   specialization_id=spec.id,
                                   department_id=dept.id,
                                   defaults={
                                       'email': safe_str(row['email']),
                                       'phone': safe_str(row['phone'])
                                   }
                                   )
            db.session.flush()

            email = safe_str(row['email'])
            if email:
                user = get_or_create(db.session, User,
                                     email=email,
                                     defaults={
                                         'password_hash': generate_password_hash('default123'),
                                         'role': 'doctor',
                                         'is_active': True,
                                         'doctor_id': doctor.id
                                     }
                                     )
                db.session.flush()


def import_patients():
    df = pd.read_csv('patient.csv', sep=',', encoding='cp1251', header=None, skiprows=1)
    df.columns = ['surname', 'name', 'patronim', 'gender', 'city', 'street', 'building', 'email', 'birth_date', 'phone']

    for _, row in df.iterrows():
        email = safe_str(row['email'])
        if not email:
            continue

        gender_val = safe_str(row['gender'])
        gender = 'м' if gender_val and gender_val.lower() in ['м', 'мужской', 'муж'] else 'ж'

        patient = get_or_create(db.session, Patient,
                                email=email,
                                defaults={
                                    'surname': safe_str(row['surname']),
                                    'name': safe_str(row['name']),
                                    'patronim': safe_str(row['patronim']),
                                    'gender': gender,
                                    'birth_date': parse_date(row['birth_date']),
                                    'city': safe_str(row['city']),
                                    'street': safe_str(row['street']),
                                    'building': safe_str(row['building']),
                                    'phone': safe_str(row['phone']),
                                    'height': float(row['height']) if 'height' in df.columns and pd.notna(
                                        row.get('height')) and safe_str(row.get('height')) else None,
                                    'weight': float(row['weight']) if 'weight' in df.columns and pd.notna(
                                        row.get('weight')) and safe_str(row.get('weight')) else None
                                }
                                )
        db.session.flush()

        user = get_or_create(db.session, User,
                             email=email,
                             defaults={
                                 'password_hash': generate_password_hash('default123'),
                                 'role': 'patient',
                                 'is_active': True,
                                 'patient_id': patient.id
                             }
                             )
        db.session.flush()


def import_prescriptions():
    try:
        df = pd.read_csv('prescriptions.csv', sep=',', encoding='cp1251', header=None, skiprows=1)
        df.columns = ['patient_surname', 'patient_name', 'patient_patronim', 'doctor_surname', 'doctor_name',
                      'doctor_patronim', 'medication_name', 'quantity', 'dose_unit', 'frequency', 'duration_days',
                      'start_date', 'end_date', 'instructions', 'status', 'created_at']
    except FileNotFoundError:
        print("Файл prescriptions.csv не найден, пропускаем импорт назначений")
        return

    patients = {f"{p.surname} {p.name} {p.patronim or ''}".strip().lower(): p for p in db.session.query(Patient).all()}
    doctors = {f"{d.surname} {d.name} {d.patronim or ''}".strip().lower(): d for d in db.session.query(Doctor).all()}

    for _, row in df.iterrows():
        patient_key = f"{row['patient_surname']} {row['patient_name']} {row['patient_patronim'] or ''}".strip().lower()
        doctor_key = f"{row['doctor_surname']} {row['doctor_name']} {row['doctor_patronim'] or ''}".strip().lower()

        patient = patients.get(patient_key)
        doctor = doctors.get(doctor_key)

        if patient and doctor:
            status = 'активно' if str(row['status']).strip().lower() in ['активно', '1', 'active'] else 'завершено'

            prescription = Prescription(
                patient_id=patient.id,
                doctor_id=doctor.id,
                medication_name=safe_str(row['medication_name']),
                quantity=float(row['quantity']) if pd.notna(row['quantity']) else 0.0,
                dose_unit=safe_str(row['dose_unit']),
                frequency=safe_str(row['frequency']),
                duration_days=int(row['duration_days']) if pd.notna(row['duration_days']) else 0,
                start_date=parse_datetime(row['start_date']),
                end_date=parse_datetime(row['end_date']) if pd.notna(row['end_date']) else None,
                instructions=safe_str(row['instructions']),
                status=status
            )
            db.session.add(prescription)


def import_complaints():
    try:
        df = pd.read_csv('patient_complaints.csv', sep=',', encoding='cp1251', header=None, skiprows=1)
        df.columns = ['patient_surname', 'patient_name', 'patient_patronim', 'symptom_name', 'complaint_date',
                      'severity', 'description']
    except FileNotFoundError:
        print("Файл patient_complaints.csv не найден, пропускаем импорт жалоб")
        return

    patients = {f"{p.surname} {p.name} {p.patronim or ''}".strip().lower(): p for p in db.session.query(Patient).all()}
    symptoms = {s.name.strip().lower(): s for s in db.session.query(Symptom).all()}

    for _, row in df.iterrows():
        patient_key = f"{row['patient_surname']} {row['patient_name']} {row['patient_patronim'] or ''}".strip().lower()
        patient = patients.get(patient_key)
        symptom = symptoms.get(safe_str(row['symptom_name']).lower())

        if patient and symptom:
            complaint = Complaint(
                patient_id=patient.id,
                symptom_id=symptom.id,
                complaint_date=parse_datetime(row['complaint_date']) or datetime.utcnow(),
                severity=safe_str(row['severity']),
                description=safe_str(row['description'])
            )
            db.session.add(complaint)


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        import_symptom_categories()
        import_symptoms()
        import_diagnoses()
        import_specializations_departments()
        db.session.commit()

        import_doctors()
        import_patients()
        db.session.commit()

        import_prescriptions()
        import_complaints()
        db.session.commit()

        print("Импорт данных завершен успешно")
        print(f"Пациентов: {db.session.query(Patient).count()}")
        print(f"Врачей: {db.session.query(Doctor).count()}")
        print(f"Назначений: {db.session.query(Prescription).count()}")
        print(f"Жалоб: {db.session.query(Complaint).count()}")


if __name__ == '__main__':
    main()