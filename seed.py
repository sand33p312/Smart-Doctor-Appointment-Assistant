from datetime import date, timedelta
from main import SessionLocal
from models import Doctor, Patient

def seed_database():
    db = SessionLocal()
    print("Seeding database with expanded data set...")

    try:
        # Clear existing data to prevent duplicates
        db.query(Patient).delete()
        db.query(Doctor).delete()
        print("Cleared existing doctors and patients.")

        # Create availability for the next 14 days
        availability_data = {}
        today = date.today()
        for i in range(14):
            current_date = today + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            availability_data[date_str] = [
                "09:00", "10:00", "11:00", "12:00", 
                "14:00", "15:00", "16:00", "17:00", "18:00"
            ]

        # Add more Doctors
        doctors = [
            Doctor(
                name="Dr. Ravi Ahuja", 
                specialization="Cardiologist", 
                availability=availability_data
            ),
            Doctor(
                name="Dr. Priya Sharma", 
                specialization="Dermatologist", 
                availability=availability_data
            ),
            Doctor(
                name="Dr. Anil Kumar", 
                specialization="Pediatrician", 
                availability=availability_data
            ),
            Doctor(
                name="Dr. Sunita Desai", 
                specialization="General Physician", 
                availability=availability_data
            ),
        ]
        db.add_all(doctors)
        print(f"Added {len(doctors)} doctors.")

        # Add more Patients
        patients = [
            Patient(name="Sandeep Madwal", email="sandeep.madwal2007@gmail.com", symptoms="Fever and cough"),
            Patient(name="Jane Smith", email="jane.smith@example.com", symptoms="Annual checkup"),
            Patient(name="Amit Singh", email="amit.singh@example.com", symptoms="Headache"),
        ]
        db.add_all(patients)
        print(f"Added {len(patients)} patients.")

        db.commit()
        print("✅ Expanded seeding complete!")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()