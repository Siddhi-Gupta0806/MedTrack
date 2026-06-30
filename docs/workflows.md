# MedTrack System Workflows

This document outlines the step-by-step logic flows for MedTrack's core features. 

---

## 🔍 Workflow A: User Search ➡️ Book Flow

This sequence demonstrates how a user searches for clinics near their grid location and books a doctor.

```mermaid
sequenceDiagram
    actor Patient
    participant UI as React Frontend
    participant HF as Hospital Finder Agent
    participant BK as Booking Agent
    participant DB as SQLite DB

    Patient->>UI: Enter grid coords & specialty (e.g. Cardology)
    UI->>HF: Get hospitals(x, y, specialty)
    HF->>DB: Query hospitals filtering by specialty & capacity
    DB-->>HF: Return hospital rows
    HF->>HF: Calculate distance from user grid location
    HF->>HF: Sort list by closest proximity
    HF-->>UI: Return sorted hospitals list
    UI-->>Patient: Display closest hospitals with available beds

    Patient->>UI: Select doctor & click "Confirm Booking"
    UI->>BK: create_booking(patient, doctor_id, slot)
    BK->>DB: Save booking & decrement doctor available slot
    DB-->>BK: Confirm write
    BK-->>UI: Return booking confirmation detail
    UI-->>Patient: Show "Successfully booked appointment!"
```

---

## 💬 Workflow B: Chatbot Triage Flow

This sequence shows how a user consults the AI Triage chatbot to check symptoms, which automatically recommends a specialty.

```mermaid
sequenceDiagram
    actor Patient
    participant UI as React Frontend
    participant TR as Triage Chatbot Agent
    participant AI as Gemini API (or Local Fallback)

    Patient->>UI: Type message: "I have high fever and skin rash"
    UI->>TR: triage_chat(message, history)
    
    rect rgb(20, 20, 40)
        Note over TR, AI: If Gemini API Key present
        TR->>AI: generate_content(history + message)
        AI-->>TR: Return symptoms analysis & triage recommendations
    end
    
    rect rgb(40, 20, 20)
        Note over TR: If offline or no API Key
        TR->>TR: Fallback to keyword-based symptom scanner
    end

    TR->>TR: Extract urgency level & suggested specialty (Infectious Diseases)
    TR->>TR: Prepend permanent safety medical disclaimer
    TR-->>UI: Return response text + triage suggestion data
    UI-->>Patient: Display AI response with warning disclaimer
    UI-->>Patient: Show smart shortcut: "Find Infectious Diseases Clinics"
```

---

## ⚡ Workflow C: Outbreak Reallocation Loop (End-to-End)

This sequence details the core live demonstration: spiking cases, detecting the outbreak, shifting equipment, and redirecting patient bookings.

```mermaid
sequenceDiagram
    actor Judge as Hackathon Judge
    participant UI as React Frontend
    participant Orch as Orchestrator Agent
    participant OB as Outbreak Agent
    participant EQ as Equipment Agent
    participant BK as Booking Agent
    participant DB as SQLite DB

    Judge->>UI: Click "Simulate Outbreak"
    UI->>Orch: run_simulation()
    
    Note over Orch: Step 1: Inject Outbreak Spike
    Orch->>DB: Set today's cases for Zone A to 85
    
    Note over Orch: Step 2: Run Outbreak Agent
    Orch->>OB: check_zone_outbreak(Zone A)
    OB->>DB: Query recent daily cases time-series
    OB->>OB: Calculate growth rate (e.g. >20%)
    OB-->>Orch: Return "Zone A is At-Risk"
    
    Note over Orch: Step 3: Locate Overloaded Clinic
    Orch->>DB: Query hospitals in Zone A with low capacity
    DB-->>Orch: Return "City Infectious Clinic" (0 ventilators)
    
    Note over Orch: Step 4: Find Spare Capacity Donor
    Orch->>DB: Query hospitals in Zone A with high capacity
    DB-->>Orch: Return "St. Jude General Hospital" (8 ventilators)
    
    Note over Orch: Step 5: Transfer Equipment
    Orch->>EQ: transfer_equipment(St. Jude, City Infectious, ventilators, 3)
    EQ->>DB: Decrement St. Jude vents, increment City Infectious vents
    
    Note over Orch: Step 6: Activate Redirection
    Orch->>DB: Register RedirectRule(City Infectious -> St. Jude)
    
    Orch-->>UI: Return step-by-step actions log array
    UI-->>Judge: Stream logs live on dashboard timeline & update visual map

    Note over Judge: Step 7: Verify Closed-Loop Redirection
    Judge->>UI: Try booking doctor at "City Infectious Clinic"
    UI->>BK: create_booking(patient, doctor_at_overloaded)
    BK->>DB: Check for active RedirectRule
    DB-->>BK: Return active rule redirecting to St. Jude
    BK->>DB: Save booking under "St. Jude" with status "Redirected"
    BK-->>UI: Return redirection message
    UI-->>Judge: Display: "Booking auto-redirected due to active outbreak capacity!"
```
