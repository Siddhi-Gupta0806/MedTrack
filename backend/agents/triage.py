import os
from google import genai
from google.genai import types

DISCLAIMER = (
    "**DISCLAIMER:** This is an AI-powered triage chatbot and does NOT provide a professional "
    "medical diagnosis. If you are experiencing a life-threatening emergency, please visit the "
    "nearest Emergency Room (ER) immediately.\n\n"
)

SYSTEM_PROMPT = """
You are a helpful, professional medical triage chatbot for the MedTrack platform.
Your goals:
1. Greet the user, mention that you are a triage helper, and prompt them to describe their symptoms.
2. Analyze their symptoms and recommend the most appropriate specialty:
   - Chest pain, heart racing, high blood pressure -> Cardiology
   - Coughing, shortness of breath, asthma -> Pulmonology
   - High fever, skin rash, persistent infection, suspected contagious illness -> Infectious Diseases
   - General checkups, minor stomach ache, body aches, headaches -> General Medicine
3. Guide them on the next steps:
   - For severe/life-threatening symptoms, tell them to visit the ER immediately (Urgent triage).
   - For mild to moderate symptoms, advise them to use the Hospital Finder or Bookings tab on the platform.
4. Keep answers concise, empathetic, and clear.
5. Never state that you are making a medical diagnosis. Keep the tone helpful but advisory.
"""

class TriageAgent:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                # Initialize the Gemini SDK client
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini Client: {e}")
                self.client = None

    def triage_chat(self, history: list, user_message: str):
        """
        history: list of dicts with {"role": "user"|"model", "text": "..."}
        user_message: current message from user
        """
        # If no client, use the local fallback rule-based system
        if not self.client:
            return self._local_triage_fallback(user_message)

        try:
            # Prepare contents with history and current message
            contents = []
            for h in history:
                contents.append(
                    types.Content(
                        role="user" if h["role"] == "user" else "model",
                        parts=[types.Part.from_text(text=h["text"])]
                    )
                )
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message)]
                )
            )

            # Generate content using gemini-2.5-flash
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                )
            )
            
            # Prepend the mandatory disclaimer to the model's text response
            reply = DISCLAIMER + response.text
            return {
                "response": reply,
                "triage_level": self._infer_triage_level(reply),
                "specialty": self._infer_specialty(reply),
                "is_fallback": False
            }
        except Exception as e:
            print(f"Gemini API Error, falling back: {e}")
            return self._local_triage_fallback(user_message)

    def _local_triage_fallback(self, user_message: str):
        msg = user_message.lower()
        
        # Check for urgent/cardiac symptoms
        if any(w in msg for w in ["chest pain", "heart attack", "difficulty breathing", "shortness of breath", "severe pressure"]):
            reply = (
                DISCLAIMER +
                "I detected symptoms that could indicate a serious or cardiovascular emergency. "
                "Because of the severe nature of these symptoms, **please go to the nearest ER immediately** or dial emergency services.\n\n"
                "If this is a chronic, non-emergency issue, we recommend searching for a **Cardiology** or **Pulmonology** specialist."
            )
            triage_level = "Urgent"
            specialty = "Cardiology"
        # Check for pulmonary symptoms
        elif any(w in msg for w in ["cough", "wheez", "asthma", "bronchitis", "lung"]):
            reply = (
                DISCLAIMER +
                "Your symptoms suggest a respiratory or pulmonary concern. "
                "We recommend booking an appointment with a **Pulmonology** specialist.\n\n"
                "Please use the **Hospital Finder** on the sidebar to search for available clinics with pulmonology beds/ICUs."
            )
            triage_level = "Semi-urgent"
            specialty = "Pulmonology"
        # Check for infectious symptoms
        elif any(w in msg for w in ["fever", "rash", "infection", "contagious", "flu", "covid"]):
            reply = (
                DISCLAIMER +
                "Based on the symptoms described (such as fever or signs of infection), you may need a consult for an infectious disease. "
                "We recommend searching for an **Infectious Diseases** specialist.\n\n"
                "Please consult the **Hospital Finder** to find nearby clinics with specialized capacity."
            )
            triage_level = "Semi-urgent"
            specialty = "Infectious Diseases"
        else:
            reply = (
                DISCLAIMER +
                "Thank you for sharing your symptoms. For general concerns, body aches, or mild issues, a **General Medicine** doctor is standard. "
                "You can search for general hospitals and book an appointment through the platform.\n\n"
                "How else can I help guide your medical booking?"
            )
            triage_level = "General"
            specialty = "General Medicine"

        return {
            "response": reply,
            "triage_level": triage_level,
            "specialty": specialty,
            "is_fallback": True
        }

    def _infer_triage_level(self, text: str):
        txt = text.lower()
        if "er" in txt or "emergency" in txt or "urgent" in txt:
            return "Urgent"
        if "pulmonology" in txt or "cardiology" in txt or "infectious" in txt:
            return "Semi-urgent"
        return "General"

    def _infer_specialty(self, text: str):
        txt = text.lower()
        if "cardiology" in txt or "cardiac" in txt:
            return "Cardiology"
        if "pulmonology" in txt or "respiratory" in txt:
            return "Pulmonology"
        if "infectious" in txt or "fever" in txt:
            return "Infectious Diseases"
        return "General Medicine"
