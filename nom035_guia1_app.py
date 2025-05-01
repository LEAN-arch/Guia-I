import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import secrets
import os
import time
import logging
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import functools
from pathlib import Path
import uuid
import retrying
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# Load environment variables
load_dotenv()
PASSWORD = os.getenv("SURVEY_PASSWORD", "securepassword123")
SALT = os.getenv("SURVEY_SALT", secrets.token_hex(16))
LOG_FILE = os.getenv("LOG_FILE", "nom035_log.csv")

# Validate environment variables
if not all([PASSWORD, SALT, LOG_FILE]):
    logger.error("Missing required environment variables: SURVEY_PASSWORD, SURVEY_SALT, or LOG_FILE")
    st.error("Aplicación mal configurada. Contacte al soporte.")
    st.stop()

# Language translations (Spanish only)
LANGUAGES = {
    "es": {
        "title": "Encuesta NOM-035-STPS-2018",
        "welcome": "Bienvenido a la encuesta NOM-035. Responda todas las preguntas con honestidad para ayudarnos a mejorar su entorno laboral.",
        "guide1": "Guía I: Acontecimientos Traumáticos Severos",
        "guide2": "Guía II: Factores de Riesgo Psicosocial",
        "guide3": "Guía III: Entorno Organizacional Favorable",
        "submit": "Enviar",
        "previous": "Anterior",
        "download_log": "Descargar Registro",
        "refresh_log": "Refrescar Registro",
        "password_prompt": "Ingrese la contraseña:",
        "incorrect_password": "Contraseña incorrecta",
        "progress": "Progreso",
        "yes": "Sí",
        "no": "No",
        "always": "Siempre",
        "almost_always": "Casi siempre",
        "sometimes": "A veces",
        "almost_never": "Casi nunca",
        "never": "Nunca",
        "tooltip_guide1": "Indique si ha experimentado estos eventos en el último año.",
        "tooltip_guide2": "Evalúe los factores de riesgo en su entorno laboral.",
        "tooltip_guide3": "Evalúe el entorno organizacional en su lugar de trabajo.",
        "personal_info": "Información Personal",
        "traumatic_events": "Eventos Traumáticos",
        "persistent_memories": "Recuerdos Persistentes",
        "avoidance_efforts": "Esfuerzos por Evitar",
        "affectation": "Afectación",
        "work_conditions": "Condiciones de Trabajo",
        "workload_pace": "Carga y Ritmo de Trabajo",
        "control_decision": "Control y Toma de Decisiones",
        "work_relationships": "Relaciones Laborales",
        "work_life_balance": "Balance Trabajo-Vida y Crecimiento",
        "validation_error": "Por favor complete todos los campos requeridos correctamente.",
        "invalid_age": "La edad debe ser un número entre 18 y 100.",
        "invalid_years_worked": "Los años trabajados deben ser un número entre 0 y la edad ingresada.",
        "please_wait": "Por favor espere, procesando...",
        "log_refreshed": "Registro refrescado exitosamente.",
        "missing_field": "El campo '{field}' está incompleto o no válido.",
        "optional_field": "(Opcional)",
        "completed": "¡Guía completada exitosamente!",
        "file_not_found": "No hay datos en el registro.",
        "unexpected_error": "Ocurrió un error inesperado: {error}. Por favor intenta de nuevo o contacta al soporte.",
        "debug_prompt": "Para más detalles, habilite DEBUG_MODE=True en el archivo .env y reinicie la aplicación."
    }
}

