from sqlalchemy.orm import Session
from datetime import datetime
from database import Hospital, RedirectRule, OutbreakCase, ResourceTransfer
from agents.outbreak import OutbreakPredictionAgent
from agents.equipment import EquipmentAgent

class OrchestratorAgent:
    def __init__(self, db: Session):
        self.db = db
        self.outbreak_agent = OutbreakPredictionAgent(db)
        self.equipment_agent = EquipmentAgent(db)

    def simulate_outbreak_flow(self, zone: str = "Zone A"):
        logs = []
        logs.append({
            "step": "SIMULATION_START",
            "message": f"Simulating outbreak outbreak in {zone}...",
            "timestamp": datetime.now().isoformat()
        })

        # 1. Inject outbreak case count spike for today
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Check if today's case record already exists, or create/update it
        today_case = self.db.query(OutbreakCase).filter(
            OutbreakCase.zone == zone,
            OutbreakCase.date == today_str
        ).first()
        
        spike_count = 85
        if today_case:
            today_case.case_count = spike_count
        else:
            today_case = OutbreakCase(zone=zone, date=today_str, case_count=spike_count)
            self.db.add(today_case)
            
        self.db.commit()
        logs.append({
            "step": "SPIKE_INJECTED",
            "message": f"Injected spike of {spike_count} cases in {zone} for date {today_str}.",
            "timestamp": datetime.now().isoformat()
        })

        # 2. Run Outbreak Agent analysis
        outbreak_report = self.outbreak_agent.check_zone_outbreak(zone)
        logs.append({
            "step": "OUTBREAK_ANALYSIS",
            "message": outbreak_report["message"],
            "data": outbreak_report,
            "timestamp": datetime.now().isoformat()
        })

        if not outbreak_report["is_at_risk"]:
            logs.append({
                "step": "SIMULATION_ABORTED",
                "message": f"Zone {zone} growth rate did not cross threshold. No action taken.",
                "timestamp": datetime.now().isoformat()
            })
            return {"success": False, "logs": logs}

        # 3. Locate Overloaded Hospitals in this zone
        # Define overloaded: available ventilators <= 1 or available beds <= 10
        overloaded_hospitals = self.db.query(Hospital).filter(
            Hospital.zone == zone,
            (Hospital.available_ventilators <= 1) | (Hospital.available_beds <= 10)
        ).all()

        if not overloaded_hospitals:
            logs.append({
                "step": "NO_OVERLOADED_HOSPITALS",
                "message": f"Outbreak flagged in {zone}, but all hospitals have stable capacity.",
                "timestamp": datetime.now().isoformat()
            })
            return {"success": True, "logs": logs}

        # We'll process the most overloaded hospital (least available beds)
        overloaded_hospitals.sort(key=lambda h: h.available_beds)
        overloaded = overloaded_hospitals[0]
        
        logs.append({
            "step": "OVERLOAD_DETECTED",
            "message": f"Overload detected at '{overloaded.name}'! Available beds: {overloaded.available_beds}/{overloaded.total_beds}, ICU: {overloaded.available_icu}/{overloaded.total_icu}, Ventilators: {overloaded.available_ventilators}/{overloaded.total_ventilators}.",
            "hospital_id": overloaded.id,
            "timestamp": datetime.now().isoformat()
        })

        # 4. Search for Nearby Spare Capacity Hospitals in same zone
        # We need a hospital with available ventilators > 2 and available beds > 20
        spare_candidates = self.db.query(Hospital).filter(
            Hospital.id != overloaded.id,
            Hospital.zone == zone,
            Hospital.available_beds > 20,
            Hospital.available_ventilators > 2
        ).all()

        if not spare_candidates:
            logs.append({
                "step": "NO_SPARE_CAPACITY",
                "message": f"CRITICAL: No nearby hospitals in {zone} have spare capacity to help '{overloaded.name}'!",
                "timestamp": datetime.now().isoformat()
            })
            return {"success": False, "logs": logs}

        # Select target hospital (highest available beds)
        spare_candidates.sort(key=lambda h: h.available_beds, reverse=True)
        spare = spare_candidates[0]

        logs.append({
            "step": "SPARE_CAPACITY_FOUND",
            "message": f"Found spare capacity at '{spare.name}'. Available beds: {spare.available_beds}/{spare.total_beds}, ICU: {spare.available_icu}/{spare.total_icu}, Ventilators: {spare.available_ventilators}/{spare.total_ventilators}.",
            "hospital_id": spare.id,
            "timestamp": datetime.now().isoformat()
        })

        # 5. Generate Resource Transfer (Beds & Ventilators)
        # Move 10 beds and 3 ventilators from spare to overloaded to balance inventory
        beds_to_transfer = 10
        vent_to_transfer = 3

        transfer_results = []
        
        # Transfer Beds
        bed_trans = self.equipment_agent.transfer_equipment(spare.id, overloaded.id, "beds", beds_to_transfer)
        if "error" not in bed_trans:
            transfer_results.append(bed_trans)
            logs.append({
                "step": "RESOURCE_TRANSFER_EXECUTED",
                "message": f"Transferred {beds_to_transfer} beds from '{spare.name}' to '{overloaded.name}' successfully.",
                "data": bed_trans,
                "timestamp": datetime.now().isoformat()
            })
        else:
            logs.append({
                "step": "RESOURCE_TRANSFER_FAILED",
                "message": f"Failed to transfer beds: {bed_trans['error']}",
                "timestamp": datetime.now().isoformat()
            })

        # Transfer Ventilators
        vent_trans = self.equipment_agent.transfer_equipment(spare.id, overloaded.id, "ventilators", vent_to_transfer)
        if "error" not in vent_trans:
            transfer_results.append(vent_trans)
            logs.append({
                "step": "RESOURCE_TRANSFER_EXECUTED",
                "message": f"Transferred {vent_to_transfer} ventilators from '{spare.name}' to '{overloaded.name}' successfully.",
                "data": vent_trans,
                "timestamp": datetime.now().isoformat()
            })
        else:
            logs.append({
                "step": "RESOURCE_TRANSFER_FAILED",
                "message": f"Failed to transfer ventilators: {vent_trans['error']}",
                "timestamp": datetime.now().isoformat()
            })

        # 6. Configure Booking Redirection Rule
        # Redirect all new patients for overloaded hospital to spare hospital
        redirect_rule = self.db.query(RedirectRule).filter(
            RedirectRule.source_hospital_id == overloaded.id
        ).first()

        if redirect_rule:
            redirect_rule.target_hospital_id = spare.id
            redirect_rule.active = True
        else:
            redirect_rule = RedirectRule(
                source_hospital_id=overloaded.id,
                target_hospital_id=spare.id,
                active=True
            )
            self.db.add(redirect_rule)
            
        self.db.commit()

        logs.append({
            "step": "BOOKING_REDIRECT_ACTIVE",
            "message": f"Activated booking redirection rule: New patients for '{overloaded.name}' are now auto-routed to '{spare.name}'.",
            "source_id": overloaded.id,
            "target_id": spare.id,
            "timestamp": datetime.now().isoformat()
        })

        logs.append({
            "step": "SIMULATION_COMPLETE",
            "message": "Orchestration successfully completed. Outbreak mitigated.",
            "timestamp": datetime.now().isoformat()
        })

        return {
            "success": True,
            "logs": logs,
            "transfers": transfer_results,
            "redirect": {
                "source": overloaded.name,
                "target": spare.name
            }
        }

    def reset_simulation(self):
        # Disable all redirection rules
        self.db.query(RedirectRule).update({RedirectRule.active: False})
        
        # Reset the outbreak counts to historical averages (clean up spikes)
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.db.query(OutbreakCase).filter(OutbreakCase.date == today_str).delete()
        
        # Reset hospital resource levels back to seed levels
        hospitals_seeds = {
            "St. Jude General Hospital": {"beds": 60, "icu": 12, "vent": 8},
            "Metro Cardiac Care": {"beds": 30, "icu": 5, "vent": 3},
            "City Infectious Clinic": {"beds": 8, "icu": 1, "vent": 0},
            "Zone B Memorial Hospital": {"beds": 95, "icu": 20, "vent": 14},
            "Pulmonary Health Institute": {"beds": 50, "icu": 10, "vent": 9},
            "Lakeside Community Clinic": {"beds": 25, "icu": 4, "vent": 3},
            "Hope Medical Center": {"beds": 130, "icu": 28, "vent": 18},
            "Zone C Specialty Clinic": {"beds": 40, "icu": 9, "vent": 8},
            "Northside Care Center": {"beds": 65, "icu": 12, "vent": 10}
        }
        
        for name, resources in hospitals_seeds.items():
            h = self.db.query(Hospital).filter(Hospital.name == name).first()
            if h:
                h.available_beds = resources["beds"]
                h.available_icu = resources["icu"]
                h.available_ventilators = resources["vent"]
                
        # Delete resource transfer logs
        self.db.query(ResourceTransfer).delete()
        
        self.db.commit()
        return {"success": True, "message": "Simulation states and database inventories reset to seed values."}
