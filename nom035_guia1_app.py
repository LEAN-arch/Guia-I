import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import base64
import secrets
import os
import time
import logging
from typing import Dict, List, Tuple

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
DEBUG_MODE = True

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
PASSWORD = os.getenv("NOM35", "NOM35")
SALT = os.getenv("NOM35", secrets.token_hex(16))

# Validate environment variables
if not PASSWORD or not SALT:
    logger.error("Missing SURVEY_PASSWORD or SURVEY_SALT in .env file")
    st.error("Configuration error: Missing password or salt. Contact support.")

# Language translations
LANGUAGES = {
    "es": {
        "title": "Encuesta NOM-035-STPS-2018",
        "welcome": "Bienvenido a la encuesta NOM-035. Responda todas las preguntas con honestidad para ayudarnos a mejorar su entorno laboral.",
        "guide1": "Guía I: Acontecimientos Traumáticos Severos",
        "guide2": "Guía II: Factores de Riesgo Psicosocial",
        "guide3": "Guía III: Entorno Organizacional Favorable",
        "submit": "Enviar",
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
        "file_error": "Error al acceder al archivo de registro. Contacte al soporte.",
        "sidebar_error": "Error al cargar la barra lateral. Intente de nuevo o contacte al soporte.",
        "version_error": "Streamlit version incompatibility. Please ensure Streamlit version >= 1.12.0 is installed."
    },
    "en": {
        "title": "NOM-035-STPS-2018 Survey",
        "welcome": "Welcome to the NOM-035 survey. Please answer all questions honestly to help us improve your work environment.",
        "guide1": "Guide I: Severe Traumatic Events",
        "guide2": "Guide II: Psychosocial Risk Factors",
        "guide3": "Guide III: Favorable Organizational Environment",
        "submit": "Submit",
        "download_log": "Download Log",
        "refresh_log": "Refresh Log",
        "password_prompt": "Enter the password:",
        "incorrect_password": "Incorrect password",
        "progress": "Progress",
        "yes": "Yes",
        "no": "No",
        "always": "Always",
        "almost_always": "Almost always",
        "sometimes": "Sometimes",
        "almost_never": "Almost never",
        "never": "Never",
        "tooltip_guide1": "Indicate if you have experienced these events in the past year.",
        "tooltip_guide2": "Assess the risk factors in your work environment.",
        "tooltip_guide3": "Assess the organizational environment in your workplace.",
        "personal_info": "Personal Information",
        "traumatic_events": "Traumatic Events",
        "persistent_memories": "Persistent Memories",
        "avoidance_efforts": "Avoidance Efforts",
        "affectation": "Affectation",
        "work_conditions": "Work Conditions",
        "workload_pace": "Workload and Pace",
        "control_decision": "Control and Decision-Making",
        "work_relationships": "Work Relationships",
        "work_life_balance": "Work-Life Balance and Growth",
        "validation_error": "Please complete all required fields correctly.",
        "invalid_age": "Age must be a number between 18 and 100.",
        "invalid_years_worked": "Years worked must be a number between 0 and the entered age.",
        "please_wait": "Please wait, processing...",
        "log_refreshed": "Log refreshed successfully.",
        "missing_field": "The field '{field}' is incomplete or invalid.",
        "optional_field": "(Optional)",
        "completed": "Guide completed successfully!",
        "file_error": "Error accessing the log file. Contact support.",
        "sidebar_error": "Error loading the sidebar. Try again or contact support.",
        "version_error": "Streamlit version incompatibility. Please ensure Streamlit version >= 1.12.0 is installed."
    }
}

