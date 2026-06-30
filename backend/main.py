from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db, Hospital, Doctor, Booking, ResourceTransfer, RedirectRule
from agents.hospital_finder import HospitalFinderAgent
from agents.booking import BookingAgent
from agents.triage import TriageAgent
from agents.outbreak import OutbreakPredictionAgent
from agents.equipment import EquipmentAgent
from agents.orchestrator import OrchestratorAgent

app = FastAPI(title="MedTrack API", description="AI-powered health resource management platform")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for the demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Chat model
class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

# Booking model
class BookingRequest(BaseModel):
    patient_name: str
    doctor_id: int
    time_slot: str

# API Endpoints

@app.get("/api/hospitals")
def get_hospitals(
    x: Optional[float] = None, 
    y: Optional[float] = None, 
    specialty: Optional[str] = None,
    min_beds: Optional[int] = 0,
    min_icu: Optional[int] = 0,
    min_ventilators: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    finder = HospitalFinderAgent(db)
    return finder.search_hospitals(x, y, specialty, min_beds, min_icu, min_ventilators)

@app.get("/api/doctors")
def get_doctors(db: Session = Depends(get_db)):
    booking_agent = BookingAgent(db)
    return booking_agent.get_all_doctors()

@app.get("/api/doctors/{doctor_id}/slots")
def get_doctor_slots(doctor_id: int, db: Session = Depends(get_db)):
    booking_agent = BookingAgent(db)
    res = booking_agent.get_doctor_slots(doctor_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.post("/api/book")
def book_appointment(req: BookingRequest, db: Session = Depends(get_db)):
    booking_agent = BookingAgent(db)
    res = booking_agent.create_booking(req.patient_name, req.doctor_id, req.time_slot)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Booking failed"))
    return res

@app.get("/api/bookings")
def get_bookings(db: Session = Depends(get_db)):
    bookings = db.query(Booking).order_by(Booking.timestamp.desc()).all()
    results = []
    for b in bookings:
        doctor = db.query(Doctor).filter(Doctor.id == b.doctor_id).first()
        hospital = db.query(Hospital).filter(Hospital.id == b.hospital_id).first()
        results.append({
            "id": b.id,
            "patient_name": b.patient_name,
            "doctor_name": doctor.name if doctor else "Unknown",
            "hospital_name": hospital.name if hospital else "Unknown",
            "time_slot": b.time_slot,
            "status": b.status,
            "original_hospital_name": b.original_hospital_name,
            "timestamp": b.timestamp
        })
    return results

# Initialize the single instance TriageAgent (which loads Gemini environment)
triage_agent = TriageAgent()

@app.post("/api/chat")
def chat_triage(req: ChatRequest):
    history_dicts = [{"role": msg.role, "text": msg.text} for msg in req.history]
    return triage_agent.triage_chat(history_dicts, req.message)

@app.get("/api/outbreak/status")
def get_outbreak_status(db: Session = Depends(get_db)):
    agent = OutbreakPredictionAgent(db)
    return agent.get_all_zones_status()

@app.get("/api/equipment/status")
def get_equipment_status(db: Session = Depends(get_db)):
    agent = EquipmentAgent(db)
    return agent.get_all_inventories()

@app.get("/api/transfers")
def get_transfers(db: Session = Depends(get_db)):
    transfers = db.query(ResourceTransfer).order_by(ResourceTransfer.timestamp.desc()).all()
    results = []
    for t in transfers:
        src = db.query(Hospital).filter(Hospital.id == t.source_hospital_id).first()
        tgt = db.query(Hospital).filter(Hospital.id == t.target_hospital_id).first()
        results.append({
            "id": t.id,
            "source_hospital": src.name if src else "Unknown",
            "target_hospital": tgt.name if tgt else "Unknown",
            "equipment_type": t.equipment_type,
            "quantity": t.quantity,
            "timestamp": t.timestamp
        })
    return results

@app.get("/api/redirects")
def get_redirects(db: Session = Depends(get_db)):
    rules = db.query(RedirectRule).filter(RedirectRule.active == True).all()
    results = []
    for r in rules:
        src = db.query(Hospital).filter(Hospital.id == r.source_hospital_id).first()
        tgt = db.query(Hospital).filter(Hospital.id == r.target_hospital_id).first()
        results.append({
            "id": r.id,
            "source_hospital": src.name if src else "Unknown",
            "target_hospital": tgt.name if tgt else "Unknown"
        })
    return results

@app.post("/api/simulation/run")
def run_simulation(db: Session = Depends(get_db)):
    orchestrator = OrchestratorAgent(db)
    return orchestrator.simulate_outbreak_flow("Zone A")

@app.post("/api/simulation/reset")
def reset_simulation(db: Session = Depends(get_db)):
    orchestrator = OrchestratorAgent(db)
    return orchestrator.reset_simulation()