# Question Definitions
GUIDE1_QUESTIONS = [
    {"id": "g1_q1", "text": "¿Cuál es su nombre?", "type": "text_group", "subfields": [
        {"id": "g1_q1_nombre", "label": "Nombre", "placeholder": "Ej. Juan"},
        {"id": "g1_q1_apellido", "label": "Apellido", "placeholder": "Ej. Pérez"},
        {"id": "g1_q1_segundo_apellido", "label": "Segundo apellido", "optional": True, "placeholder": "Ej. García"}
    ], "group": "personal_info"},
    {"id": "g1_q2", "text": "¿Qué edad tienes? (Solo incluye el número de años, ej. 21)", "type": "number", "group": "personal_info"},
    {"id": "g1_q3", "text": "¿Cuál es tu género?", "type": "select", "options": ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"], "group": "personal_info"},
    {"id": "g1_q4", "text": "¿Cuántos años llevas trabajando para esta empresa? (Solo incluye el número de años, ej. 3)", "type": "number", "group": "personal_info"},
    {"id": "g1_q5", "text": "¿En qué departamento labora?", "type": "select", "options": ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"], "group": "personal_info"},
    {"id": "g1_q6", "text": "¿Cuál es su función?", "type": "select", "options": ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"], "group": "personal_info"},
    {"id": "g1_q7", "text": "¿Cuál es su lugar de trabajo? (Seleccione el lugar donde pase más tiempo)", "type": "select", "options": ["Planta 1", "Planta 2", "Planta 3"], "group": "personal_info"},
    {"id": "g1_q8", "text": "¿Ha presenciado o sufrido un accidente grave en el trabajo?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q9", "text": "¿Ha presenciado o sufrido un asalto en el trabajo?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q10", "text": "¿Ha presenciado o sufrido actos violentos en el trabajo?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q11", "text": "¿Ha presenciado o sufrido un secuestro en el trabajo?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q12", "text": "¿Ha presenciado o sufrido amenazas en el trabajo?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q13", "text": "¿Ha experimentado situaciones de riesgo para su vida o salud en el trabajo?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q14", "text": "¿Ha tenido recuerdos recurrentes que le causan malestar?", "type": "yes_no", "group": "persistent_memories"},
    {"id": "g1_q15", "text": "¿Ha tenido sueños recurrentes que le causan malestar?", "type": "yes_no", "group": "persistent_memories"},
    {"id": "g1_q16", "text": "¿Evita sentimientos o situaciones que le recuerdan el evento?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q17", "text": "¿Evita actividades o personas que le recuerdan el evento?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q18", "text": "¿Tiene dificultad para recordar partes del evento?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q19", "text": "¿Ha perdido interés en sus actividades cotidianas?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q20", "text": "¿Se siente distante de los demás?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q21", "text": "¿Tiene dificultad para expresar sus sentimientos?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q22", "text": "¿Siente que su vida será más corta?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q23", "text": "¿Tiene problemas para dormir?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q24", "text": "¿Ha estado más irritable de lo usual?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q25", "text": "¿Tiene dificultad para concentrarse?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q26", "text": "¿Se siente nervioso o en alerta constante?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q27", "text": "¿Se sobresalta fácilmente?", "type": "yes_no", "group": "affectation"}
]

GUIDE2_QUESTIONS = [
    {"id": "g2_q1", "text": "Mi trabajo requiere gran esfuerzo físico.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q2", "text": "Me siento expuesto(a) a riesgos físicos en mi trabajo.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q3", "text": "Manejo herramientas que representan riesgo.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q4", "text": "Trabajo en un lugar con ruidos fuertes.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q5", "text": "Trabajo en un lugar con temperaturas extremas.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q6", "text": "Estoy expuesto(a) a materiales peligrosos.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q7", "text": "Mi trabajo requiere estar de pie mucho tiempo.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q8", "text": "Realizo movimientos repetitivos en mi trabajo.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q9", "text": "Mi trabajo requiere posturas incómodas.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q10", "text": "Tengo que mover objetos pesados.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q11", "text": "Puedo tomar pausas cuando las necesito.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q12", "text": "Puedo decidir la cantidad de trabajo que realizo.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q13", "text": "Tengo libertad para decidir cómo realizar mi trabajo.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q14", "text": "Mi trabajo requiere decisiones difíciles.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q15", "text": "Tengo que atender varias tareas a la vez.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q16", "text": "Mi trabajo requiere alta concentración.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q17", "text": "La cantidad de trabajo es excesiva.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q18", "text": "Trabajo horas extras con frecuencia.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q19", "text": "Debo estar disponible fuera de mi horario.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q20", "text": "Mi ritmo de trabajo es muy acelerado.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q21", "text": "Mi jefe me presiona para cumplir objetivos.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q22", "text": "Recibo órdenes contradictorias.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q23", "text": "Mi jefe me da instrucciones claras.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q24", "text": "Mi jefe me apoya en problemas laborales.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q25", "text": "Mi jefe confía en mi capacidad.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q26", "text": "Mi jefe me trata con respeto.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q27", "text": "Me siento valorado(a) por mis compañeros.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q28", "text": "Tengo buena comunicación con mis compañeros.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q29", "text": "Hay un ambiente de colaboración.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q30", "text": "Recibo críticas negativas con frecuencia.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q31", "text": "Mis compañeros me excluyen.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q32", "text": "He sido víctima de burlas en el trabajo.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q33", "text": "He sido testigo de discriminación.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q34", "text": "Mi trabajo interfiere con mi familia.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q35", "text": "Mi trabajo afecta mi vida personal.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q36", "text": "Tengo tiempo para actividades personales.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q37", "text": "Mi horario de trabajo es flexible.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q38", "text": "Recibo capacitación para mi trabajo.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q39", "text": "Tengo oportunidades de crecimiento.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q40", "text": "Siento que mi trabajo es estable.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q41", "text": "Mi salario es adecuado.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q42", "text": "Recibo beneficios adicionales.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q43", "text": "Mi trabajo es importante para la empresa.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q44", "text": "Me siento motivado(a) en mi trabajo.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q45", "text": "Mi trabajo me permite desarrollar habilidades.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q46", "text": "Mi trabajo tiene un propósito claro.", "type": "likert", "group": "work_life_balance"}
]

GUIDE3_QUESTIONS = [
    {"id": "g3_q1", "text": "Me informan claramente mis responsabilidades.", "type": "likert"},
    {"id": "g3_q2", "text": "Recibo instrucciones claras para mi trabajo.", "type": "likert"},
    {"id": "g3_q3", "text": "Mi jefe comunica lo que espera de mí.", "type": "likert"},
    {"id": "g3_q4", "text": "Tengo los recursos necesarios para mi trabajo.", "type": "likert"},
    {"id": "g3_q5", "text": "Tengo acceso a herramientas necesarias.", "type": "likert"},
    {"id": "g3_q6", "text": "Recibo retroalimentación sobre mi desempeño.", "type": "likert"},
    {"id": "g3_q7", "text": "Mi jefe reconoce mi trabajo bien hecho.", "type": "likert"},
    {"id": "g3_q8", "text": "Me siento valorado(a) por mis contribuciones.", "type": "likert"},
    {"id": "g3_q9", "text": "Recibo reconocimiento por mis logros.", "type": "likert"},
    {"id": "g3_q10", "text": "Se promueve la igualdad de oportunidades.", "type": "likert"},
    {"id": "g3_q11", "text": "Siento que se me trata con justicia.", "type": "likert"},
    {"id": "g3_q12", "text": "Mis opiniones son tomadas en cuenta.", "type": "likert"},
    {"id": "g3_q13", "text": "Puedo expresar mis ideas.", "type": "likert"},
    {"id": "g3_q14", "text": "Se fomenta la participación en decisiones.", "type": "likert"},
    {"id": "g3_q15", "text": "Siento que pertenezco a un equipo.", "type": "likert"},
    {"id": "g3_q16", "text": "Existe respeto mutuo.", "type": "likert"},
    {"id": "g3_q17", "text": "Mis compañeros me tratan con cortesía.", "type": "likert"},
    {"id": "g3_q18", "text": "Se promueve la colaboración entre compañeros.", "type": "likert"},
    {"id": "g3_q19", "text": "Hay un buen ambiente laboral.", "type": "likert"},
    {"id": "g3_q20", "text": "Se fomenta la confianza entre empleados.", "type": "likert"},
    {"id": "g3_q21", "text": "La empresa promueve un mejor clima laboral.", "type": "likert"},
    {"id": "g3_q22", "text": "Recibo apoyo para balancear mi vida laboral.", "type": "likert"},
    {"id": "g3_q23", "text": "La empresa ofrece beneficios para mi bienestar.", "type": "likert"},
    {"id": "g3_q24", "text": "La empresa se preocupa por mi salud.", "type": "likert"},
    {"id": "g3_q25", "text": "Se promueve el respeto a la diversidad.", "type": "likert"},
    {"id": "g3_q26", "text": "La empresa valora mi trabajo.", "type": "likert"}
]

# Validate Questions
def validate_questions(questions: List[Dict], guide_name: str) -> bool:
    """Validate question data structure."""
    valid_types = {"text_group", "number", "select", "yes_no", "likert"}
    for q in questions:
        try:
            if not all(key in q for key in ["id", "text", "type"]):
                logger.error(f"Invalid question in {guide_name}: Missing required keys in {q}")
                return False
            if q["type"] not in valid_types:
                logger.error(f"Invalid question type in {guide_name}: {q['type']} in {q}")
                return False
            if q["type"] == "text_group" and "subfields" not in q:
                logger.error(f"Missing subfields in text_group question in {guide_name}: {q}")
                return False
            if q["type"] == "select" and "options" not in q:
                logger.error(f"Missing options in select question in {guide_name}: {q}")
                return False
        except Exception as e:
            logger.error(f"Error validating question in {guide_name}: {str(e)}")
            return False
    return True

# Cache question data
@functools.lru_cache(maxsize=1)
def get_all_questions() -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Cache and validate question data."""
    if not all(validate_questions(q, name) for q, name in [
        (GUIDE1_QUESTIONS, "Guide 1"),
        (GUIDE2_QUESTIONS, "Guide 2"),
        (GUIDE3_QUESTIONS, "Guide 3")
    ]):
        logger.error("Question validation failed. Application cannot proceed.")
        st.error("Critical error: Invalid question data. Please contact support.")
        raise ValueError("Invalid question data")
    return GUIDE1_QUESTIONS, GUIDE2_QUESTIONS, GUIDE3_QUESTIONS

# Valid responses for Guides 2 and 3
@functools.lru_cache(maxsize=1)
def get_valid_responses() -> List[str]:
    """Return valid response options for Guides 2 and 3."""
    return [
        LANGUAGES["es"]["always"],
        LANGUAGES["es"]["almost_always"],
        LANGUAGES["es"]["sometimes"],
        LANGUAGES["es"]["almost_never"],
        LANGUAGES["es"]["never"]
    ]

# Utility Functions
def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using SHA-256."""
    try:
        if not isinstance(password, str) or not isinstance(salt, str):
            raise ValueError("Password and salt must be strings")
        salted_password = password + salt
        return hashlib.sha256(salted_password.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

CORRECT_PASSWORD_HASH = hash_password(PASSWORD, SALT)

@retrying.retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000,
    retry_on_exception=lambda e: isinstance(e, (PermissionError, IOError, FileNotFoundError, OSError))
)
def initialize_log() -> None:
    """Initialize log file with headers if it doesn't exist."""
    log_path = Path(LOG_FILE)
    try:
        if not log_path.exists():
            headers = (
                ["timestamp"] +
                [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" for subfield in q["subfields"]] +
                [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"] +
                [q["id"] for q in GUIDE2_QUESTIONS] +
                [q["id"] for q in GUIDE3_QUESTIONS]
            )
            pd.DataFrame(columns=headers).to_csv(log_path, index=False)
            logger.info("Log file initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize log file: {str(e)}")
        raise

@retrying.retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000,
    retry_on_exception=lambda e: isinstance(e, (PermissionError, IOError, FileNotFoundError, OSError))
)
def save_responses_to_log(responses: Dict) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Save responses to log file with timestamp."""
    log_path = Path(LOG_FILE)
    try:
        initialize_log()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        responses_copy = responses.copy()
        responses_copy["timestamp"] = timestamp
        df = pd.DataFrame([responses_copy])
        try:
            existing_df = pd.read_csv(log_path)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            existing_df = pd.DataFrame(columns=df.columns)
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        updated_df.to_csv(log_path, index=False)
        logger.info(f"Responses saved to log with timestamp {timestamp}.")
        return df, timestamp
    except Exception as e:
        logger.error(f"Failed to save responses to log: {str(e)}")
        raise

@retrying.retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000,
    retry_on_exception=lambda e: isinstance(e, (PermissionError, IOError, FileNotFoundError, OSError))
)
def refresh_log() -> bool:
    """Refresh log file by recreating it."""
    try:
        initialize_log()
        logger.info("Log file refreshed successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh log: {str(e)}")
        raise

# Session State Initialization
def initialize_session_state() -> None:
    """Initialize session state variables with all possible response keys."""
    try:
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
                "initialized": True,
                "session_id": str(uuid.uuid4())
            }
            
            # Initialize response keys
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
                st.session_state[key] = st.session_state.get(key, value)
            
            # Check for trauma based on existing responses
            update_trauma_status(st.session_state.responses, LANGUAGES["es"])
            logger.info(f"Session state initialized with session_id: {st.session_state.session_id}")
    except Exception as e:
        logger.error(f"Error initializing session state: {str(e)}")
        st.error(f"Failed to initialize application: {str(e)}")

def update_trauma_status(responses: Dict, t: Dict) -> None:
    """Update has_trauma based on Guide I responses."""
    try:
        trauma_questions = [q["id"] for q in GUIDE1_QUESTIONS if q["type"] == "yes_no"]
        st.session_state.has_trauma = any(responses.get(qid) == t["yes"] for qid in trauma_questions)
        logger.debug(f"Trauma status updated: has_trauma={st.session_state.has_trauma}")
    except Exception as e:
        logger.error(f"Error updating trauma status: {str(e)}")
        st.error("Failed to update trauma status.")

# Streamlit Configuration
st.set_page_config(page_title="NOM-035 Survey", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .main {
        background-color: #F8FAFC;
        font-family: 'Inter', sans-serif;
        color: #1F2937;
    }
    .stButton>button {
        background-color: #10B981;
        color: white;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #059669;
        transform: translateY(-1px);
    }
    .stButton>button:focus {
        outline: 2px solid #059669;
        outline-offset: 2px;
    }
    .stButton>button.secondary {
        background-color: #6B7280;
    }
    .stButton>button.secondary:hover {
        background-color: #4B5563;
    }
    .stProgress .st-bo {
        background-color: #10B981;
    }
    .container {
        max-width: 1280px;
        margin: 0 auto;
        padding: 24px;
    }
    .card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        padding: 24px;
        margin-bottom: 24px;
    }
    .header {
        font-size: 28px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 16px;
    }
    .subheader {
        font-size: 20px;
        font-weight: 600;
        color: #1F2937;
        margin-bottom: 12px;
    }
    .question {
        font-size: 16px;
        font-weight: 500;
        color: #374151;
        margin-bottom: 12px;
    }
    .tooltip {
        color: #6B7280;
        font-size: 14px;
        margin-bottom: 16px;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }
    .invalid-field {
        border-color: #EF4444 !important;
        box-shadow: 0 0 0 3px rgba(239,68,68,0.1) !important;
    }
    .error-message {
        color: #EF4444;
        font-size: 14px;
        margin-top: 4px;
    }
    .stRadio > div {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
    }
    .stRadio label {
        background: #F3F4F6;
        padding: 8px 16px;
        border-radius: 9999px;
        font-size: 14px;
        cursor: pointer;
        transition: background-color 0.2s ease;
    }
    .stRadio label:hover {
        background: #E5E7EB;
    }
    .stSelectbox select {
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        padding: 10px;
    }
    .st-expander {
        background: white;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
    }
    .st-expander summary {
        font-weight: 600;
        font-size: 18px;
        color: #1F2937;
        padding: 12px;
    }
    .success-message {
        color: #10B981;
        font-size: 16px;
        font-weight: 600;
        text-align: center;
        padding: 12px;
        background: #ECFDF5;
        border-radius: 8px;
        margin-bottom: 16px;
    }
    .spinner {
        display: inline-block;
        width: 24px;
        height: 24px;
        border: 3px solid #D1D5DB;
        border-top: 3px solid #10B981;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    @media (max-width: 640px) {
        .container { padding: 16px; }
        .header { font-size: 24px; }
        .subheader { font-size: 18px; }
        .question { font-size: 14px; }
        .stRadio > div { flex-direction: column; }
        .stButton>button { width: 100%; padding: 12px; }
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
def render_sidebar() -> None:
    """Render the sidebar with log management."""
    t = LANGUAGES["es"]
    try:
        with st.sidebar:
            st.markdown(f'<h3 class="subheader">Opciones</h3>', unsafe_allow_html=True)

            st.markdown(f'<h3 class="subheader">{t["download_log"]}</h3>', unsafe_allow_html=True)
            password_download = st.text_input(
                t["password_prompt"],
                type="password",
                key="download_password",
                label="Download Password"
            )
            if st.button(t["download_log"], key="download_button"):
                if action_lock():
                    try:
                        if not password_download:
                            st.error(t["incorrect_password"])
                            logger.debug("Empty password provided for download")
                            return
                        hashed_input = hash_password(password_download, SALT)
                        if hashed_input == CORRECT_PASSWORD_HASH:
                            log_path = Path(LOG_FILE)
                            if not log_path.exists():
                                st.warning(t["file_not_found"])
                                logger.debug("Log file not found for download")
                            elif log_path.stat().st_size == 0:
                                st.warning(t["file_not_found"])
                                logger.debug("Log file is empty")
                            else:
                                try:
                                    with log_path.open("rb") as f:
                                        csv_bytes = f.read()
                                    b64 = base64.b64encode(csv_bytes).decode()
                                    href = f'<a href="data:file/csv;base64,{b64}" download="nom035_log.csv" role="button" aria-label="Download Log CSV">Download Log CSV</a>'
                                    st.markdown(href, unsafe_allow_html=True)
                                    logger.info("Log file downloaded successfully")
                                except (PermissionError, IOError, OSError) as e:
                                    logger.error(f"Failed to read log file: {str(e)}")
                                    st.error(f"{t['unexpected_error'].format(error='No se pudo leer el archivo de registro')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="No se pudo leer el archivo de registro"))
                        else:
                            st.error(t["incorrect_password"])
                            logger.debug("Incorrect password provided for download")
                    except ValueError as e:
                        logger.error(f"Password hashing error: {str(e)}")
                        st.error(f"{t['unexpected_error'].format(error='Error de autenticación')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Error de autenticación"))
                    except Exception as e:
                        logger.error(f"Unexpected error during log download: {str(e)}")
                        st.error(f"{t['unexpected_error'].format(error='Descarga de registro fallida')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Descarga de registro fallida"))

            st.markdown(f'<h3 class="subheader">{t["refresh_log"]}</h3>', unsafe_allow_html=True)
            password_refresh = st.text_input(
                t["password_prompt"],
                type="password",
                key="refresh_password",
                label="Refresh Password"
            )
            if st.button(t["refresh_log"], key="refresh_button"):
                if action_lock():
                    try:
                        if not password_refresh:
                            st.error(t["incorrect_password"])
                            logger.debug("Empty password provided for refresh")
                            return
                        hashed_input = hash_password(password_refresh, SALT)
                        if hashed_input == CORRECT_PASSWORD_HASH:
                            if refresh_log():
                                st.success(t["log_refreshed"])
                                logger.info("Log file refreshed successfully")
                            else:
                                st.error("No se pudo refrescar el registro.")
                                logger.error("Log refresh returned False")
                        else:
                            st.error(t["incorrect_password"])
                            logger.debug("Incorrect password provided for refresh")
                    except ValueError as e:
                        logger.error(f"Password hashing error: {str(e)}")
                        st.error(f"{t['unexpected_error'].format(error='Error de autenticación')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Error de autenticación"))
                    except Exception as e:
                        logger.error(f"Unexpected error during log refresh: {str(e)}")
                        st.error(f"{t['unexpected_error'].format(error='Refresco de registro fallido')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Refresco de registro fallido"))
    except Exception as e:
        logger.error(f"Error rendering sidebar: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error='No se pudo cargar la barra lateral')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="No se pudo cargar la barra lateral"))

def action_lock() -> bool:
    """Prevent rapid button clicks with a 1-second debounce."""
    try:
        current_time = time.time()
        last_action_time = st.session_state.get("last_action_time", 0)
        if current_time - last_action_time < 1:
            logger.debug(f"Action lock triggered: Too frequent clicks (current: {current_time}, last: {last_action_time})")
            st.warning("Por favor espere, procesando...")
            return False
        st.session_state.last_action_time = current_time
        logger.debug(f"Action lock passed: Updated last_action_time to {current_time}")
        return True
    except Exception as e:
        logger.error(f"Error in action_lock: {str(e)}")
        return False

def calculate_progress() -> float:
    """Calculate survey completion progress, accounting for optional fields."""
    try:
        total_questions = (
            sum(1 for q in GUIDE1_QUESTIONS if q["type"] != "text_group") +
            sum(1 for subfield in GUIDE1_QUESTIONS[0]["subfields"] if not subfield.get("optional", False))
        )
        if st.session_state.has_trauma:
            total_questions += len(GUIDE2_QUESTIONS) + len(GUIDE3_QUESTIONS)
        
        answered_questions = 0
        required_keys = (
            [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" for subfield in q["subfields"] if not subfield.get("optional", False)] +
            [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"]
        )
        if st.session_state.has_trauma:
            required_keys += [q["id"] for q in GUIDE2_QUESTIONS] + [q["id"] for q in GUIDE3_QUESTIONS]
        
        for key in required_keys:
            value = st.session_state.responses.get(key)
            if value is not None and value != "" and value != 0:
                answered_questions += 1
        
        progress = answered_questions / total_questions if total_questions > 0 else 0
        logger.debug(f"Progress calculated: {answered_questions}/{total_questions} = {progress:.2f}")
        return progress
    except Exception as e:
        logger.error(f"Error calculating progress: {str(e)}")
        return 0.0

def validate_responses(responses: Dict, guide_questions: List, guide_id: str, is_guide1: bool = False) -> Dict[str, str]:
    """Validate survey responses and return field-specific errors."""
    try:
        t = LANGUAGES["es"]
        errors = {}
        
        if is_guide1:
            # Validate text_group subfields
            for q in guide_questions:
                if q["type"] == "text_group":
                    for subfield in q["subfields"]:
                        if not subfield.get("optional", False):
                            value = responses.get(subfield["id"], "")
                            if not isinstance(value, str) or not value.strip():
                                field_label = subfield["label"]
                                errors[subfield["id"]] = t["missing_field"].format(field=field_label)
                                logger.debug(f"Validation failed for {subfield['id']}: Value='{value}'")
        
            # Validate age
            age = responses.get("g1_q2")
            if not isinstance(age, (int, float)) or not (18 <= age <= 100):
                errors["g1_q2"] = t["invalid_age"]
                logger.debug(f"Validation failed for g1_q2: Value='{age}'")
        
            # Validate years worked
            years_worked = responses.get("g1_q4")
            if isinstance(age, (int, float)) and isinstance(years_worked, (int, float)) and not (0 <= years_worked <= age):
                errors["g1_q4"] = t["invalid_years_worked"]
                logger.debug(f"Validation failed for g1_q4: Value='{years_worked}'")
        
        # Validate other questions
        for q in guide_questions:
            if q["type"] != "text_group":
                key = q["id"]
                value = responses.get(key)
                try:
                    if q["type"] == "yes_no":
                        valid_responses = [t["yes"], t["no"]]
                    elif q["type"] == "likert":
                        valid_responses = get_valid_responses()
                    else:  # select
                        valid_responses = q["options"]
                except KeyError as e:
                    logger.error(f"Missing key {str(e)} for question {key}")
                    errors[key] = t["unexpected_error"].format(error=f"Invalid question configuration for {key}")
                    continue
                
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors[key] = t["missing_field"].format(field=q["text"])
                    logger.debug(f"Validation failed for {key}: Value='{value}'")
                elif value not in valid_responses:
                    errors[key] = t["missing_field"].format(field=q["text"])
                    logger.debug(f"Validation failed for {key}: Invalid response='{value}'")
        
        st.session_state.validation_errors[guide_id] = errors
        logger.debug(f"Validation completed for {guide_id}: {len(errors)} errors found")
        return errors
    except Exception as e:
        logger.error(f"Error in validate_responses: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error='Validation failed')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Validation failed"))
        return {}

def render_question(q: Dict, t: Dict, guide_id: str) -> None:
    """Render a single question based on its type."""
    try:
        question_text = q["text"]
        is_invalid = q["id"] in st.session_state.validation_errors[guide_id]
        st.markdown(
            f'<div role="radiogroup" aria-describedby="question-{q["id"]}" class="radio-group">'
            f'<p class="question" id="question-{q["id"]}" role="heading" aria-label="{question_text}">{question_text}</p>',
            unsafe_allow_html=True
        )

        if q["type"] == "text_group":
            for subfield in q["subfields"]:
                label = subfield["label"]
                if subfield.get("optional", False):
                    label += f" {t['optional_field']}"
                is_subfield_invalid = subfield["id"] in st.session_state.validation_errors[guide_id]
                response = st.text_input(
                    label,
                    key=subfield["id"],
                    placeholder=subfield["placeholder"],
                    value=st.session_state.responses.get(subfield["id"], ""),
                    disabled=st.session_state.get(f"{guide_id}_complete", False)
                )
                st.session_state.responses[subfield["id"]] = response
                if is_subfield_invalid:
                    st.markdown(f'<p class="error-message">{st.session_state.validation_errors[guide_id][subfield["id"]]}</p>', unsafe_allow_html=True)
        elif q["type"] == "number":
            response = st.number_input(
                question_text,
                min_value=0,
                max_value=100,
                step=1,
                key=q["id"],
                format="%d",
                label_visibility="collapsed",
                value=int(st.session_state.responses.get(q["id"], 0) or 0),
                disabled=st.session_state.get(f"{guide_id}_complete", False)
            )
            st.session_state.responses[q["id"]] = response
            if is_invalid:
                st.markdown(f'<p class="error-message">{st.session_state.validation_errors[guide_id][q["id"]]}</p>', unsafe_allow_html=True)
        elif q["type"] == "select":
            response = st.selectbox(
                question_text,
                q["options"],
                key=q["id"],
                label_visibility="collapsed",
                index=q["options"].index(st.session_state.responses.get(q["id"])) if st.session_state.responses.get(q["id"]) in q["options"] else None,
                placeholder="Seleccione",
                disabled=st.session_state.get(f"{guide_id}_complete", False)
            )
            st.session_state.responses[q["id"]] = response
            if is_invalid:
                st.markdown(f'<p class="error-message">{st.session_state.validation_errors[guide_id][q["id"]]}</p>', unsafe_allow_html=True)
        elif q["type"] == "yes_no":
            response = st.radio(
                question_text,
                [t["yes"], t["no"]],
                key=q["id"],
                label_visibility="collapsed",
                index=0 if st.session_state.responses.get(q["id"]) == t["yes"] else 1 if st.session_state.responses.get(q["id"]) == t["no"] else None,
                disabled=st.session_state.get(f"{guide_id}_complete", False)
            )
            st.session_state.responses[q["id"]] = response
            if response == t["yes"]:
                update_trauma_status(st.session_state.responses, t)
            if is_invalid:
                st.markdown(f'<p class="error-message">{st.session_state.validation_errors[guide_id][q["id"]]}</p>', unsafe_allow_html=True)
        elif q["type"] == "likert":
            response = st.radio(
                question_text,
                get_valid_responses(),
                key=q["id"],
                label_visibility="collapsed",
                index=get_valid_responses().index(st.session_state.responses.get(q["id"])) if st.session_state.responses.get(q["id"]) in get_valid_responses() else None,
                disabled=st.session_state.get(f"{guide_id}_complete", False)
            )
            st.session_state.responses[q["id"]] = response
            if is_invalid:
                st.markdown(f'<p class="error-message">{st.session_state.validation_errors[guide_id][q["id"]]}</p>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering question {q['id']}: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error='Question rendering failed')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Question rendering failed"))

# Main App
def main():
    try:
        initialize_session_state()
        t = LANGUAGES["es"]

        render_sidebar()

        st.markdown('<div class="container">', unsafe_allow_html=True)
        st.markdown(f'<h1 class="header">{t["title"]}</h1>', unsafe_allow_html=True)
        st.write(t["welcome"])

        progress = calculate_progress()
        st.progress(min(progress, 1.0))  # Ensure progress doesn't exceed 100%
        st.markdown(f'<p class="tooltip">{t["progress"]}: {int(progress * 100)}%</p>', unsafe_allow_html=True)

        # Guide I
        if not st.session_state.guide1_complete:
            st.markdown(f'<h2 class="header">{t["guide1"]}</h2>', unsafe_allow_html=True)
            st.markdown(f'<p class="tooltip">{t["tooltip_guide1"]}</p>', unsafe_allow_html=True)

            guide1_groups = [
                ("personal_info", t["personal_info"], GUIDE1_QUESTIONS[:7]),
                ("traumatic_events", t["traumatic_events"], GUIDE1_QUESTIONS[7:13]),
                ("persistent_memories", t["persistent_memories"], GUIDE1_QUESTIONS[13:15]),
                ("avoidance_efforts", t["avoidance_efforts"], GUIDE1_QUESTIONS[15:22]),
                ("affectation", t["affectation"], GUIDE1_QUESTIONS[22:])
            ]

            for group_id, group_label, questions in guide1_groups:
                with st.expander(group_label, expanded=True):
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    for q in questions:
                        render_question(q, t, "guide1")
                    st.markdown('</div>', unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])
            with col2:
                if st.button(t["submit"], key="submit_guide1"):
                    if action_lock():
                        try:
                            errors = validate_responses(st.session_state.responses, GUIDE1_QUESTIONS, "guide1", is_guide1=True)
                            if errors:
                                for error in errors.values():
                                    st.error(error)
                            else:
                                st.session_state.guide1_complete = True
                                if not st.session_state.has_trauma:
                                    save_responses_to_log(st.session_state.responses)
                                st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)
                        except Exception as e:
                            logger.error(f"Error submitting Guide 1: {str(e)}")
                            st.error(f"{t['unexpected_error'].format(error='Guide 1 submission failed')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Guide 1 submission failed"))

        # Guide II
        elif st.session_state.guide1_complete and st.session_state.has_trauma and not st.session_state.guide2_complete:
            st.markdown(f'<h2 class="header">{t["guide2"]}</h2>', unsafe_allow_html=True)
            st.markdown(f'<p class="tooltip">{t["tooltip_guide2"]}</p>', unsafe_allow_html=True)

            guide2_groups = [
                ("work_conditions", t["work_conditions"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_conditions"]),
                ("workload_pace", t["workload_pace"], [q for q in GUIDE2_QUESTIONS if q["group"] == "workload_pace"]),
                ("control_decision", t["control_decision"], [q for q in GUIDE2_QUESTIONS if q["group"] == "control_decision"]),
                ("work_relationships", t["work_relationships"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_relationships"]),
                ("work_life_balance", t["work_life_balance"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_life_balance"])
            ]

            for group_id, group_label, questions in guide2_groups:
                with st.expander(group_label, expanded=True):
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    for q in questions:
                        render_question(q, t, "guide2")
                    st.markdown('</div>', unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(t["previous"], key="prev_guide2", type="secondary"):
                    if action_lock():
                        st.session_state.guide1_complete = False
                        st.session_state.validation_errors["guide1"] = {}
            with col2:
                if st.button(t["submit"], key="submit_guide2"):
                    if action_lock():
                        try:
                            errors = validate_responses(st.session_state.responses, GUIDE2_QUESTIONS, "guide2")
                            if errors:
                                for error in errors.values():
                                    st.error(error)
                            else:
                                st.session_state.guide2_complete = True
                                st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)
                        except Exception as e:
                            logger.error(f"Error submitting Guide 2: {str(e)}")
                            st.error(f"{t['unexpected_error'].format(error='Guide 2 submission failed')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Guide 2 submission failed"))

        # Guide III
        elif st.session_state.guide2_complete and st.session_state.has_trauma and not st.session_state.guide3_complete:
            st.markdown(f'<h2 class="header">{t["guide3"]}</h2>', unsafe_allow_html=True)
            st.markdown(f'<p class="tooltip">{t["tooltip_guide3"]}</p>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            for q in GUIDE3_QUESTIONS:
                render_question(q, t, "guide3")
            st.markdown('</div>', unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(t["previous"], key="prev_guide3", type="secondary"):
                    if action_lock():
                        st.session_state.guide2_complete = False
                        st.session_state.validation_errors["guide2"] = {}
            with col2:
                if st.button(t["submit"], key="submit_guide3"):
                    if action_lock():
                        try:
                            errors = validate_responses(st.session_state.responses, GUIDE3_QUESTIONS, "guide3")
                            if errors:
                                for error in errors.values():
                                    st.error(error)
                            else:
                                st.session_state.guide3_complete = True
                                save_responses_to_log(st.session_state.responses)
                                st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)
                        except Exception as e:
                            logger.error(f"Error submitting Guide 3: {str(e)}")
                            st.error(f"{t['unexpected_error'].format(error='Guide 3 submission failed')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Guide 3 submission failed"))

        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Unexpected error in main: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error='Application failed to load')} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Application failed to load"))

if __name__ == "__main__":
    main()