# Question Definitions
GUIDE1_QUESTIONS = [
    {
        "id": "g1_q1",
        "text": "¿Cuál es su nombre?",
        "text_en": "What is your name?",
        "type": "text_group",
        "subfields": [
            {"id": "g1_q1_nombre", "label": "Nombre", "label_en": "First Name", "placeholder": "Ej. Juan", "placeholder_en": "E.g., John"},
            {"id": "g1_q1_apellido", "label": "Apellido", "label_en": "Last Name", "placeholder": "Ej. Pérez", "placeholder_en": "E.g., Smith"},
            {
                "id": "g1_q1_segundo_apellido",
                "label": "Segundo apellido",
                "label_en": "Second Last Name",
                "optional": True,
                "placeholder": "Ej. García",
                "placeholder_en": "E.g., Garcia",
            },
        ],
        "group": "personal_info",
    },
    {
        "id": "g1_q2",
        "text": "¿Qué edad tienes? (Solo incluye el número de años, ej. 21)",
        "text_en": "How old are you? (Only include the number of years, e.g., 21)",
        "type": "number",
        "group": "personal_info",
    },
    {
        "id": "g1_q3",
        "text": "¿Cuál es tu género?",
        "text_en": "What is your gender?",
        "type": "select",
        "options": ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"],
        "options_en": ["Female", "Male", "LGTBTTTIQ+", "Other"],
        "group": "personal_info",
    },
    {
        "id": "g1_q4",
        "text": "¿Cuántos años llevas trabajando para esta empresa? (Solo incluye el número de años, ej. 3)",
        "text_en": "How many years have you been working for this company? (Only include the number of years, e.g., 3)",
        "type": "number",
        "group": "personal_info",
    },
    {
        "id": "g1_q5",
        "text": "¿En qué departamento labora?",
        "text_en": "In which department do you work?",
        "type": "select",
        "options": [
            "Mantenimiento",
            "Control de Calidad",
            "Manufactura",
            "Ventas",
            "Producción",
            "Recursos Humanos",
            "Ventas y Marketing",
            "Contabilidad y Finanzas",
            "Administración",
        ],
        "options_en": [
            "Maintenance",
            "Quality Control",
            "Manufacturing",
            "Sales",
            "Production",
            "Human Resources",
            "Sales and Marketing",
            "Accounting and Finance",
            "Administration",
        ],
        "group": "personal_info",
    },
    {
        "id": "g1_q6",
        "text": "¿Cuál es su función?",
        "text_en": "What is your role?",
        "type": "select",
        "options": ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"],
        "options_en": ["Operator", "Technician", "Engineer", "Analyst", "Supervisor", "Manager", "Director"],
        "group": "personal_info",
    },
    {
        "id": "g1_q7",
        "text": "¿Cuál es su lugar de trabajo? (Seleccione el lugar donde pase más tiempo)",
        "text_en": "What is your workplace? (Select the place where you spend most of your time)",
        "type": "select",
        "options": ["Planta 1", "Planta 2", "Planta 3"],
        "options_en": ["Plant 1", "Plant 2", "Plant 3"],
        "group": "personal_info",
    },
    {
        "id": "g1_q8",
        "text": "¿Ha presenciado o sufrido un accidente grave en el trabajo?",
        "text_en": "Have you witnessed or suffered a serious accident at work?",
        "type": "yes_no",
        "group": "traumatic_events",
    },
    {
        "id": "g1_q9",
        "text": "¿Ha presenciado o sufrido un asalto en el trabajo?",
        "text_en": "Have you witnessed or suffered an assault at work?",
        "type": "yes_no",
        "group": "traumatic_events",
    },
    {
        "id": "g1_q10",
        "text": "¿Ha presenciado o sufrido actos violentos en el trabajo?",
        "text_en": "Have you witnessed or suffered violent acts at work?",
        "type": "yes_no",
        "group": "traumatic_events",
    },
    {
        "id": "g1_q11",
        "text": "¿Ha presenciado o sufrido un secuestro en el trabajo?",
        "text_en": "Have you witnessed or suffered a kidnapping at work?",
        "type": "yes_no",
        "group": "traumatic_events",
    },
    {
        "id": "g1_q12",
        "text": "¿Ha presenciado o sufrido amenazas en el trabajo?",
        "text_en": "Have you witnessed or suffered threats at work?",
        "type": "yes_no",
        "group": "traumatic_events",
    },
    {
        "id": "g1_q13",
        "text": "¿Ha experimentado situaciones de riesgo para su vida o salud en el trabajo?",
        "text_en": "Have you experienced situations that put your life or health at risk at work?",
        "type": "yes_no",
        "group": "traumatic_events",
    },
    {
        "id": "g1_q14",
        "text": "¿Ha tenido recuerdos recurrentes que le causan malestar?",
        "text_en": "Have you had recurrent memories causing discomfort?",
        "type": "yes_no",
        "group": "persistent_memories",
    },
    {
        "id": "g1_q15",
        "text": "¿Ha tenido sueños recurrentes que le causan malestar?",
        "text_en": "Have you had recurrent dreams causing discomfort?",
        "type": "yes_no",
        "group": "persistent_memories",
    },
    {
        "id": "g1_q16",
        "text": "¿Evita sentimientos o situaciones que le recuerdan el evento?",
        "text_en": "Do you avoid feelings or situations that remind you of the event?",
        "type": "yes_no",
        "group": "avoidance_efforts",
    },
    {
        "id": "g1_q17",
        "text": "¿Evita actividades o personas que le recuerdan el evento?",
        "text_en": "Do you avoid activities or people that remind you of the event?",
        "type": "yes_no",
        "group": "avoidance_efforts",
    },
    {
        "id": "g1_q18",
        "text": "¿Tiene dificultad para recordar partes del evento?",
        "text_en": "Do you have difficulty remembering parts of the event?",
        "type": "yes_no",
        "group": "avoidance_efforts",
    },
    {
        "id": "g1_q19",
        "text": "¿Ha perdido interés en sus actividades cotidianas?",
        "text_en": "Have you lost interest in daily activities?",
        "type": "yes_no",
        "group": "avoidance_efforts",
    },
    {
        "id": "g1_q20",
        "text": "¿Se siente distante de los demás?",
        "text_en": "Do you feel distant from others?",
        "type": "yes_no",
        "group": "avoidance_efforts",
    },
    {
        "id": "g1_q21",
        "text": "¿Tiene dificultad para expresar sus sentimientos?",
        "text_en": "Do you have difficulty expressing feelings?",
        "type": "yes_no",
        "group": "avoidance_efforts",
    },
    {
        "id": "g1_q22",
        "text": "¿Siente que su vida será más corta?",
        "text_en": "Do you feel your life will be shorter?",
        "type": "yes_no",
        "group": "avoidance_efforts",
    },
    {
        "id": "g1_q23",
        "text": "¿Tiene problemas para dormir?",
        "text_en": "Do you have trouble sleeping?",
        "type": "yes_no",
        "group": "affectation",
    },
    {
        "id": "g1_q24",
        "text": "¿Ha estado más irritable de lo usual?",
        "text_en": "Have you been more irritable than usual?",
        "type": "yes_no",
        "group": "affectation",
    },
    {
        "id": "g1_q25",
        "text": "¿Tiene dificultad para concentrarse?",
        "text_en": "Do you have difficulty concentrating?",
        "type": "yes_no",
        "group": "affectation",
    },
    {
        "id": "g1_q26",
        "text": "¿Se siente nervioso o en alerta constante?",
        "text_en": "Do you feel nervous or constantly on alert?",
        "type": "yes_no",
        "group": "affectation",
    },
    {
        "id": "g1_q27",
        "text": "¿Se sobresalta fácilmente?",
        "text_en": "Do you get startled easily?",
        "type": "yes_no",
        "group": "affectation",
    },
]

