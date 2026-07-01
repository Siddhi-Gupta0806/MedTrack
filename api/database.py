import os
import json
import shutil
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Determine database path
if os.environ.get("VERCEL"):
    db_dir = "/tmp"
    db_path = os.path.join(db_dir, "medtrack.db")
    # If the database does not exist in /tmp, copy the template from our package path
    if not os.path.exists(db_path):
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medtrack.db")
        if os.path.exists(template_path):
            shutil.copy2(template_path, db_path)
else:
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, "medtrack.db")

DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    zone = Column(String, index=True)  # Zone A, Zone B, Zone C
    x = Column(Integer)  # Grid coordinates
    y = Column(Integer)
    specialty = Column(String)  # Primary specialty
    total_beds = Column(Integer)
    available_beds = Column(Integer)
    total_icu = Column(Integer)
    available_icu = Column(Integer)
    total_ventilators = Column(Integer)
    available_ventilators = Column(Integer)
    
    doctors = relationship("Doctor", back_populates="hospital")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    name = Column(String)
    specialty = Column(String)
    slots = Column(Text)  # JSON-serialized list of slots e.g., ["09:00", "10:00"]
    
    hospital = relationship("Hospital", back_populates="doctors")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    patient_name = Column(String)
    time_slot = Column(String)
    status = Column(String)  # Confirmed, Redirected
    original_hospital_name = Column(String, nullable=True)
    timestamp = Column(String, default=lambda: datetime.now().isoformat())

class OutbreakCase(Base):
    __tablename__ = "outbreak_cases"
    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String, index=True)
    date = Column(String, index=True)  # YYYY-MM-DD
    case_count = Column(Integer)

class ResourceTransfer(Base):
    __tablename__ = "resource_transfers"
    id = Column(Integer, primary_key=True, index=True)
    source_hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    target_hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    equipment_type = Column(String)  # beds, icu, ventilators
    quantity = Column(Integer)
    timestamp = Column(String, default=lambda: datetime.now().isoformat())

