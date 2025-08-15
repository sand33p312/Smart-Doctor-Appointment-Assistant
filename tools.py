import os
from sqlalchemy.orm import Session
from models import Doctor, Patient, Appointment
from datetime import datetime, timedelta, date
import dateparser

# --- MOCK API FUNCTIONS ---
def schedule_with_google_calendar(doctor_name: str, patient_email: str, start_time: datetime):
    """Simulates booking an event on Google Calendar."""
    print(f"--- MOCK GOOGLE CALENDAR API ---")
    print(f"Booking event for {patient_email} with {doctor_name} at {start_time.isoformat()}")
    print(f"--- MOCK SUCCESS ---")
    return True, f"event-id-{datetime.now().timestamp()}"

def send_confirmation_email(patient_email: str, subject: str, body: str):
    """Simulates sending a confirmation email."""
    print(f"--- MOCK EMAIL API ---")
    print(f"Sending email to: {patient_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"--- MOCK SUCCESS ---")
    return True

def send_slack_notification(doctor_name: str, report: str):
    """Simulates sending a Slack notification to a doctor."""
    print(f"--- MOCK SLACK API ---")
    print(f"Sending report to Dr. {doctor_name}'s Slack channel:")
    print(report)
    print(f"--- MOCK SUCCESS ---")
    return True

def _parse_date_string(date_str: str) -> str:
    """Uses dateparser to reliably convert natural language dates into YYYY-MM-DD format."""
    # The 'future' setting helps interpret "Friday" as this coming Friday, not a past one.
    parsed_date = dateparser.parse(date_str, settings={'PREFER_DATES_FROM': 'future'})
    if parsed_date:
        return parsed_date.strftime('%Y-%m-%d')
    raise ValueError(f"Date format not recognized: {date_str}")

def _parse_time_string(time_str: str) -> str:
    """Normalizes a time string (e.g., '5 PM', '17:00', '5pm') into HH:MM format."""
    time_str = time_str.replace('pm', ' pm').replace('am', ' am').strip()
    formats_to_try = ['%I:%M %p', '%I %p', '%H:%M']
    for fmt in formats_to_try:
        try:
            return datetime.strptime(time_str, fmt).strftime('%H:%M')
        except ValueError:
            continue
    raise ValueError(f"Time format not recognized: {time_str}")


# --- DATABASE TOOLS FOR THE AI AGENT ---

def get_doctor_schedule(db: Session, doctor_name: str, date: str):
    """Fetches the raw, unfiltered list of available appointment slots for a doctor on a given day."""
    try:
        target_date_str = _parse_date_string(date)
        target_date_obj = datetime.fromisoformat(target_date_str).date()
        
        search_name = doctor_name.replace("Dr.", "").strip()
        doctor = db.query(Doctor).filter(Doctor.name.ilike(f"%{search_name}%")).first()

        if not doctor: return f"Doctor '{doctor_name}' not found."
        all_slots = doctor.availability.get(target_date_str, [])
        if not all_slots: return f"Dr. {doctor.name} has no availability on {target_date_str}."

        booked_times = [a.datetime.strftime("%H:%M") for a in db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.datetime.between(
                datetime.combine(target_date_obj, datetime.min.time()),
                datetime.combine(target_date_obj, datetime.max.time())
            ),
            Appointment.status == "booked"
        ).all()]
        
        free_slots = [s for s in all_slots if s not in booked_times]
        return free_slots
    except Exception as e:
        return f"Error fetching schedule: {e}"