GUIDE2_QUESTIONS = [
    {"id": "g2_q1", "text": "Mi trabajo requiere gran esfuerzo físico.", "text_en": "My job requires significant physical effort.", "group": "work_conditions"},
    {"id": "g2_q2", "text": "Me siento expuesto(a) a riesgos físicos en mi trabajo.", "text_en": "I feel exposed to physical risks at work.", "group": "work_conditions"},
    {"id": "g2_q3", "text": "Manejo herramientas que representan riesgo.", "text_en": "I handle tools that pose a risk.", "group": "work_conditions"},
    {"id": "g2_q4", "text": "Trabajo en un lugar con ruidos fuertes.", "text_en": "I work in a place with loud noises.", "group": "work_conditions"},
    {"id": "g2_q5", "text": "Trabajo en un lugar con temperaturas extremas.", "text_en": "I work in a place with extreme temperatures.", "group": "work_conditions"},
    {"id": "g2_q6", "text": "Estoy expuesto(a) a materiales peligrosos.", "text_en": "I am exposed to hazardous materials.", "group": "work_conditions"},
    {"id": "g2_q7", "text": "Mi trabajo requiere estar de pie mucho tiempo.", "text_en": "My job requires standing for long periods.", "group": "work_conditions"},
    {"id": "g2_q8", "text": "Realizo movimientos repetitivos en mi trabajo.", "text_en": "I perform repetitive movements at work.", "group": "work_conditions"},
    {"id": "g2_q9", "text": "Mi trabajo requiere posturas incómodas.", "text_en": "My job requires uncomfortable postures.", "group": "work_conditions"},
    {"id": "g2_q10", "text": "Tengo que mover objetos pesados.", "text_en": "I have to move heavy objects.", "group": "work_conditions"},
    {"id": "g2_q11", "text": "Puedo tomar pausas cuando las necesito.", "text_en": "I can take breaks when needed.", "group": "workload_pace"},
    {"id": "g2_q12", "text": "Puedo decidir la cantidad de trabajo que realizo.", "text_en": "I can decide the amount of work I do.", "group": "workload_pace"},
    {"id": "g2_q13", "text": "Tengo libertad para decidir cómo realizar mi trabajo.", "text_en": "I have freedom to decide how to do my job.", "group": "workload_pace"},
    {"id": "g2_q14", "text": "Mi trabajo requiere decisiones difíciles.", "text_en": "My job requires difficult decisions.", "group": "workload_pace"},
    {"id": "g2_q15", "text": "Tengo que atender varias tareas a la vez.", "text_en": "I handle multiple tasks at once.", "group": "workload_pace"},
    {"id": "g2_q16", "text": "Mi trabajo requiere alta concentración.", "text_en": "My job requires high concentration.", "group": "workload_pace"},
    {"id": "g2_q17", "text": "La cantidad de trabajo es excesiva.", "text_en": "The amount of work is excessive.", "group": "workload_pace"},
    {"id": "g2_q18", "text": "Trabajo horas extras con frecuencia.", "text_en": "I work overtime frequently.", "group": "workload_pace"},
    {"id": "g2_q19", "text": "Debo estar disponible fuera de mi horario.", "text_en": "I must be available outside working hours.", "group": "workload_pace"},
    {"id": "g2_q20", "text": "Mi ritmo de trabajo es muy acelerado.", "text_en": "My work pace is very fast.", "group": "workload_pace"},
    {"id": "g2_q21", "text": "Mi jefe me presiona para cumplir objetivos.", "text_en": "My boss pressures me to meet goals.", "group": "control_decision"},
    {"id": "g2_q22", "text": "Recibo órdenes contradictorias.", "text_en": "I receive contradictory orders.", "group": "control_decision"},
    {"id": "g2_q23", "text": "Mi jefe me da instrucciones claras.", "text_en": "My boss gives clear instructions.", "group": "control_decision"},
    {"id": "g2_q24", "text": "Mi jefe me apoya en problemas laborales.", "text_en": "My boss supports me with work problems.", "group": "control_decision"},
    {"id": "g2_q25", "text": "Mi jefe confía en mi capacidad.", "text_en": "My boss trusts my ability.", "group": "control_decision"},
    {"id": "g2_q26", "text": "Mi jefe me trata con respeto.", "text_en": "My boss treats me with respect.", "group": "work_relationships"},
    {"id": "g2_q27", "text": "Me siento valorado(a) por mis compañeros.", "text_en": "I feel valued by my colleagues.", "group": "work_relationships"},
    {"id": "g2_q28", "text": "Tengo buena comunicación con mis compañeros.", "text_en": "I have good communication with coworkers.", "group": "work_relationships"},
    {"id": "g2_q29", "text": "Hay un ambiente de colaboración.", "text_en": "There is a collaborative environment.", "group": "work_relationships"},
    {"id": "g2_q30", "text": "Recibo críticas negativas con frecuencia.", "text_en": "I receive negative criticism frequently.", "group": "work_relationships"},
    {"id": "g2_q31", "text": "Mis compañeros me excluyen.", "text_en": "My colleagues exclude me.", "group": "work_relationships"},
    {"id": "g2_q32", "text": "He sido víctima de burlas en el trabajo.", "text_en": "I have been a victim of teasing at work.", "group": "work_relationships"},
    {"id": "g2_q33", "text": "He sido testigo de discriminación.", "text_en": "I have witnessed discrimination.", "group": "work_relationships"},
    {"id": "g2_q34", "text": "Mi trabajo interfiere con mi familia.", "text_en": "My job interferes with family responsibilities.", "group": "work_life_balance"},
    {"id": "g2_q35", "text": "Mi trabajo afecta mi vida personal.", "text_en": "My job negatively affects my personal life.", "group": "work_life_balance"},
    {"id": "g2_q36", "text": "Tengo tiempo para actividades personales.", "text_en": "I have time for personal activities.", "group": "work_life_balance"},
    {"id": "g2_q37", "text": "Mi horario de trabajo es flexible.", "text_en": "My work schedule is flexible.", "group": "work_life_balance"},
    {"id": "g2_q38", "text": "Recibo capacitación para mi trabajo.", "text_en": "I receive training for my job.", "group": "work_life_balance"},
    {"id": "g2_q39", "text": "Tengo oportunidades de crecimiento.", "text_en": "I have opportunities for growth.", "group": "work_life_balance"},
    {"id": "g2_q40", "text": "Siento que mi trabajo es estable.", "text_en": "I feel my job is stable.", "group": "work_life_balance"},
    {"id": "g2_q41", "text": "Mi salario es adecuado.", "text_en": "My salary is adequate.", "group": "work_life_balance"},
    {"id": "g2_q42", "text": "Recibo beneficios adicionales.", "text_en": "I receive additional benefits.", "group": "work_life_balance"},
    {"id": "g2_q43", "text": "Mi trabajo es importante para la empresa.", "text_en": "My job is important to the company.", "group": "work_life_balance"},
    {"id": "g2_q44", "text": "Me siento motivado(a) en mi trabajo.", "text_en": "I feel motivated at work.", "group": "work_life_balance"},
    {"id": "g2_q45", "text": "Mi trabajo me permite desarrollar habilidades.", "text_en": "My job allows skill development.", "group": "work_life_balance"},
    {"id": "g2_q46", "text": "Mi trabajo tiene un propósito claro.", "text_en": "My job has a clear purpose.", "group": "work_life_balance"},
]

