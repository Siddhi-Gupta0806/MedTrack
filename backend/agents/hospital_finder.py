import math
from sqlalchemy.orm import Session
from database import Hospital

class HospitalFinderAgent:
    def __init__(self, db: Session):
        self.db = db

    def search_hospitals(self, x: float = None, y: float = None, specialty: str = None, 
                         min_beds: int = 0, min_icu: int = 0, min_ventilators: int = 0):
        query = self.db.query(Hospital)
        
        # Apply filters
        if specialty:
            query = query.filter(Hospital.specialty.like(f"%{specialty}%"))
        if min_beds > 0:
            query = query.filter(Hospital.available_beds >= min_beds)
        if min_icu > 0:
            query = query.filter(Hospital.available_icu >= min_icu)
        if min_ventilators > 0:
            query = query.filter(Hospital.available_ventilators >= min_ventilators)
            
        hospitals = query.all()
        results = []
        
        for h in hospitals:
            h_data = {
                "id": h.id,
                "name": h.name,
                "zone": h.zone,
                "x": h.x,
                "y": h.y,
                "specialty": h.specialty,
                "total_beds": h.total_beds,
                "available_beds": h.available_beds,
                "total_icu": h.total_icu,
                "available_icu": h.available_icu,
                "total_ventilators": h.total_ventilators,
                "available_ventilators": h.available_ventilators,
            }
            
            # Calculate distance if user location provided
            if x is not None and y is not None:
                dist = math.sqrt((h.x - x)**2 + (h.y - y)**2)
                h_data["distance"] = round(dist, 2)
            else:
                h_data["distance"] = 0.0
                
            results.append(h_data)
            
        # Sort by distance if location provided
        if x is not None and y is not None:
            results.sort(key=lambda item: item["distance"])
            
        return results
