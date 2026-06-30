import os
import sys
import pytest
from sqlalchemy.orm import Session

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db, Hospital, Doctor, Booking, RedirectRule, OutbreakCase, ResourceTransfer
from agents.hospital_finder import HospitalFinderAgent
from agents.booking import BookingAgent
from agents.triage import TriageAgent
from agents.outbreak import OutbreakPredictionAgent
from agents.equipment import EquipmentAgent
from agents.orchestrator import OrchestratorAgent

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # Force use of a test DB or reset the existing DB
    init_db()
    db = SessionLocal()
    # Reset simulation states before tests
    orch = OrchestratorAgent(db)
    orch.reset_simulation()
    db.close()
    yield
    # Clean up after tests
    db = SessionLocal()
    orch = OrchestratorAgent(db)
    orch.reset_simulation()
    db.close()

def test_hospital_finder():
    db = SessionLocal()
    finder = HospitalFinderAgent(db)
    
    # Test basic specialty filter
    cardio_hospitals = finder.search_hospitals(specialty="Cardiology")
    assert len(cardio_hospitals) >= 1
    assert any(h["name"] == "Metro Cardiac Care" for h in cardio_hospitals)
    
    # Test proximity sorting
    # Lakeside is at x=40, y=55; Zone B Memorial is at 45, 50
    # Let's search from x=41, y=54
    sorted_hospitals = finder.search_hospitals(x=41, y=54)
    assert len(sorted_hospitals) > 0
    # Lakeside should be very close
    assert sorted_hospitals[0]["name"] == "Lakeside Community Clinic"
    
    db.close()

def test_booking_and_redirection():
    db = SessionLocal()
    booking_agent = BookingAgent(db)
    
    # 1. Test booking standard appointment
    # Dr. Alice Smith is at St. Jude (General Medicine)
    doc = db.query(Doctor).filter(Doctor.name == "Dr. Alice Smith").first()
    assert doc is not None
    
    res = booking_agent.create_booking(
        patient_name="John Doe",
        doctor_id=doc.id,
        time_slot="09:00"
    )
    
    assert res["success"] is True
    assert res["status"] == "Confirmed"
    assert res["hospital_name"] == "St. Jude General Hospital"
    
    # Verify slot was removed
    slots_res = booking_agent.get_doctor_slots(doc.id)
    assert "09:00" not in slots_res["slots"]
    
    # 2. Test booking with active redirect rule
    # Let's create a redirect rule: City Infectious Clinic (overloaded) -> St. Jude (spare)
    src_hosp = db.query(Hospital).filter(Hospital.name == "City Infectious Clinic").first()
    tgt_hosp = db.query(Hospital).filter(Hospital.name == "St. Jude General Hospital").first()
    
    rule = RedirectRule(source_hospital_id=src_hosp.id, target_hospital_id=tgt_hosp.id, active=True)
    db.add(rule)
    db.commit()
    
    # Try booking Dr. Frank Harris (at City Infectious Clinic)
    infect_doc = db.query(Doctor).filter(Doctor.hospital_id == src_hosp.id).first()
    
    res_redirect = booking_agent.create_booking(
        patient_name="Jane Doe",
        doctor_id=infect_doc.id,
        time_slot="09:00"
    )
    
    assert res_redirect["success"] is True
    assert res_redirect["status"] == "Redirected"
    # Booking should be made at St. Jude (target) instead
    assert res_redirect["hospital_name"] == "St. Jude General Hospital"
    assert res_redirect["original_hospital_name"] == "City Infectious Clinic"
    
    # Clean up redirect rule
    db.delete(rule)
    db.commit()
    db.close()

def test_triage_chatbot():
    triage = TriageAgent()
    
    # Verify local fallback handles chest pain (Cardiology)
    res_cardio = triage.triage_chat(history=[], user_message="I have severe chest pain and heart racing")
    assert res_cardio["triage_level"] == "Urgent"
    assert res_cardio["specialty"] == "Cardiology"
    assert "DISCLAIMER" in res_cardio["response"]
    
    # Verify local fallback handles cough (Pulmonology)
    res_pulm = triage.triage_chat(history=[], user_message="I have a chronic cough and wheezing")
    assert res_pulm["triage_level"] == "Semi-urgent"
    assert res_pulm["specialty"] == "Pulmonology"
    assert "DISCLAIMER" in res_pulm["response"]

def test_orchestrator_simulation_flow():
    db = SessionLocal()
    orchestrator = OrchestratorAgent(db)
    
    # Run the simulation flow for Zone A
    res = orchestrator.simulate_outbreak_flow("Zone A")
    
    assert res["success"] is True
    
    # Verify logs were generated
    logs = res["logs"]
    assert len(logs) > 0
    assert any(log["step"] == "OUTBREAK_ANALYSIS" for log in logs)
    assert any(log["step"] == "OVERLOAD_DETECTED" for log in logs)
    assert any(log["step"] == "RESOURCE_TRANSFER_EXECUTED" for log in logs)
    assert any(log["step"] == "BOOKING_REDIRECT_ACTIVE" for log in logs)
    
    # Verify database transfer logs
    transfers = db.query(ResourceTransfer).all()
    assert len(transfers) > 0
    
    # Verify redirect rule is active in the database
    src_hosp = db.query(Hospital).filter(Hospital.name == "City Infectious Clinic").first()
    rule = db.query(RedirectRule).filter(RedirectRule.source_hospital_id == src_hosp.id).first()
    assert rule is not None
    assert rule.active is True
    
    # Reset simulation
    reset_res = orchestrator.reset_simulation()
    assert reset_res["success"] is True
    
    # Verify redirection was deactivated
    rule_after = db.query(RedirectRule).filter(RedirectRule.source_hospital_id == src_hosp.id).first()
    assert rule_after.active is False
    
    db.close()
