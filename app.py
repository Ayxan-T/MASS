import streamlit as st
# import psycopg2
import json
import datetime

# ==========================================
# 1. DATABASE CONNECTION & AUDIT LOGGING
# ==========================================
@st.cache_resource
def init_db_connection():
    """Establishes a persistent PostgreSQL connection pool/client."""
    # Replace with your actual PostgreSQL connection string
    # e.g., "postgresql://user:password@localhost:5432/med_audit_db"
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="password",
        host="localhost",
        port="5432"
    )
    
    # Initialize audit table if it doesn't exist
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                session_id TEXT,
                stage TEXT,
                payload JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    return conn

def log_audit_event(stage: str, payload: dict):
    """Utility to write pipeline events directly to PostgreSQL."""
    try:
        conn = init_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_logs (session_id, stage, payload) VALUES (%s, %s, %s)",
                (st.session_state.get("session_id", "anon_session"), stage, json.dumps(payload))
            )
            conn.commit()
    except Exception as e:
        st.sidebar.error(f"Audit Log Error: {e}")

# Initialize session state tracking
if "session_id" not in st.session_state:
    st.session_state.session_id = f"sess_{int(datetime.datetime.now().timestamp())}"

# ==========================================
# 2. PIPELINE MOCK / ML LOGIC STUBS
# ==========================================
def extract_symptoms(text: str, image, audio) -> dict:
    """Step 1: Symptom & Keyword Extraction Model (Stub)"""
    extracted = {
        "text_processed": text,
        "keywords": ["chest_pain", "shortness_of_breath"] if "chest" in text.lower() else ["mild_headache"],
        "has_image": image is not None,
        "has_audio": audio is not None
    }
    return extracted

def check_red_flags(extracted_data: dict, profile: dict) -> tuple[bool, str]:
    """Step 2: Dual-Layer Safety & Red-Flag Engine"""
    keywords = extracted_data.get("keywords", [])
    
    # Example Emergency Trigger: Chest pain in high-risk demographic or explicit keyword
    is_chest_pain = "chest_pain" in keywords
    has_cardiac_history = "Heart Disease" in profile.get("conditions", [])
    
    if is_chest_pain or has_cardiac_history and "chest" in extracted_data["text_processed"].lower():
        dispatch_script = (
            f"EMERGENCY DISPATCH READOUT:\n"
            f"- Patient Age: {profile['age']}, Sex: {profile['sex']}\n"
            f"- History: {', '.join(profile['conditions']) if profile['conditions'] else 'None'}\n"
            f"- Reported Symptom: Severe chest discomfort / possible cardiac event.\n"
            f"- Location: {profile.get('location', 'GPS Auto-Detected')}"
        )
        return True, dispatch_script
    
    return False, ""

def generate_medical_guidance(extracted_data: dict, profile: dict) -> str:
    """Step 3: Medical RAG & Safe Response Generation"""
    allergies = profile.get("allergies", [])
    med_warning = ""
    if "Aspirin / NSAIDs" in allergies or "Unsure / Never Taken" in allergies:
        med_warning = "\n⚠️ **Safety Note:** Avoid OTC NSAIDs/Aspirin due to your allergy status."
        
    return (
        f"### Pre-Clinical Guidance\n"
        f"Based on your report, here are non-diagnostic first-aid instructions:\n\n"
        f"1. **Rest & Monitor:** Sit comfortably in a cool, quiet space.\n"
        f"2. **Hydration:** Sip water slowly.\n"
        f"3. **When to Seek Immediate Care:** If symptoms escalate to severe pain, dizziness, or vomiting.{med_warning}"
    )

# ==========================================
# 3. STREAMLIT UI LAYOUT
# ==========================================
st.set_page_config(page_title="Medical AI Support System", page_icon="🏥", layout="wide")

st.title("🏥 Medical AI Support System")
st.caption("Rapid Pre-Clinical Triage & Safety Guidance Engine")

# --- REQUIRED PERSONALIZED INFO ---
st.subheader("1. Required Baseline Context")

