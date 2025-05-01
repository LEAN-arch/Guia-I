import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import base64
import secrets
import os
import time
import logging
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import functools

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# Load environment variables
load_dotenv()
PASSWORD = os.getenv("SURVEY_PASSWORD", "securepassword123")
SALT = os.getenv("SURVEY_SALT", secrets.token_hex(16))
LOG_FILE = os.getenv("LOG_FILE", "nom035_log.csv")

# Language translations - Fixed structure and added missing translations
LANGUAGES = {
    "es": {
        "title": "Encuesta NOM-035-STPS-2018",
        "welcome": "Bienvenido a la encuesta NOM-035. Responda todas las preguntas con honestidad para ayudarnos a mejorar su entorno laboral.",
        # ... (rest of Spanish translations remain the same)
    },
    "en": {
        "title": "NOM-035-STPS-2018 Survey",
        "welcome": "Welcome to the NOM-035 survey. Please answer all questions honestly to help us improve your work environment.",
        # ... (rest of English translations remain the same)
    }
}

# Fixed question definitions - corrected structure and IDs
GUIDE1_QUESTIONS = [
    {"id": "g1_q1", "text": "¿Cuál es su nombre?", "text_en": "What is your name?", "type": "text_group", 
     "subfields": [
        {"id": "g1_q1_nombre", "label": "Nombre", "label_en": "First Name", "placeholder": "Ej. Juan", "placeholder_en": "E.g., John"},
        # ... (rest of subfields)
     ], "group": "personal_info"},
    # ... (rest of Guide 1 questions)
]

# Fixed Guide 2 questions - corrected structure
GUIDE2_QUESTIONS = [
    {"id": "g2_q1", "text": "Mi trabajo requiere gran esfuerzo físico.", "text_en": "My job requires significant physical effort.", 
     "type": "likert", "group": "work_conditions"},
    # ... (rest of Guide 2 questions)
]

# Fixed Guide 3 questions - corrected structure and fixed question 16
GUIDE3_QUESTIONS = [
    {"id": "g3_q1", "text": "Me informan claramente mis responsabilidades.", 
     "text_en": "I am clearly informed about my responsibilities.", "type": "likert"},
    # ... (other questions)
    {"id": "g3_q16", "text": "Hay respeto mutuo entre compañeros.", 
     "text_en": "There is mutual respect.", "type": "likert"},  # Fixed question 16
    {"id": "g3_q17", "text": "Mis compañeros me tratan con cortesía.", 
     "text_en": "My colleagues treat me with courtesy.", "type": "likert"},
    # ... (rest of questions)
]

