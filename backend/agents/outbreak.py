from sqlalchemy.orm import Session
from database import OutbreakCase

class OutbreakPredictionAgent:
    def __init__(self, db: Session):
        self.db = db

    def check_zone_outbreak(self, zone: str, threshold_rate: float = 0.20, min_cases: int = 12):
        # Query the latest cases for the zone, ordered by date descending
        cases = self.db.query(OutbreakCase).filter(
            OutbreakCase.zone == zone
        ).order_by(OutbreakCase.date.desc()).limit(4).all()
        
        if len(cases) < 4:
            # Not enough history to calculate growth rate
            return {
                "zone": zone,
                "is_at_risk": False,
                "latest_count": cases[0].case_count if cases else 0,
                "growth_rate": 0.0,
                "message": "Insufficient data to analyze outbreak."
            }
            
        # cases[0] is the most recent day (t)
        # cases[1] is t-1
        # cases[2] is t-2
        # cases[3] is t-3
        latest_count = cases[0].case_count
        prev_count = cases[3].case_count
        
        if prev_count == 0:
            growth_rate = 1.0 if latest_count > 0 else 0.0
        else:
            growth_rate = (latest_count - prev_count) / prev_count
            
        is_at_risk = (growth_rate >= threshold_rate) and (latest_count >= min_cases)
        
        return {
            "zone": zone,
            "is_at_risk": is_at_risk,
            "latest_count": latest_count,
            "previous_count": prev_count,
            "growth_rate": round(growth_rate, 4),
            "message": f"Outbreak detected! Case count grew by {round(growth_rate*100, 2)}% to {latest_count}." if is_at_risk else 
                       f"Zone is stable. Case growth is {round(growth_rate*100, 2)}%."
        }

    def get_all_zones_status(self, threshold_rate: float = 0.20, min_cases: int = 12):
        # Get unique zones
        zones = [r[0] for r in self.db.query(OutbreakCase.zone).distinct().all()]
        results = {}
        for z in zones:
            results[z] = self.check_zone_outbreak(z, threshold_rate, min_cases)
        return results