col1, col2 = st.columns(2)
with col1:
    age = st.number_input("Age*", min_value=0, max_value=120, value=45)
    sex = st.radio("Biological Sex*", ["Male", "Female"], horizontal=True)
    
    is_pregnant = "No"
    if sex == "Female":
        is_pregnant = st.radio("Pregnant?*", ["No", "Yes", "Unsure"], horizontal=True)

with col2:
    conditions_options = ["None", "Heart Disease", "High Blood Pressure", "Diabetes", "Asthma / Breathing Issues", "History of Stroke", "Immunocompromised"]
    selected_conditions = st.multiselect("High-Risk Conditions*", options=conditions_options, default=["None"])
    
    allergy_options = ["None", "Unsure / Never Taken", "Penicillin / Antibiotics", "Aspirin / NSAIDs", "Latex", "Other"]
    selected_allergies = st.multiselect("Known Allergies*", options=allergy_options, default=["None"])

# --- OPTIONAL CONTEXT ---
with st.expander("2. Optional Clinical Context (Medications, Vitals, Location)"):
    meds = st.text_input("Current Medications", placeholder="e.g., Metformin 500mg, Lisinopril")
    
    v_col1, v_col2, v_col3 = st.columns(3)
    with v_col1:
        hr = st.text_input("Heart Rate (BPM)", placeholder="72")
    with v_col2:
        bp = st.text_input("Blood Pressure (mmHg)", placeholder="120/80")
    with v_col3:
        spo2 = st.text_input("SpO2 (%)", placeholder="98")
        
    location = st.text_input("Current Location / Environment", placeholder="e.g., Home, Outdoors, Driving")

# Baseline Profile Object
user_profile = {
    "age": age,
    "sex": sex,
    "is_pregnant": is_pregnant,
    "conditions": selected_conditions,
    "allergies": selected_allergies,
    "medications": meds,
    "vitals": {"hr": hr, "bp": bp, "spo2": spo2},
    "location": location
}

st.divider()

# --- INPUT UI ---
st.subheader("3. Symptom Input")

input_text = st.text_area("Describe what is happening right now...", placeholder="e.g., Severe sharp pain in chest, feeling dizzy, started 10 mins ago")

in_col1, in_col2 = st.columns(2)
with in_col1:
    uploaded_image = st.file_uploader("Take Photo / Upload Image", type=["jpg", "png", "jpeg"])
with in_col2:
    audio_input = st.audio_input("Tap to Speak (Voice Record)")

# --- EXECUTION BUTTON ---
if st.button("Run Safety Check & Get Guidance", type="primary"):
    if not input_text and not uploaded_image and not audio_input:
        st.warning("Please provide symptoms via text, image, or voice input.")
    else:
        # FUSED PAYLOAD LOGGING
        fused_payload = {
            "profile": user_profile,
            "raw_text": input_text,
            "has_image": uploaded_image is not None,
            "has_audio": audio_input is not None
        }
        # log_audit_event("FUSED_INPUT_RECEIVED", fused_payload)

        # STEP 1: EXTRACTION
        extracted = extract_symptoms(input_text, uploaded_image, audio_input)
        # log_audit_event("STEP_1_SYMPTOM_EXTRACTION", extracted)

        # STEP 2: FAST RED FLAG CHECK
        is_emergency, dispatch_msg = check_red_flags(extracted, user_profile)

        # BRANCHING OUTCOME
        if is_emergency:
            # log_audit_event("STEP_3_DISPATCH_TRIGGERED", {"dispatch_message": dispatch_msg})
            
            # Outcome: Emergency Alert Screen
            st.error("🚨 EMERGENCY DETECTED — IMMEDIATE ACTION REQUIRED")
            st.button("📞 CALL 911 / EMERGENCY SERVICES NOW", type="primary")
            st.code(dispatch_msg, language="text")
            st.warning("Do not leave the patient unattended. Unlock front door for paramedics.")
            
        else:
            # STEP 3: MEDICAL RAG & RESPONSE
            guidance_response = generate_medical_guidance(extracted, user_profile)
            # log_audit_event("STEP_3_GUIDANCE_GENERATED", {"response": guidance_response})

            # Outcome: Info & Instructions
            st.success("Analysis Complete — Pre-Clinical Guidance")
            st.markdown(guidance_response)