class RedirectRule(Base):
    __tablename__ = "redirect_rules"
    id = Column(Integer, primary_key=True, index=True)
    source_hospital_id = Column(Integer, ForeignKey("hospitals.id"), unique=True)
    target_hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    active = Column(Boolean, default=True)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if we already have data
    if db.query(Hospital).count() > 0:
        db.close()
        return

    # Seed 9 hospitals
    hospitals = [
        # Zone A
        Hospital(name="St. Jude General Hospital", zone="Zone A", x=15, y=20, specialty="General Medicine",
                 total_beds=120, available_beds=60, total_icu=25, available_icu=12, total_ventilators=15, available_ventilators=8),
        Hospital(name="Metro Cardiac Care", zone="Zone A", x=12, y=25, specialty="Cardiology",
                 total_beds=60, available_beds=30, total_icu=15, available_icu=5, total_ventilators=8, available_ventilators=3),
        Hospital(name="City Infectious Clinic", zone="Zone A", x=18, y=15, specialty="Infectious Diseases",
                 total_beds=40, available_beds=8, total_icu=10, available_icu=1, total_ventilators=6, available_ventilators=0),
        
        # Zone B
        Hospital(name="Zone B Memorial Hospital", zone="Zone B", x=45, y=50, specialty="General Medicine",
                 total_beds=150, available_beds=95, total_icu=30, available_icu=20, total_ventilators=20, available_ventilators=14),
        Hospital(name="Pulmonary Health Institute", zone="Zone B", x=48, y=45, specialty="Pulmonology",
                 total_beds=70, available_beds=50, total_icu=15, available_icu=10, total_ventilators=12, available_ventilators=9),
        Hospital(name="Lakeside Community Clinic", zone="Zone B", x=40, y=55, specialty="General Medicine",
                 total_beds=35, available_beds=25, total_icu=5, available_icu=4, total_ventilators=4, available_ventilators=3),
                 
        # Zone C
        Hospital(name="Hope Medical Center", zone="Zone C", x=80, y=85, specialty="General Medicine",
                 total_beds=200, available_beds=130, total_icu=40, available_icu=28, total_ventilators=25, available_ventilators=18),
        Hospital(name="Zone C Specialty Clinic", zone="Zone C", x=85, y=80, specialty="Infectious Diseases",
                 total_beds=50, available_beds=40, total_icu=12, available_icu=9, total_ventilators=10, available_ventilators=8),
        Hospital(name="Northside Care Center", zone="Zone C", x=75, y=90, specialty="General Medicine",
                 total_beds=80, available_beds=65, total_icu=15, available_icu=12, total_ventilators=12, available_ventilators=10)
    ]
    db.add_all(hospitals)
    db.commit()

    # Re-fetch hospitals to map IDs for doctor seeding
    hosp_objs = db.query(Hospital).all()
    hosp_map = {h.name: h.id for h in hosp_objs}

    # Seed 22 Doctors
    doctors = [
        # St. Jude General Hospital
        Doctor(hospital_id=hosp_map["St. Jude General Hospital"], name="Dr. Alice Smith", specialty="General Medicine", slots=json.dumps(["09:00", "10:00", "11:00", "14:00", "15:00"])),
        Doctor(hospital_id=hosp_map["St. Jude General Hospital"], name="Dr. Bob Johnson", specialty="General Medicine", slots=json.dumps(["09:30", "10:30", "13:30", "16:00"])),
        Doctor(hospital_id=hosp_map["St. Jude General Hospital"], name="Dr. Clara Davis", specialty="Pediatrics", slots=json.dumps(["10:00", "11:00", "12:00", "14:00"])),

        # Metro Cardiac Care
        Doctor(hospital_id=hosp_map["Metro Cardiac Care"], name="Dr. David Miller", specialty="Cardiology", slots=json.dumps(["09:00", "10:00", "11:00", "13:00", "15:00"])),
        Doctor(hospital_id=hosp_map["Metro Cardiac Care"], name="Dr. Emily Wilson", specialty="Cardiology", slots=json.dumps(["11:00", "14:00", "15:00", "16:00"])),

        # City Infectious Clinic
        Doctor(hospital_id=hosp_map["City Infectious Clinic"], name="Dr. Frank Harris", specialty="Infectious Diseases", slots=json.dumps(["09:00", "10:00", "11:00", "14:00"])),
        Doctor(hospital_id=hosp_map["City Infectious Clinic"], name="Dr. Grace Lee", specialty="Infectious Diseases", slots=json.dumps(["09:30", "13:00", "14:30", "15:30"])),

        # Zone B Memorial Hospital
        Doctor(hospital_id=hosp_map["Zone B Memorial Hospital"], name="Dr. Henry Clark", specialty="General Medicine", slots=json.dumps(["09:00", "10:00", "11:00", "13:00", "15:00"])),
        Doctor(hospital_id=hosp_map["Zone B Memorial Hospital"], name="Dr. Irene Lewis", specialty="General Medicine", slots=json.dumps(["10:00", "12:00", "14:00", "16:00"])),
        Doctor(hospital_id=hosp_map["Zone B Memorial Hospital"], name="Dr. Jack Walker", specialty="Pediatrics", slots=json.dumps(["09:00", "11:00", "14:00", "15:00"])),

        # Pulmonary Health Institute
        Doctor(hospital_id=hosp_map["Pulmonary Health Institute"], name="Dr. Karen Hall", specialty="Pulmonology", slots=json.dumps(["09:00", "10:00", "11:00", "14:00", "15:00"])),
        Doctor(hospital_id=hosp_map["Pulmonary Health Institute"], name="Dr. Leo Allen", specialty="Pulmonology", slots=json.dumps(["10:30", "13:30", "15:00", "16:00"])),

        # Lakeside Community Clinic
        Doctor(hospital_id=hosp_map["Lakeside Community Clinic"], name="Dr. Mona Young", specialty="General Medicine", slots=json.dumps(["09:00", "10:00", "11:00", "14:00"])),

        # Hope Medical Center
        Doctor(hospital_id=hosp_map["Hope Medical Center"], name="Dr. Nathan King", specialty="General Medicine", slots=json.dumps(["09:00", "10:00", "11:00", "13:00", "14:00", "15:00"])),
        Doctor(hospital_id=hosp_map["Hope Medical Center"], name="Dr. Olivia Wright", specialty="General Medicine", slots=json.dumps(["09:30", "10:30", "13:30", "14:30", "15:30"])),
        Doctor(hospital_id=hosp_map["Hope Medical Center"], name="Dr. Paul Lopez", specialty="Cardiology", slots=json.dumps(["10:00", "11:00", "14:00", "15:00"])),

        # Zone C Specialty Clinic
        Doctor(hospital_id=hosp_map["Zone C Specialty Clinic"], name="Dr. Rachel Green", specialty="Infectious Diseases", slots=json.dumps(["09:00", "10:00", "11:00", "13:00", "14:00"])),
        Doctor(hospital_id=hosp_map["Zone C Specialty Clinic"], name="Dr. Samuel Adams", specialty="Infectious Diseases", slots=json.dumps(["09:30", "10:30", "13:30", "15:30"])),

        # Northside Care Center
        Doctor(hospital_id=hosp_map["Northside Care Center"], name="Dr. Tina Baker", specialty="General Medicine", slots=json.dumps(["09:00", "10:00", "11:00", "14:00", "15:00"])),
        Doctor(hospital_id=hosp_map["Northside Care Center"], name="Dr. Victor Carter", specialty="Pediatrics", slots=json.dumps(["10:00", "11:30", "13:30", "15:00"]))
    ]
    db.add_all(doctors)
    db.commit()

    # Seed 14 days of historical daily case counts for Zone A, Zone B, Zone C
    # Zone A: low, stable cases
    # Zone B: moderate, stable cases
    # Zone C: low, stable cases
    base_date = datetime.now() - timedelta(days=14)
    daily_cases = []
    
    # Static counts that are stable
    zone_a_counts = [5, 6, 5, 7, 6, 8, 7, 8, 9, 8, 9, 8, 9, 10]
    zone_b_counts = [15, 16, 15, 17, 18, 16, 17, 18, 19, 20, 18, 19, 21, 22]
    zone_c_counts = [3, 4, 3, 5, 4, 5, 4, 6, 5, 6, 5, 6, 7, 7]
    
    for i in range(14):
        date_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_cases.append(OutbreakCase(zone="Zone A", date=date_str, case_count=zone_a_counts[i]))
        daily_cases.append(OutbreakCase(zone="Zone B", date=date_str, case_count=zone_b_counts[i]))
        daily_cases.append(OutbreakCase(zone="Zone C", date=date_str, case_count=zone_c_counts[i]))

    db.add_all(daily_cases)
    db.commit()
    db.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded.")