def book_appointment(db: Session, doctor_name: str, patient_email: str, date: str, time: str, symptoms: str | None = None):
    """Schedules a new appointment, preventing double-bookings and saving symptoms for new patients."""
    try:
        normalized_time = _parse_time_string(time)
        target_date_str = _parse_date_string(date)
        target_dt = datetime.fromisoformat(f"{target_date_str}T{normalized_time}")
        doctor_to_book = None

        if "any" in doctor_name.lower():
            all_doctors = db.query(Doctor).all()
            for doc in all_doctors:
                if normalized_time not in doc.availability.get(target_date_str, []): continue
                if not db.query(Appointment).filter_by(doctor_id=doc.id, datetime=target_dt, status="booked").first():
                    doctor_to_book = doc
                    break
            if not doctor_to_book: return f"I'm sorry, but no doctors are available on {target_date_str} at {normalized_time}."
        else:
            doctor_to_book = db.query(Doctor).filter(Doctor.name.ilike(f"%{doctor_name}%")).first()
            if not doctor_to_book: return f"Doctor '{doctor_name}' not found."
            if db.query(Appointment).filter_by(doctor_id=doctor_to_book.id, datetime=target_dt, status="booked").first():
                return f"I'm sorry, but Dr. {doctor_to_book.name} is already booked at {normalized_time} on {target_date_str}."

        patient = db.query(Patient).filter_by(email=patient_email).first()
        if not patient:
            patient = Patient(name=patient_email.split('@')[0], email=patient_email, symptoms=symptoms or "Not provided")
            db.add(patient)
            db.commit(); db.refresh(patient)

        gcal_success, _ = schedule_with_google_calendar(doctor_to_book.name, patient.email, target_dt)
        if not gcal_success: return "Failed to book on Google Calendar."

        new_appointment = Appointment(doctor_id=doctor_to_book.id, patient_id=patient.id, datetime=target_dt, status="booked")
        db.add(new_appointment)
        db.commit()

        email_body = f"Your appointment with {doctor_to_book.name} is confirmed for {target_date_str} at {normalized_time}."
        send_confirmation_email(patient.email, "Appointment Confirmed", email_body)

        return f"Success! Your appointment is booked with {doctor_to_book.name} on {target_date_str} at {normalized_time}."
    except ValueError as ve:
        return f"I'm sorry, I couldn't understand the date or time you provided: {ve}"
    except Exception as e:
        return f"Error booking appointment: {e}"

def get_appointment_summary(db: Session, query: str, doctor_name: str | None = None):
    """Generates a detailed summary report for a doctor."""
    try:
        today = date.today()
        query_lower = query.lower()
        
        # --- NEW: Clean the query string if a doctor's name is present ---
        # This ensures that we isolate the actual query (e.g., "how many patients with fever")
        # from the context provided by the dashboard (e.g., "for Dr. Ravi Ahuja")
        if doctor_name:
            clean_doc_name_for_search = doctor_name.replace("Dr.", "").strip().lower()
            query_lower = query_lower.replace(f"for {clean_doc_name_for_search}", "").strip()
        # --- END OF NEW LOGIC ---

        base_query = db.query(Appointment)

        if doctor_name:
            doctor = db.query(Doctor).filter(Doctor.name.ilike(f"%{doctor_name.replace('Dr.', '').strip()}%")).first()
            if doctor: base_query = base_query.filter_by(doctor_id=doctor.id)
            else: return f"Could not find doctor: {doctor_name}"

        if 'yesterday' in query_lower or 'today' in query_lower:
            target_date = today - timedelta(days=1) if 'yesterday' in query_lower else today
            appointments = base_query.filter(Appointment.datetime.between(datetime.combine(target_date, datetime.min.time()), datetime.combine(target_date, datetime.max.time()))).order_by(Appointment.datetime).all()
            period = "yesterday" if 'yesterday' in query_lower else "today"
            if not appointments: return f"You had no appointments {period}."
            report_lines = [f"You have {len(appointments)} appointment(s) {period}:"]
            for appt in appointments:
                patient = db.query(Patient).filter_by(id=appt.patient_id).first()
                report_lines.append(f"- At {appt.datetime.strftime('%I:%M %p')} with patient: {patient.email if patient else 'Unknown'}")
            return "\n".join(report_lines)
        else:
            # Now, the query_lower is clean and ready for symptom searching
            symptom = query_lower.replace("how many patients with", "").strip()
            count = base_query.join(Patient).filter(Patient.symptoms.ilike(f'%{symptom}%')).count()
            return f"Found {count} patient(s) with symptoms related to '{symptom}'."
    except Exception as e:
        return f"Error generating summary: {e}"

def list_all_doctors(db: Session):
    """Returns a list of all available doctors."""
    try:
        doctors = db.query(Doctor).all()
        if not doctors: return "There are no doctors available."
        doctor_list = [f"- {d.name} ({d.specialization})" for d in doctors]
        return "Here are the available doctors:\n" + "\n".join(doctor_list)
    except Exception as e:
        return f"Error listing doctors: {e}"

def find_doctor_by_symptom(db: Session, symptom: str):
    """Finds a suitable doctor specialization based on a symptom."""
    symptom_map = {"fever": "General Physician", "cough": "General Physician", "headache": "General Physician", "skin": "Dermatologist", "rash": "Dermatologist", "heart": "Cardiologist", "chest pain": "Cardiologist", "child": "Pediatrician", "kid": "Pediatrician"}
    for key, specialization in symptom_map.items():
        if key in symptom.lower():
            if db.query(Doctor).filter_by(specialization=specialization).first():
                return f"For that symptom, I recommend a {specialization}."
            else:
                return f"I would normally recommend a {specialization}, but none are available. I can look for a General Physician."
    return "I can look for a General Physician for you for that symptom."
