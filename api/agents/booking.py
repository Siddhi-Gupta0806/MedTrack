import json
from sqlalchemy.orm import Session
from database import Doctor, Booking, Hospital, RedirectRule

class BookingAgent:
    def __init__(self, db: Session):
        self.db = db

    def get_doctor_slots(self, doctor_id: int):
        doctor = self.db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            return {"error": "Doctor not found"}
        
        try:
            slots = json.loads(doctor.slots)
        except Exception:
            slots = []
            
        hospital = self.db.query(Hospital).filter(Hospital.id == doctor.hospital_id).first()
        
        return {
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "specialty": doctor.specialty,
            "hospital_id": doctor.hospital_id,
            "hospital_name": hospital.name if hospital else "Unknown",
            "slots": slots
        }

    def get_all_doctors(self):
        doctors = self.db.query(Doctor).all()
        results = []
        for d in doctors:
            hospital = self.db.query(Hospital).filter(Hospital.id == d.hospital_id).first()
            try:
                slots = json.loads(d.slots)
            except:
                slots = []
            results.append({
                "id": d.id,
                "name": d.name,
                "specialty": d.specialty,
                "hospital_id": d.hospital_id,
                "hospital_name": hospital.name if hospital else "Unknown",
                "slots": slots
            })
        return results

    def create_booking(self, patient_name: str, doctor_id: int, time_slot: str):
        # 1. Find doctor and check existence
        doctor = self.db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            return {"error": f"Doctor with ID {doctor_id} not found", "success": False}

        orig_hospital = self.db.query(Hospital).filter(Hospital.id == doctor.hospital_id).first()
        orig_hospital_name = orig_hospital.name if orig_hospital else "Unknown"

        # 2. Check for active redirection rule for this hospital
        redirect_rule = self.db.query(RedirectRule).filter(
            RedirectRule.source_hospital_id == doctor.hospital_id,
            RedirectRule.active == True
        ).first()

        is_redirected = False
        target_doctor = doctor
        target_hospital_name = orig_hospital_name

        if redirect_rule:
            is_redirected = True
            # Find target hospital
            target_hospital = self.db.query(Hospital).filter(Hospital.id == redirect_rule.target_hospital_id).first()
            if target_hospital:
                target_hospital_name = target_hospital.name
                # Find a doctor at target hospital with matching specialty, or fallback to any doctor at target
                new_doc = self.db.query(Doctor).filter(
                    Doctor.hospital_id == target_hospital.id,
                    Doctor.specialty == doctor.specialty
                ).first()
                
                if not new_doc:
                    new_doc = self.db.query(Doctor).filter(
                        Doctor.hospital_id == target_hospital.id
                    ).first()

                if new_doc:
                    target_doctor = new_doc
                else:
                    return {"error": f"Redirection active, but no doctors available at target hospital {target_hospital.name}", "success": False}
            else:
                return {"error": "Redirection target hospital not found", "success": False}

        # 3. Process slot booking on target doctor
        try:
            slots = json.loads(target_doctor.slots)
        except Exception:
            slots = []

        if time_slot not in slots:
            # If redirected, we might need to select an available slot at target doctor
            if is_redirected and slots:
                time_slot = slots[0]  # Take the first available slot at the target
            else:
                return {"error": f"Time slot {time_slot} not available for doctor {target_doctor.name}", "success": False}

        # 4. Remove slot from doctor's list and update
        slots.remove(time_slot)
        target_doctor.slots = json.dumps(slots)

        # 5. Create booking entry
        booking = Booking(
            doctor_id=target_doctor.id,
            hospital_id=target_doctor.hospital_id,
            patient_name=patient_name,
            time_slot=time_slot,
            status="Redirected" if is_redirected else "Confirmed",
            original_hospital_name=orig_hospital_name if is_redirected else None
        )
        
        self.db.add(booking)
        
        # 6. Adjust beds in target/source hospital if booking acts as admission
        # Let's say every general medicine/infectious booking decrements available beds by 1 (just to simulate real-time load)
        hosp = self.db.query(Hospital).filter(Hospital.id == target_doctor.hospital_id).first()
        if hosp and hosp.available_beds > 0:
            hosp.available_beds -= 1

        self.db.commit()

        return {
            "success": True,
            "booking_id": booking.id,
            "patient_name": patient_name,
            "doctor_name": target_doctor.name,
            "specialty": target_doctor.specialty,
            "hospital_name": target_hospital_name,
            "time_slot": time_slot,
            "status": booking.status,
            "original_hospital_name": booking.original_hospital_name,
            "message": f"Successfully booked appointment at {target_hospital_name}!" if not is_redirected else 
                       f"Booking auto-redirected from {orig_hospital_name} to {target_hospital_name} due to active outbreak capacity reallocation!"
        }