GUIDE3_QUESTIONS = [
    {"id": "g3_q1", "text": "Me informan claramente mis responsabilidades.", "text_en": "I am clearly informed about my responsibilities."},
    {"id": "g3_q2", "text": "Recibo instrucciones claras para mi trabajo.", "text_en": "I receive clear instructions for my job."},
    {"id": "g3_q3", "text": "Mi jefe comunica lo que espera de mí.", "text_en": "My boss communicates expectations clearly."},
    {"id": "g3_q4", "text": "Tengo los recursos necesarios para mi trabajo.", "text_en": "I have the necessary resources for my job."},
    {"id": "g3_q5", "text": "Tengo acceso a herramientas necesarias.", "text_en": "I have access to necessary tools."},
    {"id": "g3_q6", "text": "Recibo retroalimentación sobre mi desempeño.", "text_en": "I receive feedback on my performance."},
    {"id": "g3_q7", "text": "Mi jefe reconoce mi trabajo bien hecho.", "text_en": "My boss acknowledges my good work."},
    {"id": "g3_q8", "text": "Me siento valorado(a) por mis contribuciones.", "text_en": "I feel valued for my contributions."},
    {"id": "g3_q9", "text": "Recibo reconocimiento por mis logros.", "text_en": "I receive recognition for my achievements."},
    {"id": "g3_q10", "text": "Se promueve la igualdad de oportunidades.", "text_en": "Equal opportunities are promoted."},
    {"id": "g3_q11", "text": "Siento que se me trata con justicia.", "text_en": "I feel treated fairly."},
    {"id": "g3_q12", "text": "Mis opiniones son tomadas en cuenta.", "text_en": "My opinions are considered."},
    {"id": "g3_q13", "text": "Puedo expresar mis ideas.", "text_en": "I can express my ideas."},
    {"id": "g3_q14", "text": "Se fomenta la participación en decisiones.", "text_en": "Participation in decisions is encouraged."},
    {"id": "g3_q15", "text": "Siento que pertenezco a un equipo.", "text_en": "I feel part of a team."},
    {"id": "g3_q16", "text": "Hay un ambiente de respeto mutuo.", "text_en": "There is mutual respect."},
    {"id": "g3_q17", "text": "Mis compañeros me tratan con cortesía.", "text_en": "My colleagues treat me with courtesy."},
    {"id": "g3_q18", "text": "Se promueve la colaboración entre compañeros.", "text_en": "Collaboration is promoted."},
    {"id": "g3_q19", "text": "Hay un buen ambiente laboral.", "text_en": "There is a good work environment."},
    {"id": "g3_q20", "text": "Se fomenta la confianza entre empleados.", "text_en": "Trust among employees is fostered."},
    {"id": "g3_q21", "text": "La empresa promueve un mejor clima laboral.", "text_en": "The company promotes a better work environment."},
    {"id": "g3_q22", "text": "Recibo apoyo para balancear mi vida laboral.", "text_en": "I receive support to balance work and life."},
    {"id": "g3_q23", "text": "La empresa ofrece beneficios para mi bienestar.", "text_en": "The company offers benefits for my well-being."},
    {"id": "g3_q24", "text": "La empresa se preocupa por mi salud.", "text_en": "The company cares about my health."},
    {"id": "g3_q25", "text": "Se promueve el respeto a la diversidad.", "text_en": "Respect for diversity is promoted."},
    {"id": "g3_q26", "text": "La empresa valora mi trabajo.", "text_en": "The company values my work."},
]

