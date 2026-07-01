from sqlalchemy.orm import Session
from database import Hospital, ResourceTransfer

class EquipmentAgent:
    def __init__(self, db: Session):
        self.db = db

    def get_inventory(self, hospital_id: int):
        h = self.db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not h:
            return {"error": "Hospital not found"}
            
        return {
            "hospital_id": h.id,
            "hospital_name": h.name,
            "zone": h.zone,
            "beds": {"total": h.total_beds, "available": h.available_beds},
            "icu": {"total": h.total_icu, "available": h.available_icu},
            "ventilators": {"total": h.total_ventilators, "available": h.available_ventilators}
        }

    def get_all_inventories(self):
        hospitals = self.db.query(Hospital).all()
        return [self.get_inventory(h.id) for h in hospitals]

    def find_spare_capacity(self, exclude_hospital_id: int, zone: str, equipment_type: str, min_qty: int = 5):
        """
        Finds hospitals in the same zone that have significant spare capacity of the given equipment.
        For simplicity, spare capacity means available quantity >= min_qty.
        """
        query = self.db.query(Hospital).filter(
            Hospital.id != exclude_hospital_id,
            Hospital.zone == zone
        )
        
        candidates = query.all()
        results = []
        for h in candidates:
            avail = 0
            if equipment_type == "beds":
                avail = h.available_beds
            elif equipment_type == "icu":
                avail = h.available_icu
            elif equipment_type == "ventilators":
                avail = h.available_ventilators
                
            # If they have spare (e.g. available > 30% of total) and meet minimum quantity
            if avail >= min_qty:
                results.append({
                    "hospital_id": h.id,
                    "hospital_name": h.name,
                    "available_qty": avail,
                    "x": h.x,
                    "y": h.y
                })
        return results

    def transfer_equipment(self, source_hospital_id: int, target_hospital_id: int, equipment_type: str, quantity: int):
        """
        Atomically transfers equipment from source_hospital to target_hospital.
        NOTE: In our orchestrator, when a hospital is overloaded, we transfer equipment FROM the spare capacity hospital TO the overloaded hospital!
        Let's read carefully: "generates a resource transfer request from overloaded to spare-capacity hospitals" OR "from spare-capacity to overloaded hospitals"?
        Wait! Let's read: "generates a resource transfer request from overloaded to spare-capacity hospitals" or wait, "from overloaded to spare-capacity" means we move the overloaded patients or we move equipment from spare-capacity to overloaded?
        Actually, let's look at the wording: "generates a 'resource transfer request' from overloaded to spare-capacity hospitals, and tells Booking Agent to redirect new patients to hospitals with free capacity" OR wait:
        "resource transfer request from overloaded to spare-capacity hospitals" — this might refer to transferring patients, OR it might refer to shifting equipment. Wait! Moving equipment from spare-capacity to overloaded helps the overloaded hospital cope. Moving equipment from overloaded to spare-capacity doesn't make sense (since the overloaded one is already short). But wait!
        What if the request says: "resource transfer request from overloaded to spare-capacity hospitals"? Ah! Maybe it means moving patients or moving resources?
        Let's support both directions or clarify! Let's write the `transfer_equipment` method generic enough so that we can transfer from any hospital to another, e.g. `source` to `target`.
        Let's design it:
        If `source` has enough available equipment, we decrement `source` and increment `target`.
        Let's check if the source has enough available.
        For example:
        If we transfer ventilators from Hospital B (spare) to Hospital A (overloaded):
        Hospital B available ventilators decreases, Hospital A available ventilators increases.
        If we transfer patients, it's represented by bookings redirection.
        Let's implement a clean `transfer_equipment` that adjusts the database values and logs the transaction.
        """
        source = self.db.query(Hospital).filter(Hospital.id == source_hospital_id).first()
        target = self.db.query(Hospital).filter(Hospital.id == target_hospital_id).first()
        
        if not source or not target:
            return {"error": "Source or target hospital not found", "success": False}
            
        # Check source availability
        src_avail = getattr(source, f"available_{equipment_type}")
        if src_avail < quantity:
            return {"error": f"Source hospital {source.name} only has {src_avail} available {equipment_type}, requested {quantity}", "success": False}
            
        # Perform atomic transfer
        setattr(source, f"available_{equipment_type}", src_avail - quantity)
        
        # We also need to adjust total capacity if we are moving physical units permanently or temporarily
        # For the demo, adjusting the available count is perfect and simulates the inventory change.
        tgt_avail = getattr(target, f"available_{equipment_type}")
        setattr(target, f"available_{equipment_type}", tgt_avail + quantity)
        
        # Log the transfer
        transfer = ResourceTransfer(
            source_hospital_id=source_hospital_id,
            target_hospital_id=target_hospital_id,
            equipment_type=equipment_type,
            quantity=quantity
        )
        self.db.add(transfer)
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Successfully transferred {quantity} {equipment_type} from {source.name} to {target.name}.",
            "transfer_id": transfer.id,
            "source_hospital": source.name,
            "target_hospital": target.name,
            "equipment_type": equipment_type,
            "quantity": quantity
        }
