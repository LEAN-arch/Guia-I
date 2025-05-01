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

# Language translations
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
    },
    "en": {
        "title": "NOM-035-STPS-2018 Survey",
        "welcome": "Welcome to the NOM-035 survey. Please answer all questions honestly to help us improve your work environment.",
        "guide1": "Guide I: Severe Traumatic Events",
        "guide2": "Guide II: Psychosocial Risk Factors",
        "guide3": "Guide III: Favorable Organizational Environment",
        "submit": "Submit",
        "previous": "Previous",
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
        "file_not_found": "No data in the log.",
        "unexpected_error": "An unexpected error occurred: {error}. Please try again or contact support.",
        "debug_prompt": "For more details, enable DEBUG_MODE=True in the .env file and restart the application."
    }
}

# Question Definitions
GUIDE1_QUESTIONS = [
    {"id": "g1_q1", "text": "¿Cuál es su nombre?", "text_en": "What is your name?", "type": "text_group", "subfields": [
        {"id": "g1_q1_nombre", "label": "Nombre", "label_en": "First Name", "placeholder": "Ej. Juan", "placeholder_en": "E.g., John"},
        {"id": "g1_q1_apellido", "label": "Apellido", "label_en": "Last Name", "placeholder": "Ej. Pérez", "placeholder_en": "E.g., Smith"},
        {"id": "g1_q1_segundo_apellido", "label": "Segundo apellido", "label_en": "Second Last Name", "optional": True, "placeholder": "Ej. García", "placeholder_en": "E.g., Garcia"}
    ], "group": "personal_info"},
    {"id": "g1_q2", "text": "¿Qué edad tienes? (Solo incluye el número de años, ej. 21)", "text_en": "How old are you? (Only include the number of years, e.g., 21)", "type": "number", "group": "personal_info"},
    {"id": "g1_q3", "text": "¿Cuál es tu género?", "text_en": "What is your gender?", "type": "select", "options": ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"], "options_en": ["Female", "Male", "LGTBTTTIQ+", "Other"], "group": "personal_info"},
    {"id": "g1_q4", "text": "¿Cuántos años llevas trabajando para esta empresa? (Solo incluye el número de años, ej. 3)", "text_en": "How many years have you been working for this company? (Only include the number of years, e.g., 3)", "type": "number", "group": "personal_info"},
    {"id": "g1_q5", "text": "¿En qué departamento labora?", "text_en": "In which department do you work?", "type": "select", "options": ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"], "options_en": ["Maintenance", "Quality Control", "Manufacturing", "Sales", "Production", "Human Resources", "Sales and Marketing", "Accounting and Finance", "Administration"], "group": "personal_info"},
    {"id": "g1_q6", "text": "¿Cuál es su función?", "text_en": "What is your role?", "type": "select", "options": ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"], "options_en": ["Operator", "Technician", "Engineer", "Analyst", "Supervisor", "Manager", "Director"], "group": "personal_info"},
    {"id": "g1_q7", "text": "¿Cuál es su lugar de trabajo? (Seleccione el lugar donde pase más tiempo)", "text_en": "What is your workplace? (Select the place where you spend most of your time)", "type": "select", "options": ["Planta 1", "Planta 2", "Planta 3"], "options_en": ["Plant 1", "Plant 2", "Plant 3"], "group": "personal_info"},
    {"id": "g1_q8", "text": "¿Ha presenciado o sufrido un accidente grave en el trabajo?", "text_en": "Have you witnessed or suffered a serious accident at work?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q9", "text": "¿Ha presenciado o sufrido un asalto en el trabajo?", "text_en": "Have you witnessed or suffered an assault at work?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q10", "text": "¿Ha presenciado o sufrido actos violentos en el trabajo?", "text_en": "Have you witnessed or suffered violent acts at work?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q11", "text": "¿Ha presenciado o sufrido un secuestro en el trabajo?", "text_en": "Have you witnessed or suffered a kidnapping at work?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q12", "text": "¿Ha presenciado o sufrido amenazas en el trabajo?", "text_en": "Have you witnessed or suffered threats at work?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q13", "text": "¿Ha experimentado situaciones de riesgo para su vida o salud en el trabajo?", "text_en": "Have you experienced situations that put your life or health at risk at work?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q14", "text": "¿Ha tenido recuerdos recurrentes que le causan malestar?", "text_en": "Have you had recurrent memories causing discomfort?", "type": "yes_no", "group": "persistent_memories"},
    {"id": "g1_q15", "text": "¿Ha tenido sueños recurrentes que le causan malestar?", "text_en": "Have you had recurrent dreams causing discomfort?", "type": "yes_no", "group": "persistent_memories"},
    {"id": "g1_q16", "text": "¿Evita sentimientos o situaciones que le recuerdan el evento?", "text_en": "Do you avoid feelings or situations that remind you of the event?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q17", "text": "¿Evita actividades o personas que le recuerdan el evento?", "text_en": "Do you avoid activities or people that remind you of the event?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q18", "text": "¿Tiene dificultad para recordar partes del evento?", "text_en": "Do you have difficulty remembering parts of the event?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q19", "text": "¿Ha perdido interés en sus actividades cotidianas?", "text_en": "Have you lost interest in daily activities?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q20", "text": "¿Se siente distante de los demás?", "text_en": "Do you feel distant from others?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q21", "text": "¿Tiene dificultad para expresar sus sentimientos?", "text_en": "Do you have difficulty expressing feelings?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q22", "text": "¿Siente que su vida será más corta?", "text_en": "Do you feel your life will be shorter?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q23", "text": "¿Tiene problemas para dormir?", "text_en": "Do you have trouble sleeping?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q24", "text": "¿Ha estado más irritable de lo usual?", "text_en": "Have you been more irritable than usual?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q25", "text": "¿Tiene dificultad para concentrarse?", "text_en": "Do you have difficulty concentrating?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q26", "text": "¿Se siente nervioso o en alerta constante?", "text_en": "Do you feel nervous or constantly on alert?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q27", "text": "¿Se sobresalta fácilmente?", "text_en": "Do you get startled easily?", "type": "yes_no", "group": "affectation"}
]

GUIDE2_QUESTIONS = [
    {"id": "g2_q1", "text": "Mi trabajo requiere gran esfuerzo físico.", "text_en": "My job requires significant physical effort.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q2", "text": "Me siento expuesto(a) a riesgos físicos en mi trabajo.", "text_en": "I feel exposed to physical risks at work.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q3", "text": "Manejo herramientas que representan riesgo.", "text_en": "I handle tools that pose a risk.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q4", "text": "Trabajo en un lugar con ruidos fuertes.", "text_en": "I work in a place with loud noises.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q5", "text": "Trabajo en un lugar con temperaturas extremas.", "text_en": "I work in a place with extreme temperatures.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q6", "text": "Estoy expuesto(a) a materiales peligrosos.", "text_en": "I am exposed to hazardous materials.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q7", "text": "Mi trabajo requiere estar de pie mucho tiempo.", "text_en": "My job requires standing for long periods.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q8", "text": "Realizo movimientos repetitivos en mi trabajo.", "text_en": "I perform repetitive movements at work.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q9", "text": "Mi trabajo requiere posturas incómodas.", "text_en": "My job requires uncomfortable postures.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q10", "text": "Tengo que mover objetos pesados.", "text_en": "I have to move heavy objects.", "type": "likert", "group": "work_conditions"},
    {"id": "g2_q11", "text": "Puedo tomar pausas cuando las necesito.", "text_en": "I can take breaks when needed.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q12", "text": "Puedo decidir la cantidad de trabajo que realizo.", "text_en": "I can decide the amount of work I do.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q13", "text": "Tengo libertad para decidir cómo realizar mi trabajo.", "text_en": "I have freedom to decide how to do my job.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q14", "text": "Mi trabajo requiere decisiones difíciles.", "text_en": "My job requires difficult decisions.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q15", "text": "Tengo que atender varias tareas a la vez.", "text_en": "I handle multiple tasks at once.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q16", "text": "Mi trabajo requiere alta concentración.", "text_en": "My job requires high concentration.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q17", "text": "La cantidad de trabajo es excesiva.", "text_en": "The amount of work is excessive.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q18", "text": "Trabajo horas extras con frecuencia.", "text_en": "I work overtime frequently.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q19", "text": "Debo estar disponible fuera de mi horario.", "text_en": "I must be available outside working hours.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q20", "text": "Mi ritmo de trabajo es muy acelerado.", "text_en": "My work pace is very fast.", "type": "likert", "group": "workload_pace"},
    {"id": "g2_q21", "text": "Mi jefe me presiona para cumplir objetivos.", "text_en": "My boss pressures me to meet goals.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q22", "text": "Recibo órdenes contradictorias.", "text_en": "I receive contradictory orders.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q23", "text": "Mi jefe me da instrucciones claras.", "text_en": "My boss gives clear instructions.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q24", "text": "Mi jefe me apoya en problemas laborales.", "text_en": "My boss supports me with work problems.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q25", "text": "Mi jefe confía en mi capacidad.", "text_en": "My boss trusts my ability.", "type": "likert", "group": "control_decision"},
    {"id": "g2_q26", "text": "Mi jefe me trata con respeto.", "text_en": "My boss treats me with respect.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q27", "text": "Me siento valorado(a) por mis compañeros.", "text_en": "I feel valued by my colleagues.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q28", "text": "Tengo buena comunicación con mis compañeros.", "text_en": "I have good communication with coworkers.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q29", "text": "Hay un ambiente de colaboración.", "text_en": "There is a collaborative environment.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q30", "text": "Recibo críticas negativas con frecuencia.", "text_en": "I receive negative criticism frequently.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q31", "text": "Mis compañeros me excluyen.", "text_en": "My colleagues exclude me.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q32", "text": "He sido víctima de burlas en el trabajo.", "text_en": "I have been a victim of teasing at work.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q33", "text": "He sido testigo de discriminación.", "text_en": "I have witnessed discrimination.", "type": "likert", "group": "work_relationships"},
    {"id": "g2_q34", "text": "Mi trabajo interfiere con mi familia.", "text_en": "My job interferes with family responsibilities.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q35", "text": "Mi trabajo afecta mi vida personal.", "text_en": "My job negatively affects my personal life.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q36", "text": "Tengo tiempo para actividades personales.", "text_en": "I have time for personal activities.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q37", "text": "Mi horario de trabajo es flexible.", "text_en": "My work schedule is flexible.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q38", "text": "Recibo capacitación para mi trabajo.", "text_en": "I receive training for my job.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q39", "text": "Tengo oportunidades de crecimiento.", "text_en": "I have opportunities for growth.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q40", "text": "Siento que mi trabajo es estable.", "text_en": "I feel my job is stable.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q41", "text": "Mi salario es adecuado.", "text_en": "My salary is adequate.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q42", "text": "Recibo beneficios adicionales.", "text_en": "I receive additional benefits.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q43", "text": "Mi trabajo es importante para la empresa.", "text_en": "My job is important to the company.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q44", "text": "Me siento motivado(a) en mi trabajo.", "text_en": "I feel motivated at work.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q45", "text": "Mi trabajo me permite desarrollar habilidades.", "text_en": "My job allows skill development.", "type": "likert", "group": "work_life_balance"},
    {"id": "g2_q46", "text": "Mi trabajo tiene un propósito claro.", "text_en": "My job has a clear purpose.", "type": "likert", "group": "work_life_balance"}
]

GUIDE3_QUESTIONS = [
    {"id": "g3_q1", "text": "Me informan claramente mis responsabilidades.", "text_en": "I am clearly informed about my responsibilities.", "type": "likert"},
    {"id": "g3_q2", "text": "Recibo instrucciones claras para mi trabajo.", "text_en": "I receive clear instructions for my job.", "type": "likert"},
    {"id": "g3_q3", "text": "Mi jefe comunica lo que espera de mí.", "text_en": "My boss communicates expectations clearly.", "type": "likert"},
    {"id": "g3_q4", "text": "Tengo los recursos necesarios para mi trabajo.", "text_en": "I have the necessary resources for my job.", "type": "likert"},
    {"id": "g3_q5", "text": "Tengo acceso a herramientas necesarias.", "text_en": "I have access to necessary tools.", "type": "likert"},
    {"id": "g3_q6", "text": "Recibo retroalimentación sobre mi desempeño.", "text_en": "I receive feedback on my performance.", "type": "likert"},
    {"id": "g3_q7", "text": "Mi jefe reconoce mi trabajo bien hecho.", "text_en": "My boss acknowledges my good work.", "type": "likert"},
    {"id": "g3_q8", "text": "Me siento valorado(a) por mis contribuciones.", "text_en": "I feel valued for my contributions.", "type": "likert"},
    {"id": "g3_q9", "text": "Recibo reconocimiento por mis logros.", "text_en": "I receive recognition for my achievements.", "type": "likert"},
    {"id": "g3_q10", "text": "Se promueve la igualdad de oportunidades.", "text_en": "Equal opportunities are promoted.", "type": "likert"},
    {"id": "g3_q11", "text": "Siento que se me trata con justicia.", "text_en": "I feel treated fairly.", "type": "likert"},
    {"id": "g3_q12", "text": "Mis opiniones son tomadas en cuenta.", "text_en": "My opinions are considered.", "type": "likert"},
    {"id": "g3_q13", "text": "Puedo expresar mis ideas.", "text_en": "I can express my ideas.", "type": "likert"},
    {"id": "g3_q14", "text": "Se fomenta la participación en decisiones.", "text_en": "Participation in decisions is encouraged.", "type": "likert"},
    {"id": "g3_q15", "text": "Siento que pertenezco a un equipo.", "text_en": "I feel part of a team.", "type": "likert"},
    {"id": "g3_q16", "text": "Existe respeto mutuo.", "text_en": "There is mutual respect.", "type": "likert"},
    {"id": "g3_q17", "text": "Mis compañeros me tratan con cortesía.", "text_en": "My colleagues treat me with courtesy.", "type": "likert"},
    {"id": "g3_q18", "text": "Se promueve la colaboración entre compañeros.", "text_en": "Collaboration is promoted.", "type": "likert"},
    {"id": "g3_q19", "text": "Hay un buen ambiente laboral.", "text_en": "There is a good work environment.", "type": "likert"},
    {"id": "g3_q20", "text": "Se fomenta la confianza entre empleados.", "text_en": "Trust among employees is fostered.", "type": "likert"},
    {"id": "g3_q21", "text": "La empresa promueve un mejor clima laboral.", "text_en": "The company promotes a better work environment.", "type": "likert"},
    {"id": "g3_q22", "text": "Recibo apoyo para balancear mi vida laboral.", "text_en": "I receive support to balance work and life.", "type": "likert"},
    {"id": "g3_q23", "text": "La empresa ofrece beneficios para mi bienestar.", "text_en": "The company offers benefits for my well-being.", "type": "likert"},
    {"id": "g3_q24", "text": "La empresa se preocupa por mi salud.", "text_en": "The company cares about my health.", "type": "likert"},
    {"id": "g3_q25", "text": "Se promueve el respeto a la diversidad.", "text_en": "Respect for diversity is promoted.", "type": "likert"},
    {"id": "g3_q26", "text": "La empresa valora mi trabajo.", "text_en": "The company values my work.", "type": "likert"}
]

# Cache question data
@functools.lru_cache(maxsize=1)
def get_all_questions() -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Cache question data to improve performance."""
    return GUIDE1_QUESTIONS, GUIDE2_QUESTIONS, GUIDE3_QUESTIONS

# Valid responses for Guides 2 and 3
def get_valid_responses(lang_code: str) -> List[str]:
    """Return valid response options for Guides 2 and 3 based on language."""
    return [
        LANGUAGES[lang_code]["always"],
        LANGUAGES[lang_code]["almost_always"],
        LANGUAGES[lang_code]["sometimes"],
        LANGUAGES[lang_code]["almost_never"],
        LANGUAGES[lang_code]["never"]
    ]

# Utility Functions
def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using SHA-256."""
    try:
        salted_password = password + salt
        return hashlib.sha256(salted_password.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

CORRECT_PASSWORD_HASH = hash_password(PASSWORD, SALT)

def initialize_log() -> None:
    """Initialize log file with headers if it doesn't exist."""
    for _ in range(3):  # Retry up to 3 times
        try:
            if not os.path.exists(LOG_FILE):
                headers = (
                    ["timestamp"] +
                    [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" for subfield in q["subfields"]] +
                    [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"] +
                    [q["id"] for q in GUIDE2_QUESTIONS] +
                    [q["id"] for q in GUIDE3_QUESTIONS]
                )
                pd.DataFrame(columns=headers).to_csv(LOG_FILE, index=False)
                logger.info("Log file initialized successfully.")
            return
        except (PermissionError, IOError) as e:
            logger.warning(f"Retrying log initialization due to: {str(e)}")
            time.sleep(1)
    logger.error("Failed to initialize log file after retries.")
    st.warning("Could not initialize log file. Proceeding without logging.")

def save_responses_to_log(responses: Dict) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Save responses to log file with timestamp."""
    for _ in range(3):  # Retry up to 3 times
        try:
            initialize_log()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            responses_copy = responses.copy()
            responses_copy["timestamp"] = timestamp
            df = pd.DataFrame([responses_copy])
            try:
                existing_df = pd.read_csv(LOG_FILE)
            except pd.errors.EmptyDataError:
                existing_df = pd.DataFrame(columns=df.columns)
            updated_df = pd.concat([existing_df, df], ignore_index=True)
            updated_df.to_csv(LOG_FILE, index=False)
            logger.info(f"Responses saved to log with timestamp {timestamp}.")
            return df, timestamp
        except (PermissionError, IOError) as e:
            logger.warning(f"Retrying log save due to: {str(e)}")
            time.sleep(1)
    logger.error("Failed to save responses to log after retries.")
    st.warning("Could not save responses to log. Continuing without saving.")
    return None, None

def refresh_log() -> bool:
    """Refresh log file by recreating it."""
    for _ in range(3):  # Retry up to 3 times
        try:
            initialize_log()
            logger.info("Log file refreshed successfully.")
            return True
        except (PermissionError, IOError) as e:
            logger.warning(f"Retrying log refresh due to: {str(e)}")
            time.sleep(1)
    logger.error("Failed to refresh log after retries.")
    return False

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
                "language_selector": "Español",
                "initialized": True
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
            update_trauma_status(st.session_state.responses, LANGUAGES["es" if st.session_state.language_selector == "Español" else "en"])
            logger.debug("Session state initialized successfully.")
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
def render_sidebar(lang_code: str) -> None:
    """Render the sidebar with language selector and log management."""
    t = LANGUAGES[lang_code]
    try:
        with st.sidebar:
            try:
                st.markdown(f'<h3 class="subheader">Opciones</h3>', unsafe_allow_html=True)
                logger.debug("Rendering language selector")
                
                def on_language_change():
                    try:
                        new_lang = st.session_state.get("language_selector", "Español")
                        old_lang_code = "es" if new_lang != "Español" else "en"
                        new_lang_code = "es" if new_lang == "Español" else "en"
                        old_t = LANGUAGES[old_lang_code]
                        new_t = LANGUAGES[new_lang_code]
                        
                        # Map responses to new language
                        for q in GUIDE1_QUESTIONS:
                            if q["type"] == "yes_no":
                                current_response = st.session_state.responses.get(q["id"])
                                if current_response == old_t["yes"]:
                                    st.session_state.responses[q["id"]] = new_t["yes"]
                                elif current_response == old_t["no"]:
                                    st.session_state.responses[q["id"]] = new_t["no"]
                        for q in GUIDE2_QUESTIONS + GUIDE3_QUESTIONS:
                            old_responses = get_valid_responses(old_lang_code)
                            new_responses = get_valid_responses(new_lang_code)
                            current_response = st.session_state.responses.get(q["id"])
                            if current_response in old_responses:
                                idx = old_responses.index(current_response)
                                st.session_state.responses[q["id"]] = new_responses[idx]
                        
                        update_trauma_status(st.session_state.responses, new_t)
                        logger.debug(f"Language changed to {new_lang}")
                    except Exception as e:
                        logger.error(f"Error in on_language_change: {str(e)}")
                        st.error(f"{t['unexpected_error'].format(error=str(e))} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Language change failed"))

                st.selectbox(
                    "Language / Idioma",
                    ["Español", "English"],
                    key="language_selector",
                    on_change=on_language_change,
                    label="Select Language"
                )
            except Exception as e:
                logger.error(f"Failed to render language selector: {str(e)}")
                st.warning("Language selector failed to load.")

            try:
                st.markdown(f'<h3 class="subheader">{t["download_log"]}</h3>', unsafe_allow_html=True)
                password_download = st.text_input(
                    t["password_prompt"],
                    type="password",
                    key="download_password",
                    label="Download Password"
                )
                if st.button(t["download_log"], key="download_button"):
                    if action_lock():
                        hashed_input = hash_password(password_download, SALT)
                        if hashed_input == CORRECT_PASSWORD_HASH:
                            try:
                                if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
                                    st.warning(t["file_not_found"])
                                else:
                                    with open(LOG_FILE, "rb") as f:
                                        csv_bytes = f.read()
                                    b64 = base64.b64encode(csv_bytes).decode()
                                    href = f'<a href="data:file/csv;base64,{b64}" download="nom035_log.csv" role="button" aria-label="Download Log CSV">Download Log CSV</a>'
                                    st.markdown(href, unsafe_allow_html=True)
                            except (FileNotFoundError, IOError) as e:
                                logger.error(f"Failed to download log: {str(e)}")
                                st.warning(t["file_not_found"])
                        else:
                            st.error(t["incorrect_password"])
            except Exception as e:
                logger.error(f"Failed to render download log section: {str(e)}")
                st.warning("Download log section failed to load.")

            try:
                st.markdown(f'<h3 class="subheader">{t["refresh_log"]}</h3>', unsafe_allow_html=True)
                password_refresh = st.text_input(
                    t["password_prompt"],
                    type="password",
                    key="refresh_password",
                    label="Refresh Password"
                )
                if st.button(t["refresh_log"], key="refresh_button"):
                    if action_lock():
                        hashed_input = hash_password(password_refresh, SALT)
                        if hashed_input == CORRECT_PASSWORD_HASH:
                            if refresh_log():
                                st.success(t["log_refreshed"])
                            else:
                                st.error("Failed to refresh log.")
                        else:
                            st.error(t["incorrect_password"])
            except Exception as e:
                logger.error(f"Failed to render refresh log section: {str(e)}")
                st.warning("Refresh log section failed to load.")
    except Exception as e:
        logger.error(f"Error rendering sidebar: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error=str(e))} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Sidebar rendering failed"))

def action_lock() -> bool:
    """Prevent rapid button clicks with a 1-second debounce."""
    try:
        current_time = time.time()
        if current_time - st.session_state.last_action_time < 1:
            logger.debug("Action lock triggered: Too frequent clicks.")
            st.warning("Please wait, processing...")
            return False
        st.session_state.last_action_time = current_time
        logger.debug("Action lock passed.")
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

def validate_responses(responses: Dict, guide_questions: List, guide_id: str, is_guide1: bool = False, lang_code: str = "es") -> Dict[str, str]:
    """Validate survey responses and return field-specific errors."""
    try:
        t = LANGUAGES[lang_code]
        errors = {}
        
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
                                logger.debug(f"Validation failed for {subfield['id']}: Value='{value}'")
        
            # Validate age
            age = responses.get("g1_q2", 0)
            if not isinstance(age, (int, float)) or not (18 <= age <= 100):
                errors["g1_q2"] = t["invalid_age"]
                logger.debug(f"Validation failed for g1_q2: Value='{age}'")
        
            # Validate years worked
            years_worked = responses.get("g1_q4", 0)
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
                        valid_responses = get_valid_responses(lang_code)
                    else:  # select
                        valid_responses = q["options" if lang_code == "es" else "options_en"]
                except KeyError as e:
                    logger.error(f"Missing key {str(e)} for question {key}")
                    errors[key] = t["unexpected_error"].format(error=f"Invalid question configuration for {key}")
                    continue
                
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors[key] = t["missing_field"].format(field=q["text" if lang_code == "es" else "text_en"])
                    logger.debug(f"Validation failed for {key}: Value='{value}'")
                elif value not in valid_responses:
                    errors[key] = t["missing_field"].format(field=q["text" if lang_code == "es" else "text_en"])
                    logger.debug(f"Validation failed for {key}: Invalid response='{value}'")
        
        st.session_state.validation_errors[guide_id] = errors
        logger.debug(f"Validation completed for {guide_id}: {len(errors)} errors found")
        return errors
    except Exception as e:
        logger.error(f"Error in validate_responses: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error=str(e))} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Validation failed"))
        return {}

def render_question(q: Dict, lang_code: str, t: Dict, guide_id: str) -> None:
    """Render a single question based on its type."""
    try:
        question_text = q["text" if lang_code == "es" else "text_en"]
        is_invalid = q["id"] in st.session_state.validation_errors[guide_id]
        st.markdown(
            f'<div role="radiogroup" aria-describedby="question-{q["id"]}" class="radio-group">'
            f'<p class="question" id="question-{q["id"]}" role="heading" aria-label="{question_text}">{question_text}</p>',
            unsafe_allow_html=True
        )

        if q["type"] == "text_group":
            for subfield in q["subfields"]:
                label = subfield["label" if lang_code == "es" else "label_en"]
                if subfield.get("optional", False):
                    label += f" {t['optional_field']}"
                is_subfield_invalid = subfield["id"] in st.session_state.validation_errors[guide_id]
                response = st.text_input(
                    label,
                    key=subfield["id"],
                    placeholder=subfield["placeholder" if lang_code == "es" else "placeholder_en"],
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
                value=int(st.session_state.responses.get(q["id"], 0)),
                disabled=st.session_state.get(f"{guide_id}_complete", False)
            )
            st.session_state.responses[q["id"]] = response
            if is_invalid:
                st.markdown(f'<p class="error-message">{st.session_state.validation_errors[guide_id][q["id"]]}</p>', unsafe_allow_html=True)
        elif q["type"] == "select":
            options = q["options" if lang_code == "es" else "options_en"]
            response = st.selectbox(
                question_text,
                options,
                key=q["id"],
                label_visibility="collapsed",
                index=options.index(st.session_state.responses.get(q["id"])) if st.session_state.responses.get(q["id"]) in options else None,
                placeholder="Seleccione / Select",
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
                get_valid_responses(lang_code),
                key=q["id"],
                label_visibility="collapsed",
                index=get_valid_responses(lang_code).index(st.session_state.responses.get(q["id"])) if st.session_state.responses.get(q["id"]) in get_valid_responses(lang_code) else None,
                disabled=st.session_state.get(f"{guide_id}_complete", False)
            )
            st.session_state.responses[q["id"]] = response
            if is_invalid:
                st.markdown(f'<p class="error-message">{st.session_state.validation_errors[guide_id][q["id"]]}</p>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error rendering question {q['id']}: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error=str(e))} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Question rendering failed"))

# Main App
def main():
    try:
        initialize_session_state()
        lang = st.session_state.language_selector
        lang_code = "es" if lang == "Español" else "en"
        t = LANGUAGES[lang_code]

        render_sidebar(lang_code)

        st.markdown('<div class="container">', unsafe_allow_html=True)
        st.markdown(f'<h1 class="header">{t["title"]}</h1>', unsafe_allow_html=True)
        st.write(t["welcome"])

        progress = calculate_progress()
        st.progress(progress)
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
                        render_question(q, lang_code, t, "guide1")
                    st.markdown('</div>', unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])
            with col2:
                if st.button(t["submit"], key="submit_guide1"):
                    if action_lock():
                        errors = validate_responses(st.session_state.responses, GUIDE1_QUESTIONS, "guide1", is_guide1=True, lang_code=lang_code)
                        if errors:
                            for error in errors.values():
                                st.error(error)
                        else:
                            st.session_state.guide1_complete = True
                            if not st.session_state.has_trauma:
                                save_responses_to_log(st.session_state.responses)
                            st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)

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
                        render_question(q, lang_code, t, "guide2")
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
                        errors = validate_responses(st.session_state.responses, GUIDE2_QUESTIONS, "guide2", lang_code=lang_code)
                        if errors:
                            for error in errors.values():
                                st.error(error)
                        else:
                            st.session_state.guide2_complete = True
                            st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)

        # Guide III
        elif st.session_state.guide2_complete and st.session_state.has_trauma and not st.session_state.guide3_complete:
            st.markdown(f'<h2 class="header">{t["guide3"]}</h2>', unsafe_allow_html=True)
            st.markdown(f'<p class="tooltip">{t["tooltip_guide3"]}</p>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            for q in GUIDE3_QUESTIONS:
                render_question(q, lang_code, t, "guide3")
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
                        errors = validate_responses(st.session_state.responses, GUIDE3_QUESTIONS, "guide3", lang_code=lang_code)
                        if errors:
                            for error in errors.values():
                                st.error(error)
                        else:
                            st.session_state.guide3_complete = True
                            save_responses_to_log(st.session_state.responses)
                            st.markdown(f'<p class="success-message">{t["completed"]}</p>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Unexpected error in main: {str(e)}")
        st.error(f"{t['unexpected_error'].format(error=str(e))} {t['debug_prompt']}" if DEBUG_MODE else t["unexpected_error"].format(error="Application failed to load"))

if __name__ == "__main__":
    main()