# Utility Functions
def hash_password(password: str, salt: str) -> str:
    try:
        salted_password = password + salt
        return hashlib.sha256(salted_password.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error in hash_password: {str(e)}")
        return ""

def action_lock() -> bool:
    try:
        current_time = time.time()
        if current_time - st.session_state.last_action_time < 1:
            st.warning(t["please_wait"])
            return False
        st.session_state.last_action_time = current_time
        logger.debug("action_lock: Allowed action")
        return True
    except Exception as e:
        logger.error(f"Error in action_lock: {str(e)}")
        return False

def initialize_log():
    try:
        if not os.path.exists(LOG_FILE):
            headers = (
                ["timestamp"]
                + [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" for subfield in q["subfields"]]
                + [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"]
                + [q["id"] for q in GUIDE2_QUESTIONS]
                + [q["id"] for q in GUIDE3_QUESTIONS]
            )
            pd.DataFrame(columns=headers).to_csv(LOG_FILE, index=False)
    except Exception as e:
        logger.error(f"Error initializing log file: {str(e)}")
        raise

def save_responses_to_log() -> Tuple[pd.DataFrame, str]:
    try:
        initialize_log()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        responses = st.session_state.responses.copy()
        responses["timestamp"] = timestamp
        df = pd.DataFrame([responses])
        existing_df = pd.read_csv(LOG_FILE)
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        updated_df.to_csv(LOG_FILE, index=False)
        return df, timestamp
    except Exception as e:
        logger.error(f"Error saving responses to log: {str(e)}")
        raise

def refresh_log() -> bool:
    try:
        initialize_log()
        return True
    except Exception as e:
        logger.error(f"Error refreshing log: {str(e)}")
        raise

CORRECT_PASSWORD_HASH = hash_password(PASSWORD, SALT)

# Session State Initialization
if "responses" not in st.session_state:
    st.session_state.responses = {
        "g1_q1_nombre": "",
        "g1_q1_apellido": "",
        "g1_q1_segundo_apellido": "",
    }
if "guide1_complete" not in st.session_state:
    st.session_state.guide1_complete = False
if "guide2_complete" not in st.session_state:
    st.session_state.guide2_complete = False
if "guide3_complete" not in st.session_state:
    st.session_state.guide3_complete = False
if "has_trauma" not in st.session_state:
    st.session_state.has_trauma = False
if "last_action_time" not in st.session_state:
    st.session_state.last_action_time = 0
if "validation_errors" not in st.session_state:
    st.session_state.validation_errors = {}
if "show_guide2" not in st.session_state:
    st.session_state.show_guide2 = False

# Streamlit Configuration
st.set_page_config(page_title="NOM-035 Survey", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    * { box-sizing: border-box; }
    html, body, #root, .stApp, .block-container, [data-testid="stAppViewContainer"], [data-testid] {
        margin: 0 !important;
        padding: 0 !important;
        top: 0 !important;
        position: relative;
    }
    .stApp {
        background-color: #F5F7FA;
        /* border: 1px solid green; */ /* Debug */
    }
    .block-container {
        /* border: 1px solid yellow; */ /* Debug */
    }
    .main {
        font-family: 'Roboto', sans-serif;
        padding: 0 !important;
        margin: 0 !important;
        background-color: #F5F7FA;
    }
    .stButton>button {
        background-color: #2E7D32;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1B5E20;
        transform: scale(1.05);
    }
    .stProgress .st-bo {
        background-color: #2E7D32;
    }
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px 20px 20px;
        min-height: 100vh;
        /* border: 1px solid red; */ /* Debug */
    }
    .card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 20px;
        margin-bottom: 20px;
    }
    .header {
        font-size: 22px;
        font-weight: 700;
        color: #1A237E;
        margin: 0;
        padding-top: 2px;
        /* border: 1px solid blue; */ /* Debug */
    }
    .welcome-text {
        font-size: 13px;
        color: #333;
        margin: 0;
        padding-top: 2px;
    }
    .question {
        font-size: 18px;
        font-weight: 500;
        color: #333;
        margin-bottom: 10px;
    }
    .tooltip {
        color: #666;
        font-size: 14px;
        margin-bottom: 20px;
    }
    .stTextInput input {
        border: 2px solid #E0E0E0;
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
        transition: border-color 0.3s ease;
    }
    .stTextInput input:focus {
        border-color: #1565C0;
    }
    .invalid-field input {
        border-color: #D32F2F !important;
    }
    .error-message {
        color: #D32F2F;
        font-size: 14px;
        margin-top: 5px;
    }
    .stRadio > div {
        flex-direction: row;
        flex-wrap: wrap;
        gap: 10px;
    }
    .stRadio label {
        background: #E8F0FE;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 16px;
        transition: background-color 0.3s ease;
    }
    .stRadio label:hover {
        background: #BBDEFB;
    }
    .stSelectbox div[role="combobox"] {
        border: 2px solid #E0E0E0;
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
    }
    .st-expander {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .st-expander summary {
        font-weight: 500;
        font-size: 18px;
        color: #1565C0;
    }
    .success-message {
        color: #2E7D32;
        font-size: 16px;
        font-weight: 500;
        text-align: center;
        animation: fadeIn 0.5s ease-in;
    }
    .guide-section {
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.5s ease, transform 0.5s ease;
    }
    .guide-section.visible {
        opacity: 1;
        transform: translateY(0);
    }
    .disabled-section {
        opacity: 0.5;
        pointer-events: none;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @media (max-width: 600px) {
        .container {
            padding: 0 10px 10px 10px;
            margin: 0;
        }
        .header {
            font-size: 16px;
            margin: 0;
            padding-top: 1px;
        }
        .welcome-text {
            font-size: 11px;
            margin: 0;
            padding-top: 1px;
        }
        .question {
            font-size: 14px;
        }
        .stRadio > div {
            flex-direction: column;
        }
        .stButton>button {
            width: 100%;
        }
    }
    </style>
    <script>
        function scrollToGuide2() {
            const guide2 = document.getElementById('guide2-section');
            if (guide2) {
                guide2.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
        function maintainScrollPosition() {
            const currentPosition = window.scrollY;
            setTimeout(() => window.scrollTo(0, currentPosition), 0);
        }
        window.addEventListener('load', () => {
            const container = document.querySelector('.container');
            const stApp = document.querySelector('.stApp');
            const header = document.querySelector('.header');
            // Log offsets
            console.log('Container Offset Top:', container?.getBoundingClientRect().top);
            console.log('stApp Offset Top:', stApp?.getBoundingClientRect().top);
            console.log('Header Offset Top:', header?.getBoundingClientRect().top);
            // Log styles
            console.log('Container Styles:', getComputedStyle(container));
            console.log('stApp Styles:', getComputedStyle(stApp));
            // Log parent elements
            let parent = container?.parentElement;
            let parentChain = [];
            while (parent && parent !== document.body) {
                parentChain.push({
                    tag: parent.tagName,
                    class: parent.className,
                    offsetTop: parent.getBoundingClientRect().top,
                    styles: getComputedStyle(parent)
                });
                parent = parent.parentElement;
            }
            console.log('Parent Elements:', parentChain);
            // Log DOM structure
            console.log('Container HTML:', container?.outerHTML);
            console.log('stApp HTML:', stApp?.outerHTML);
        });
    </script>
""",
    unsafe_allow_html=True,
)

# Sidebar
try:
    lang = st.sidebar.selectbox("Language / Idioma", ["Español", "English"], key="language_selector")
    lang_code = "es" if lang == "Español" else "en"
    t = LANGUAGES[lang_code]

    LOG_FILE = "nom035_log.csv"

    with st.sidebar:
        st.subheader(t["download_log"])
        password_download = st.text_input(t["password_prompt"], type="password", key="download_password")
        if st.button(t["download_log"], key="download_button"):
            if action_lock():
                try:
                    hashed_input = hash_password(password_download, SALT)
                    if hashed_input == CORRECT_PASSWORD_HASH:
                        if os.path.exists(LOG_FILE):
                            with open(LOG_FILE, "rb") as f:
                                csv_bytes = f.read()
                            b64 = base64.b64encode(csv_bytes).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="nom035_log.csv" role="button" aria-label="Download Log CSV">Download Log CSV</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        else:
                            st.warning("No hay datos en el registro.")
                    else:
                        st.error(t["incorrect_password"])
                except Exception as e:
                    logger.error(f"Error in download_log: {str(e)}")
                    st.error(t["file_error"])

        st.subheader(t["refresh_log"])
        password_refresh = st.text_input(t["password_prompt"], type="password", key="refresh_password")
        if st.button(t["refresh_log"], key="refresh_button"):
            if action_lock():
                try:
                    hashed_input = hash_password(password_refresh, SALT)
                    if hashed_input == CORRECT_PASSWORD_HASH:
                        refresh_log()
                        st.success(t["log_refreshed"])
                    else:
                        st.error(t["incorrect_password"])
                except Exception as e:
                    logger.error(f"Error in refresh_log: {str(e)}")
                    st.error(t["file_error"])
except Exception as e:
    logger.error(f"Sidebar rendering failed: {str(e)}")
    st.error(t.get("sidebar_error", "Error loading the sidebar. Try again or contact support."))
    if DEBUG_MODE:
        st.write(f"Debug: {str(e)}")

def calculate_progress() -> float:
    try:
        total_questions = len(GUIDE1_QUESTIONS)
        required_keys = [q["id"] for q in GUIDE1_QUESTIONS]
        if st.session_state.has_trauma and not st.session_state.guide3_complete:
            required_keys += [q["id"] for q in GUIDE2_QUESTIONS] + [q["id"] for q in GUIDE3_QUESTIONS]
            total_questions += len(GUIDE2_QUESTIONS) + len(GUIDE3_QUESTIONS)
        answered_questions = 0
        for key in required_keys:
            if key == "g1_q1":
                nombre = st.session_state.responses.get("g1_q1_nombre", "").strip()
                apellido = st.session_state.responses.get("g1_q1_apellido", "").strip()
                if nombre and apellido:
                    answered_questions += 1
            else:
                response = st.session_state.responses.get(key)
                if response is not None:
                    if isinstance(response, str) and response.strip():
                        answered_questions += 1
                    elif isinstance(response, (int, float)) and response != 0:
                        answered_questions += 1
                    else:
                        answered_questions += 1
        progress = answered_questions / total_questions if total_questions > 0 else 0
        if DEBUG_MODE:
            logger.debug(f"Progress: {answered_questions}/{total_questions} = {progress:.2%}")
        return progress
    except Exception as e:
        logger.error(f"Error in calculate_progress: {str(e)}")
        return 0

def validate_responses(responses: Dict, guide_questions: List, is_guide1: bool = False) -> Dict[str, str]:
    try:
        errors = {}
        if is_guide1:
            for subfield in GUIDE1_QUESTIONS[0]["subfields"]:
                if not subfield.get("optional", False):
                    value = responses.get(subfield["id"], "").strip()
                    if not value:
                        field_label = subfield["label" if lang_code == "es" else "label_en"]
                        errors[subfield["id"]] = t["missing_field"].format(field=field_label)
            if "g1_q2" not in responses or not (18 <= responses["g1_q2"] <= 100):
                errors["g1_q2"] = t["invalid_age"]
            if "g1_q4" in responses and "g1_q2" in responses:
                if not (0 <= responses["g1_q4"] <= responses["g1_q2"]):
                    errors["g1_q4"] = t["invalid_years_worked"]
        required_keys = [q["id"] for q in guide_questions if q["type"] != "text_group"]
        if is_guide1:
            required_keys += [subfield["id"] for q in guide_questions if q.get("type") == "text_group" for subfield in q["subfields"] if not subfield.get("optional", False)]
        for key in required_keys:
            if key not in responses or responses[key] is None or (isinstance(responses[key], str) and not responses[key].strip()):
                question_text = next((q["text" if lang_code == "es" else "text_en"] for q in guide_questions if q["id"] == key), key)
                errors[key] = t["missing_field"].format(field=question_text)
            elif not is_guide1 and responses[key] not in VALID_RESPONSES_GUIDE2_3:
                question_text = next((q["text" if lang_code == "es" else "text_en"] for q in guide_questions if q["id"] == key), key)
                errors[key] = t["missing_field"].format(field=question_text)
        return errors
    except Exception as e:
        logger.error(f"Error in validate_responses: {str(e)}")
        return {}

# Main App
try:
    st.markdown('<div class="container">', unsafe_allow_html=True)
    st.markdown(f'<h1 class="header">{t["title"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="welcome-text">{t["welcome"]}</p>', unsafe_allow_html=True)

    progress = calculate_progress()
    st.progress(progress)
    st.markdown(f'<p class="tooltip">{t["progress"]}: {int(progress * 100)}%</p>', unsafe_allow_html=True)

    VALID_RESPONSES_GUIDE2_3 = [t["always"], t["almost_always"], t["sometimes"], t["almost_never"], t["never"]]

    guide1_class = "guide-section disabled-section" if st.session_state.guide1_complete else "guide-section visible"
    st.markdown(f'<div id="guide1-section" class="{guide1_class}">', unsafe_allow_html=True)
    st.markdown(f'<h2 class="header">{t["guide1"]}</h2>', unsafe_allow_html=True)
    st.markdown(f'<p class="tooltip">{t["tooltip_guide1"]}</p>', unsafe_allow_html=True)

    guide1_groups = [
        ("personal_info", t["personal_info"], GUIDE1_QUESTIONS[:7]),
        ("traumatic_events", t["traumatic_events"], GUIDE1_QUESTIONS[7:13]),
        ("persistent_memories", t["persistent_memories"], GUIDE1_QUESTIONS[13:15]),
        ("avoidance_efforts", t["avoidance_efforts"], GUIDE1_QUESTIONS[15:22]),
        ("affectation", t["affectation"], GUIDE1_QUESTIONS[22:]),
    ]

    if not st.session_state.guide1_complete:
        for group_id, group_label, questions in guide1_groups:
            with st.expander(group_label, expanded=True):
                st.markdown('<div class="card">', unsafe_allow_html=True)
                for q in questions:
                    st.markdown(
                        f'<p class="question" id="question-{q["id"]}" role="heading" aria-label="{q["text" if lang_code == "es" else "text_en"]}">{q["text" if lang_code == "es" else "text_en"]}</p>',
                        unsafe_allow_html=True,
                    )
                    if q["type"] == "text_group":
                        for subfield in q["subfields"]:
                            label = subfield["label" if lang_code == "es" else "label_en"]
                            if subfield.get("optional", False):
                                label += f" {t['optional_field']}"
                            is_invalid = subfield["id"] in st.session_state.validation_errors
                            css_class = "invalid-field" if is_invalid else ""
                            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                            response = st.text_input(
                                label,
                                key=subfield["id"],
                                placeholder=subfield["placeholder" if lang_code == "es" else "placeholder_en"],
                                value=st.session_state.responses.get(subfield["id"], ""),
                                disabled=st.session_state.guide1_complete,
                            )
                            st.session_state.responses[subfield["id"]] = response
                            if is_invalid:
                                st.markdown(
                                    f'<p class="error-message">{st.session_state.validation_errors[subfield["id"]]}</p>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown('</div>', unsafe_allow_html=True)
                    elif q["type"] == "number":
                        is_invalid = q["id"] in st.session_state.validation_errors
                        css_class = "invalid-field" if is_invalid else ""
                        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                        response = st.number_input(
                            "",
                            min_value=0,
                            max_value=100,
                            step=1,
                            key=q["id"],
                            format="%d",
                            label_visibility="collapsed",
                            value=st.session_state.responses.get(q["id"], 0),
                            disabled=st.session_state.guide1_complete,
                        )
                        st.session_state.responses[q["id"]] = response
                        if is_invalid:
                            st.markdown(
                                f'<p class="error-message">{st.session_state.validation_errors[q["id"]]}</p>',
                                unsafe_allow_html=True,
                            )
                        st.markdown('</div>', unsafe_allow_html=True)
                    elif q["type"] == "select":
                        is_invalid = q["id"] in st.session_state.validation_errors
                        css_class = "invalid-field" if is_invalid else ""
                        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                        response = st.selectbox(
                            "",
                            q["options" if lang_code == "es" else "options_en"],
                            key=q["id"],
                            label_visibility="collapsed",
                            index=None,
                            placeholder="Seleccione / Select",
                            disabled=st.session_state.guide1_complete,
                        )
                        st.session_state.responses[q["id"]] = response
                        if is_invalid:
                            st.markdown(
                                f'<p class="error-message">{st.session_state.validation_errors[q["id"]]}</p>',
                                unsafe_allow_html=True,
                            )
                        st.markdown('</div>', unsafe_allow_html=True)
                    elif q["type"] == "yes_no":
                        st.markdown(f'<div role="radiogroup" aria-describedby="question-{q["id"]}">', unsafe_allow_html=True)
                        is_invalid = q["id"] in st.session_state.validation_errors
                        css_class = "invalid-field" if is_invalid else ""
                        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                        response = st.radio(
                            "",
                            [t["yes"], t["no"]],
                            key=q["id"],
                            label_visibility="collapsed",
                            disabled=st.session_state.guide1_complete,
                        )
                        st.session_state.responses[q["id"]] = response
                        if is_invalid:
                            st.markdown(
                                f'<p class="error-message">{st.session_state.validation_errors[q["id"]]}</p>',
                                unsafe_allow_html=True,
                            )
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        if response == t["yes"]:
                            st.session_state.has_trauma = True
                st.markdown('</div>', unsafe_allow_html=True)

        if st.button(t["submit"], key="submit_guide1", disabled=st.session_state.guide1_complete):
            if action_lock():
                st.session_state.validation_errors = validate_responses(st.session_state.responses, GUIDE1_QUESTIONS, is_guide1=True)
                if st.session_state.validation_errors:
                    st.error(t["validation_error"])
                    logger.debug("Validation errors detected, triggering rerun")
                    st.rerun()
                else:
                    st.session_state.validation_errors = {}
                    st.session_state.guide1_complete = True
                    if st.session_state.has_trauma:
                        st.session_state.show_guide2 = True
                        st.markdown('<script>scrollToGuide2();</script>', unsafe_allow_html=True)
                    else:
                        save_responses_to_log()
                    st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)
                    logger.debug("Guide I completed, triggering rerun")
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.guide1_complete and st.session_state.has_trauma and not st.session_state.guide2_complete:
        guide2_class = "guide-section visible" if st.session_state.show_guide2 else "guide-section"
        st.markdown(f'<div id="guide2-section" class="{guide2_class}">', unsafe_allow_html=True)
        st.markdown(f'<h2 class="header">{t["guide2"]}</h2>', unsafe_allow_html=True)
        st.markdown(f'<p class="tooltip">{t["tooltip_guide2"]}</p>', unsafe_allow_html=True)

        for q in GUIDE2_QUESTIONS:
            if q["id"] not in st.session_state.responses:
                st.session_state.responses[q["id"]] = None

        guide2_groups = [
            ("work_conditions", t["work_conditions"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_conditions"]),
            ("workload_pace", t["workload_pace"], [q for q in GUIDE2_QUESTIONS if q["group"] == "workload_pace"]),
            ("control_decision", t["control_decision"], [q for q in GUIDE2_QUESTIONS if q["group"] == "control_decision"]),
            ("work_relationships", t["work_relationships"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_relationships"]),
            ("work_life_balance", t["work_life_balance"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_life_balance"]),
        ]

        for group_id, group_label, questions in guide2_groups:
            with st.expander(group_label, expanded=True):
                st.markdown('<div class="card">', unsafe_allow_html=True)
                for q in questions:
                    st.markdown(
                        f'<div role="radiogroup" aria-describedby="question-{q["id"]}"><p class="question" id="question-{q["id"]}" role="heading" aria-label="{q["text" if lang_code == "es" else "text_en"]}">{q["text" if lang_code == "es" else "text_en"]}</p>',
                        unsafe_allow_html=True,
                    )
                    is_invalid = q["id"] in st.session_state.validation_errors
                    css_class = "invalid-field" if is_invalid else ""
                    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                    response = st.radio(
                        "",
                        VALID_RESPONSES_GUIDE2_3,
                        key=q["id"],
                        label_visibility="collapsed",
                        index=None,
                    )
                    st.session_state.responses[q["id"]] = response
                    if is_invalid:
                        st.markdown(
                            f'<p class="error-message">{st.session_state.validation_errors[q["id"]]}</p>',
                            unsafe_allow_html=True,
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        if st.button(t["submit"], key="submit_guide2"):
            if action_lock():
                st.session_state.validation_errors = validate_responses(st.session_state.responses, GUIDE2_QUESTIONS)
                if st.session_state.validation_errors:
                    st.error(t["validation_error"])
                    logger.debug("Guide II validation errors, triggering rerun")
                    st.rerun()
                else:
                    st.session_state.validation_errors = {}
                    st.session_state.guide2_complete = True
                    st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)
                    logger.debug("Guide II completed, triggering rerun")
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.guide2_complete and st.session_state.has_trauma and not st.session_state.guide3_complete:
        st.markdown('<div id="guide3-section" class="guide-section visible">', unsafe_allow_html=True)
        st.markdown(f'<h2 class="header">{t["guide3"]}</h2>', unsafe_allow_html=True)
        st.markdown(f'<p class="tooltip">{t["tooltip_guide3"]}</p>', unsafe_allow_html=True)

        for q in GUIDE3_QUESTIONS:
            if q["id"] not in st.session_state.responses:
                st.session_state.responses[q["id"]] = None

        st.markdown('<div class="card">', unsafe_allow_html=True)
        for q in GUIDE3_QUESTIONS:
            st.markdown(
                f'<div role="radiogroup" aria-describedby="question-{q["id"]}"><p class="question" id="question-{q["id"]}" role="heading" aria-label="{q["text" if lang_code == "es" else "text_en"]}">{q["text" if lang_code == "es" else "text_en"]}</p>',
                unsafe_allow_html=True,
            )
            is_invalid = q["id"] in st.session_state.validation_errors
            css_class = "invalid-field" if is_invalid else ""
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            response = st.radio(
                "",
                VALID_RESPONSES_GUIDE2_3,
                key=q["id"],
                label_visibility="collapsed",
                index=None,
            )
            st.session_state.responses[q["id"]] = response
            if is_invalid:
                st.markdown(
                    f'<p class="error-message">{st.session_state.validation_errors[q["id"]]}</p>',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button(t["submit"], key="submit_guide3"):
            if action_lock():
                st.session_state.validation_errors = validate_responses(st.session_state.responses, GUIDE3_QUESTIONS)
                if st.session_state.validation_errors:
                    st.error(t["validation_error"])
                    logger.debug("Guide III validation errors, triggering rerun")
                    st.rerun()
                else:
                    st.session_state.validation_errors = {}
                    st.session_state.guide3_complete = True
                    save_responses_to_log()
                    st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)
                    logger.debug("Guide III completed, triggering rerun")
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
except Exception as e:
    logger.error(f"Main app rendering failed: {str(e)}")
    if "has no attribute 'experimental_rerun'" in str(e) or "has no attribute 'rerun'" in str(e):
        st.error(t.get("version_error", "Streamlit version incompatibility. Please ensure Streamlit version >= 1.12.0 is installed."))
    else:
        st.error("Error loading the survey. Try again or contact support.")
    if DEBUG_MODE:
        st.write(f"Debug: {str(e)}")