# Cache question data - improved with type hints
@functools.lru_cache(maxsize=1)
def get_all_questions() -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Cache question data to improve performance with type safety."""
    return GUIDE1_QUESTIONS, GUIDE2_QUESTIONS, GUIDE3_QUESTIONS

# Password hashing - improved with error handling
def hash_password(password: str, salt: str) -> str:
    """Securely hash password with salt using SHA-256."""
    try:
        if not password or not salt:
            raise ValueError("Password and salt cannot be empty")
        salted_password = password + salt
        return hashlib.sha256(salted_password.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

# Initialize log - improved with retry logic
def initialize_log() -> None:
    """Initialize log file with headers if it doesn't exist with retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
                headers = (
                    ["timestamp"] +
                    [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" 
                    for subfield in q["subfields"]] +
                    [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"] +
                    [q["id"] for q in GUIDE2_QUESTIONS] +
                    [q["id"] for q in GUIDE3_QUESTIONS]
                )
                pd.DataFrame(columns=headers).to_csv(LOG_FILE, index=False)
                logger.info("Log file initialized successfully.")
            return
        except (PermissionError, IOError) as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("Failed to initialize log file after retries.")
                raise
            time.sleep(1)

# Session state initialization - improved validation
def initialize_session_state() -> None:
    """Initialize session state variables with validation."""
    if "initialized" not in st.session_state:
        defaults = {
            "responses": {},
            "guide1_complete": False,
            "guide2_complete": False,
            "guide3_complete": False,
            "has_trauma": False,
            "last_action_time": 0,
            "validation_errors": {"guide1": {}, "guide2": {}, "guide3": {}},
            "current_step": 1,
            "language_selector": "Español",
            "initialized": True
        }
        
        # Initialize response keys with type checking
        response_defaults = {}
        for q in GUIDE1_QUESTIONS:
            if q["type"] == "text_group":
                for subfield in q["subfields"]:
                    response_defaults[subfield["id"]] = ""
            else:
                response_defaults[q["id"]] = None if q["type"] in ["select", "yes_no"] else 0
        
        for q in GUIDE2_QUESTIONS + GUIDE3_QUESTIONS:
            response_defaults[q["id"]] = None
        
        defaults["responses"].update(response_defaults)
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        update_trauma_status(st.session_state.responses, LANGUAGES["es"])
        logger.info("Session state initialized successfully.")

# Validation - improved with comprehensive checks
def validate_responses(responses: Dict, guide_questions: List, guide_id: str, 
                      is_guide1: bool = False, lang_code: str = "es") -> Dict[str, str]:
    """Validate survey responses with comprehensive checks."""
    t = LANGUAGES[lang_code]
    errors = {}
    
    try:
        if is_guide1:
            # Validate text_group subfields
            for q in guide_questions:
                if q["type"] == "text_group":
                    for subfield in q["subfields"]:
                        if not subfield.get("optional", False):
                            value = responses.get(subfield["id"], "")
                            if not isinstance(value, str) or not value.strip():
                                field_label = subfield["label" if lang_code == "es" else "label_en"]
                                errors[subfield["id"]] = t["missing_field"].format(field=field_label)
            
            # Validate age (18-100)
            age = responses.get("g1_q2")
            if not isinstance(age, (int, float)) or not (18 <= age <= 100):
                errors["g1_q2"] = t["invalid_age"]
            
            # Validate years worked (0 <= years <= age)
            years_worked = responses.get("g1_q4")
            if isinstance(age, (int, float)) and isinstance(years_worked, (int, float)):
                if not (0 <= years_worked <= age):
                    errors["g1_q4"] = t["invalid_years_worked"]
        
        # Validate other questions
        for q in guide_questions:
            if q["type"] != "text_group":
                key = q["id"]
                value = responses.get(key)
                
                # Get valid responses based on question type
                if q["type"] == "yes_no":
                    valid_responses = [t["yes"], t["no"]]
                elif q["type"] == "likert":
                    valid_responses = get_valid_responses(lang_code)
                elif q["type"] == "select":
                    valid_responses = q["options" if lang_code == "es" else "options_en"]
                else:
                    valid_responses = []
                
                # Check if response is valid
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors[key] = t["missing_field"].format(field=q["text" if lang_code == "es" else "text_en"])
                elif valid_responses and value not in valid_responses:
                    errors[key] = t["missing_field"].format(field=q["text" if lang_code == "es" else "text_en"])
        
        return errors
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {"validation_error": t["unexpected_error"].format(error=str(e))}

# Main application flow - improved error handling
def main():
    """Main application entry point with comprehensive error handling."""
    try:
        # Initialize application
        st.set_page_config(
            page_title="NOM-035 Survey", 
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        initialize_session_state()
        lang = st.session_state.language_selector
        lang_code = "es" if lang == "Español" else "en"
        t = LANGUAGES[lang_code]
        
        # Apply custom CSS
        apply_custom_styles()
        
        # Render sidebar
        render_sidebar(lang_code)
        
        # Main content
        with st.container():
            st.title(t["title"])
            st.write(t["welcome"])
            
            # Show progress
            progress = calculate_progress()
            st.progress(progress)
            st.caption(f"{t['progress']}: {int(progress * 100)}%")
            
            # Guide navigation
            if not st.session_state.guide1_complete:
                render_guide1(lang_code, t)
            elif st.session_state.guide1_complete and st.session_state.has_trauma:
                if not st.session_state.guide2_complete:
                    render_guide2(lang_code, t)
                elif not st.session_state.guide3_complete:
                    render_guide3(lang_code, t)
                else:
                    st.success(t["completed"])
            else:
                st.success(t["completed"])
    
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(t["unexpected_error"].format(error=str(e)))

# Helper functions for rendering guides
def render_guide1(lang_code: str, t: Dict):
    """Render Guide 1 questions."""
    st.header(t["guide1"])
    st.caption(t["tooltip_guide1"])
    
    # Group questions by category
    groups = [
        ("personal_info", t["personal_info"], GUIDE1_QUESTIONS[:7]),
        ("traumatic_events", t["traumatic_events"], GUIDE1_QUESTIONS[7:13]),
        ("persistent_memories", t["persistent_memories"], GUIDE1_QUESTIONS[13:15]),
        ("avoidance_efforts", t["avoidance_efforts"], GUIDE1_QUESTIONS[15:22]),
        ("affectation", t["affectation"], GUIDE1_QUESTIONS[22:])
    ]
    
    for group_id, group_label, questions in groups:
        with st.expander(group_label, expanded=True):
            for q in questions:
                render_question(q, lang_code, t, "guide1")
    
    if st.button(t["submit"], key="submit_guide1"):
        errors = validate_responses(st.session_state.responses, GUIDE1_QUESTIONS, "guide1", True, lang_code)
        if errors:
            for error in errors.values():
                st.error(error)
        else:
            st.session_state.guide1_complete = True
            if not st.session_state.has_trauma:
                save_responses_to_log(st.session_state.responses)
            st.success(t["completed"])

def render_question(q: Dict, lang_code: str, t: Dict, guide_id: str):
    """Render a single question based on its type."""
    try:
        question_text = q["text" if lang_code == "es" else "text_en"]
        is_invalid = q["id"] in st.session_state.validation_errors[guide_id]
        
        st.markdown(f"**{question_text}**")
        
        if q["type"] == "text_group":
            for subfield in q["subfields"]:
                label = f"{subfield['label' if lang_code == 'es' else 'label_en']}"
                if subfield.get("optional", False):
                    label += f" {t['optional_field']}"
                
                value = st.text_input(
                    label,
                    value=st.session_state.responses.get(subfield["id"], ""),
                    placeholder=subfield["placeholder" if lang_code == "es" else "placeholder_en"],
                    disabled=st.session_state.get(f"{guide_id}_complete", False),
                    key=f"{subfield['id']}_input"
                )
                st.session_state.responses[subfield["id"]] = value
                
                if subfield["id"] in st.session_state.validation_errors[guide_id]:
                    st.error(st.session_state.validation_errors[guide_id][subfield["id"]])
        
        elif q["type"] == "number":
            value = st.number_input(
                question_text,
                min_value=0,
                max_value=100,
                value=int(st.session_state.responses.get(q["id"], 0)),
                disabled=st.session_state.get(f"{guide_id}_complete", False),
                key=f"{q['id']}_number"
            )
            st.session_state.responses[q["id"]] = value
            
            if is_invalid:
                st.error(st.session_state.validation_errors[guide_id][q["id"]])
        
        # ... (other question types)
    
    except Exception as e:
        logger.error(f"Error rendering question {q['id']}: {str(e)}")
        st.error(t["unexpected_error"].format(error="Question rendering failed"))

if __name__ == "__main__":
    main()
