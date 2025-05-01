import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import base64
import secrets
import os
import time
import logging

# Configure logging (for debugging, disabled in production)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
DEBUG_MODE = False  # Set to True to enable debug output

# Load environment variables for security
from dotenv import load_dotenv
load_dotenv()
PASSWORD = os.getenv("SURVEY_PASSWORD", "securepassword123")  # Fallback for testing
SALT = os.getenv("SURVEY_SALT", secrets.token_hex(16))

# Language selector and translations
LANGUAGES = {
    "es": {
        "title": "Encuesta NOM-035-STPS-2018",
        "welcome": "Bienvenido a la encuesta NOM-035. Responda todas las preguntas con honestidad.",
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
        "missing_field": "El campo '{field}' está incompleto o no válido."
    },
    "en": {
        "title": "NOM-035-STPS-2018 Survey",
        "welcome": "Welcome to the NOM-035 survey. Please answer all questions honestly.",
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
        "missing_field": "The field '{field}' is incomplete or invalid."
    }
}

# Guía I Questions
GUIDE1_QUESTIONS = [
    {"id": "g1_q1", "text": "¿Cuál es su nombre?", "text_en": "What is your name?", "type": "text_group", "subfields": [
        {"id": "g1_q1_nombre", "label": "Nombre", "label_en": "First Name"},
        {"id": "g1_q1_apellido", "label": "Apellido", "label_en": "Last Name"},
        {"id": "g1_q1_segundo_apellido", "label": "Segundo apellido", "label_en": "Second Last Name"}
    ], "group": "personal_info"},
    {"id": "g1_q2", "text": "¿Qué edad tienes? (Solo incluye el número de años e.g. 21)", "text_en": "How old are you? (Only include the number of years, e.g., 21)", "type": "number", "group": "personal_info"},
    {"id": "g1_q3", "text": "¿Cuál es tu género?", "text_en": "What is your gender?", "type": "select", "options": ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"], "options_en": ["Female", "Male", "LGTBTTTIQ+", "Other"], "group": "personal_info"},
    {"id": "g1_q4", "text": "¿Cuántos años llevas trabajando para esta empresa? (Solo incluye el número de años e.g. 3)", "text_en": "How many years have you been working for this company? (Only include the number of years, e.g., 3)", "type": "number", "group": "personal_info"},
    {"id": "g1_q5", "text": "¿En qué departamento labora? ¿De qué departamento es parte?", "text_en": "In which department do you work? Which department are you part of?", "type": "select", "options": ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"], "options_en": ["Maintenance", "Quality Control", "Manufacturing", "Sales", "Production", "Human Resources", "Sales and Marketing", "Accounting and Finance", "Administration"], "group": "personal_info"},
    {"id": "g1_q6", "text": "¿Cuál es su función?", "text_en": "What is your role?", "type": "select", "options": ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"], "options_en": ["Operator", "Technician", "Engineer", "Analyst", "Supervisor", "Manager", "Director"], "group": "personal_info"},
    {"id": "g1_q7", "text": "¿Cuál es su lugar de trabajo? ¿Dónde se encuentra su lugar de trabajo? (Seleccione el lugar donde pase mayormente su tiempo)", "text_en": "What is your workplace? Where is your workplace located? (Select the place where you spend most of your time)", "type": "select", "options": ["Planta 1", "Planta 2", "Planta 3"], "options_en": ["Plant 1", "Plant 2", "Plant 3"], "group": "personal_info"},
    {"id": "g1_q8", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo un accidente que tenga como consecuencia la muerte, la pérdida de un miembro o una lesión grave?", "text_en": "Have you ever witnessed or suffered, during or due to work, an accident resulting in death, loss of a limb, or a serious injury?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q9", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo un asalto?", "text_en": "Have you ever witnessed or suffered, during or due to work, an assault?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q10", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo actos violentos que derivaron en lesiones graves?", "text_en": "Have you ever witnessed or suffered, during or due to work, violent acts that resulted in serious injuries?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q11", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo un secuestro?", "text_en": "Have you ever witnessed or suffered, during or due to work, a kidnapping?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q12", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo amenazas?", "text_en": "Have you ever witnessed or suffered, during or due to work, threats?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q13", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo cualquier otra situación que ponga en riesgo su vida o salud, y/o la de otras personas?", "text_en": "Have you ever witnessed or suffered, during or due to work, any other situation that puts your life or health, and/or that of others, at risk?", "type": "yes_no", "group": "traumatic_events"},
    {"id": "g1_q14", "text": "¿Ha tenido recuerdos recurrentes sobre el acontecimiento que le provocan malestar?", "text_en": "Have you had recurrent memories of the event that cause you discomfort?", "type": "yes_no", "group": "persistent_memories"},
    {"id": "g1_q15", "text": "¿Ha tenido sueños de carácter recurrente sobre el acontecimiento, que le producen malestar?", "text_en": "Have you had recurrent dreams about the event that cause you discomfort?", "type": "yes_no", "group": "persistent_memories"},
    {"id": "g1_q16", "text": "¿Se ha esforzado por evitar todo tipo de sentimientos, conversaciones o situaciones que le puedan recordar el acontecimiento?", "text_en": "Have you made an effort to avoid all kinds of feelings, conversations, or situations that might remind you of the event?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q17", "text": "¿Se ha esforzado por evitar todo tipo de actividades, lugares o personas que motivan recuerdos del acontecimiento?", "text_en": "Have you made an effort to avoid all kinds of activities, places, or people that trigger memories of the event?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q18", "text": "¿Ha tenido dificultad para recordar alguna parte importante del evento?", "text_en": "Have you had difficulty remembering some important part of the event?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q19", "text": "¿Ha disminuido su interés en sus actividades cotidianas?", "text_en": "Has your interest in your daily activities decreased?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q20", "text": "¿Se ha sentido usted alejado o distante de los demás?", "text_en": "Have you felt distant or detached from others?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q21", "text": "¿Ha notado que tiene dificultad para expresar sus sentimientos?", "text_en": "Have you noticed difficulty expressing your feelings?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q22", "text": "¿Ha tenido la impresión de que su vida se va a acortar, que va a morir antes que otras personas o que tiene un futuro limitado?", "text_en": "Have you had the impression that your life will be shortened, that you will die before others, or that you have a limited future?", "type": "yes_no", "group": "avoidance_efforts"},
    {"id": "g1_q23", "text": "¿Ha tenido usted dificultades o problemas para dormir?", "text_en": "Have you had difficulties or problems sleeping?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q24", "text": "¿Ha estado particularmente irritable o le han dado arranques de coraje?", "text_en": "Have you been particularly irritable or had outbursts of anger?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q25", "text": "¿Ha tenido dificultad para concentrarse?", "text_en": "Have you had difficulty concentrating?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q26", "text": "¿Ha estado nervioso o constantemente en alerta?", "text_en": "Have you been nervous or constantly on alert?", "type": "yes_no", "group": "affectation"},
    {"id": "g1_q27", "text": "¿Se ha sobresaltado o sentido nervioso fácilmente por cualquier cosa?", "text_en": "Have you been easily startled or felt nervous about anything?", "type": "yes_no", "group": "affectation"}
]

# Guía II Questions (Factores de Riesgo Psicosocial)
GUIDE2_QUESTIONS = [
    {"id": "g2_q1", "text": "Mi trabajo me exige hacer gran esfuerzo físico.", "text_en": "My job requires me to make significant physical effort.", "group": "work_conditions"},
    {"id": "g2_q2", "text": "Siento que estoy expuesto(a) a riesgos físicos en mi lugar de trabajo.", "text_en": "I feel exposed to physical risks in my workplace.", "group": "work_conditions"},
    {"id": "g2_q3", "text": "Manejo herramientas o equipo que representa riesgo para mi integridad física.", "text_en": "I handle tools or equipment that pose a risk to my physical integrity.", "group": "work_conditions"},
    {"id": "g2_q4", "text": "Trabajo en un lugar donde hay ruidos fuertes o constantes.", "text_en": "I work in a place with loud or constant noise.", "group": "work_conditions"},
    {"id": "g2_q5", "text": "Trabajo en un lugar donde hay temperaturas extremas (muy altas o muy bajas).", "text_en": "I work in a place with extreme temperatures (very high or very low).", "group": "work_conditions"},
    {"id": "g2_q6", "text": "Estoy expuesto(a) a sustancias químicas o materiales peligrosos en mi trabajo.", "text_en": "I am exposed to chemicals or hazardous materials in my job.", "group": "work_conditions"},
    {"id": "g2_q7", "text": "Mi trabajo requiere que esté de pie por largos periodos.", "text_en": "My job requires me to stand for long periods.", "group": "work_conditions"},
    {"id": "g2_q8", "text": "Realizo movimientos repetitivos durante mi jornada laboral.", "text_en": "I perform repetitive movements during my workday.", "group": "work_conditions"},
    {"id": "g2_q9", "text": "Mi trabajo requiere que adopte posturas incómodas o forzadas.", "text_en": "My job requires me to adopt uncomfortable or forced postures.", "group": "work_conditions"},
    {"id": "g2_q10", "text": "Tengo que cargar o mover objetos pesados en mi trabajo.", "text_en": "I have to lift or move heavy objects in my job.", "group": "work_conditions"},
    {"id": "g2_q11", "text": "Mi trabajo me permite tomar pausas cuando las necesito.", "text_en": "My job allows me to take breaks when I need them.", "group": "workload_pace"},
    {"id": "g2_q12", "text": "Puedo decidir la cantidad de trabajo que realizo durante la jornada laboral.", "text_en": "I can decide the amount of work I do during the workday.", "group": "workload_pace"},
    {"id": "g2_q13", "text": "Tengo libertad para decidir cómo realizar mi trabajo.", "text_en": "I have the freedom to decide how to perform my job.", "group": "workload_pace"},
    {"id": "g2_q14", "text": "Mi trabajo requiere que tome decisiones difíciles.", "text_en": "My job requires me to make difficult decisions.", "group": "workload_pace"},
    {"id": "g2_q15", "text": "Tengo que atender varias tareas al mismo tiempo en mi trabajo.", "text_en": "I have to handle multiple tasks at the same time in my job.", "group": "workload_pace"},
    {"id": "g2_q16", "text": "Mi trabajo requiere un alto nivel de concentración.", "text_en": "My job requires a high level of concentration.", "group": "workload_pace"},
    {"id": "g2_q17", "text": "La cantidad de trabajo que tengo que hacer es excesiva.", "text_en": "The amount of work I have to do is excessive.", "group": "workload_pace"},
    {"id": "g2_q18", "text": "Tengo que trabajar horas extras con frecuencia.", "text_en": "I have to work overtime frequently.", "group": "workload_pace"},
    {"id": "g2_q19", "text": "Mi trabajo me exige estar disponible fuera de mi horario laboral.", "text_en": "My job requires me to be available outside my working hours.", "group": "workload_pace"},
    {"id": "g2_q20", "text": "Siento que mi ritmo de trabajo es muy acelerado.", "text_en": "I feel that my work pace is very fast.", "group": "workload_pace"},
    {"id": "g2_q21", "text": "Mi jefe me presiona para cumplir con los objetivos de trabajo.", "text_en": "My boss pressures me to meet work goals.", "group": "control_decision"},
    {"id": "g2_q22", "text": "Recibo órdenes contradictorias de diferentes personas en mi trabajo.", "text_en": "I receive contradictory orders from different people at work.", "group": "control_decision"},
    {"id": "g2_q23", "text": "Mi jefe me da instrucciones claras sobre lo que debo hacer.", "text_en": "My boss gives me clear instructions about what I should do.", "group": "control_decision"},
    {"id": "g2_q24", "text": "Mi jefe me apoya cuando enfrento problemas en el trabajo.", "text_en": "My boss supports me when I face problems at work.", "group": "control_decision"},
    {"id": "g2_q25", "text": "Siento que mi jefe confía en mi capacidad para realizar mi trabajo.", "text_en": "I feel that my boss trusts my ability to perform my job.", "group": "control_decision"},
    {"id": "g2_q26", "text": "Mi jefe me trata con respeto.", "text_en": "My boss treats me with respect.", "group": "work_relationships"},
    {"id": "g2_q27", "text": "En mi trabajo me siento valorado(a) por mis compañeros.", "text_en": "At work, I feel valued by my colleagues.", "group": "work_relationships"},
    {"id": "g2_q28", "text": "Tengo buena comunicación con mis compañeros de trabajo.", "text_en": "I have good communication with my coworkers.", "group": "work_relationships"},
    {"id": "g2_q29", "text": "En mi trabajo existe un ambiente de colaboración entre compañeros.", "text_en": "There is a collaborative environment among colleagues at my workplace.", "group": "work_relationships"},
    {"id": "g2_q30", "text": "Recibo críticas o comentarios negativos de mis compañeros con frecuencia.", "text_en": "I frequently receive criticism or negative comments from my colleagues.", "group": "work_relationships"},
    {"id": "g2_q31", "text": "Siento que mis compañeros me excluyen o ignoran.", "text_en": "I feel that my colleagues exclude or ignore me.", "group": "work_relationships"},
    {"id": "g2_q32", "text": "En mi trabajo he sido víctima de burlas o bromas pesadas.", "text_en": "At work, I have been a victim of teasing or heavy-handed jokes.", "group": "work_relationships"},
    {"id": "g2_q33", "text": "He sido testigo o víctima de discriminación en mi lugar de trabajo.", "text_en": "I have witnessed or been a victim of discrimination in my workplace.", "group": "work_relationships"},
    {"id": "g2_q34", "text": "Mi trabajo interfiere con mis responsabilidades familiares.", "text_en": "My job interferes with my family responsibilities.", "group": "work_life_balance"},
    {"id": "g2_q35", "text": "Siento que mi trabajo afecta negativamente mi vida personal.", "text_en": "I feel that my job negatively affects my personal life.", "group": "work_life_balance"},
    {"id": "g2_q36", "text": "Tengo tiempo suficiente para realizar mis actividades personales fuera del trabajo.", "text_en": "I have enough time to carry out my personal activities outside of work.", "group": "work_life_balance"},
    {"id": "g2_q37", "text": "Mi horario de trabajo es flexible.", "text_en": "My work schedule is flexible.", "group": "work_life_balance"},
    {"id": "g2_q38", "text": "Recibo capacitación para realizar mejor mi trabajo.", "text_en": "I receive training to perform my job better.", "group": "work_life_balance"},
    {"id": "g2_q39", "text": "Tengo oportunidades de crecimiento profesional en mi trabajo.", "text_en": "I have opportunities for professional growth in my job.", "group": "work_life_balance"},
    {"id": "g2_q40", "text": "Siento que mi trabajo es estable.", "text_en": "I feel that my job is stable.", "group": "work_life_balance"},
    {"id": "g2_q41", "text": "Mi salario es adecuado para las responsabilidades que tengo.", "text_en": "My salary is adequate for the responsibilities I have.", "group": "work_life_balance"},
    {"id": "g2_q42", "text": "Recibo beneficios adicionales (como bonos o prestaciones) por mi trabajo.", "text_en": "I receive additional benefits (such as bonuses or perks) for my job.", "group": "work_life_balance"},
    {"id": "g2_q43", "text": "Siento que mi trabajo es importante para la empresa.", "text_en": "I feel that my job is important to the company.", "group": "work_life_balance"},
    {"id": "g2_q44", "text": "Me siento motivado(a) para realizar mi trabajo.", "text_en": "I feel motivated to perform my job.", "group": "work_life_balance"},
    {"id": "g2_q45", "text": "Mi trabajo me permite desarrollar nuevas habilidades.", "text_en": "My job allows me to develop new skills.", "group": "work_life_balance"},
    {"id": "g2_q46", "text": "Siento que mi trabajo tiene un propósito claro.", "text_en": "I feel that my job has a clear purpose.", "group": "work_life_balance"}
]

# Guía III Questions (Entorno Organizacional Favorable)
GUIDE3_QUESTIONS = [
    {"id": "g3_q1", "text": "En mi trabajo me informan claramente cuáles son mis funciones y responsabilidades.", "text_en": "At my workplace, I am clearly informed about my duties and responsibilities."},
    {"id": "g3_q2", "text": "Recibo instrucciones claras y precisas para realizar mi trabajo.", "text_en": "I receive clear and precise instructions to perform my job."},
    {"id": "g3_q3", "text": "Mi jefe me comunica de manera efectiva lo que espera de mí.", "text_en": "My boss effectively communicates what is expected of me."},
    {"id": "g3_q4", "text": "En mi trabajo me proporcionan los recursos necesarios para realizar mis tareas.", "text_en": "At my workplace, I am provided with the necessary resources to perform my tasks."},
    {"id": "g3_q5", "text": "Tengo acceso a las herramientas y equipos necesarios para hacer mi trabajo.", "text_en": "I have access to the tools and equipment necessary to do my job."},
    {"id": "g3_q6", "text": "Recibo retroalimentación sobre mi desempeño laboral.", "text_en": "I receive feedback on my job performance."},
    {"id": "g3_q7", "text": "Mi jefe reconoce mi esfuerzo y trabajo bien hecho.", "text_en": "My boss acknowledges my effort and well-done work."},
    {"id": "g3_q8", "text": "En mi trabajo me siento valorado(a) por mis contribuciones.", "text_en": "At my workplace, I feel valued for my contributions."},
    {"id": "g3_q9", "text": "Recibo reconocimiento por mis logros en el trabajo.", "text_en": "I receive recognition for my achievements at work."},
    {"id": "g3_q10", "text": "En mi lugar de trabajo se promueve la igualdad de oportunidades.", "text_en": "My workplace promotes equal opportunities."},
    {"id": "g3_q11", "text": "Siento que en mi trabajo se me trata con justicia.", "text_en": "I feel that I am treated fairly at my workplace."},
    {"id": "g3_q12", "text": "En mi trabajo se toman en cuenta mis opiniones.", "text_en": "My opinions are taken into account at my workplace."},
    {"id": "g3_q13", "text": "Puedo expresar mis ideas y sugerencias en mi lugar de trabajo.", "text_en": "I can express my ideas and suggestions at my workplace."},
    {"id": "g3_q14", "text": "En mi trabajo se fomenta la participación en la toma de decisiones.", "text_en": "My workplace encourages participation in decision-making."},
    {"id": "g3_q15", "text": "Siento que pertenezco a un equipo de trabajo.", "text_en": "I feel that I belong to a work team."},
    {"id": "g3_q16", "text": "En mi lugar de trabajo hay un ambiente de respeto mutuo.", "text_en": "There is an atmosphere of mutual respect at my workplace."},
    {"id": "g3_q17", "text": "Mis compañeros de trabajo me tratan con cortesía.", "text_en": "My colleagues treat me with courtesy."},
    {"id": "g3_q18", "text": "En mi trabajo se promueve la colaboración entre compañeros.", "text_en": "My workplace promotes collaboration among colleagues."},
    {"id": "g3_q19", "text": "Siento que en mi trabajo hay un buen ambiente laboral.", "text_en": "I feel that there is a good work environment at my workplace."},
    {"id": "g3_q20", "text": "En mi lugar de trabajo se fomenta la confianza entre empleados.", "text_en": "My workplace fosters trust among employees."},
    {"id": "g3_q21", "text": "Mi empresa promueve actividades para mejorar el clima laboral.", "text_en": "My company promotes activities to improve the work environment."},
    {"id": "g3_q22", "text": "Recibo apoyo de mi empresa para balancear mi vida laboral y personal.", "text_en": "I receive support from my company to balance my work and personal life."},
    {"id": "g3_q23", "text": "Mi empresa ofrece programas o beneficios que mejoran mi bienestar.", "text_en": "My company offers programs or benefits that improve my well-being."},
    {"id": "g3_q24", "text": "Siento que mi empresa se preocupa por mi salud y seguridad.", "text_en": "I feel that my company cares about my health and safety."},
    {"id": "g3_q25", "text": "En mi trabajo se promueve el respeto a la diversidad.", "text_en": "My workplace promotes respect for diversity."},
    {"id": "g3_q26", "text": "Siento que mi empresa valora mi trabajo y esfuerzo.", "text_en": "I feel that my company values my work and effort."}
]

# Password hashing with salt
def hash_password(password, salt):
    salted_password = password + salt
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    return hashed

# Predefined hashed password
CORRECT_PASSWORD_HASH = hash_password(PASSWORD, SALT)

# Initialize session state
if "responses" not in st.session_state:
    st.session_state.responses = {}
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

# Log file path
LOG_FILE = "nom035_log.csv"

# Initialize log file with headers if it doesn't exist
def initialize_log():
    if not os.path.exists(LOG_FILE):
        headers = (
            ["timestamp"] +
            [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" for subfield in q["subfields"]] +
            [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"] +
            [q["id"] for q in GUIDE2_QUESTIONS] +
            [q["id"] for q in GUIDE3_QUESTIONS]
        )
        df = pd.DataFrame(columns=headers)
        df.to_csv(LOG_FILE, index=False)

# Save responses to log
def save_responses_to_log():
    initialize_log()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    responses = st.session_state.responses.copy()
    responses["timestamp"] = timestamp
    df = pd.DataFrame([responses])
    # Append to existing log
    existing_df = pd.read_csv(LOG_FILE)
    updated_df = pd.concat([existing_df, df], ignore_index=True)
    updated_df.to_csv(LOG_FILE, index=False)
    return df, timestamp

# Refresh log file
def refresh_log():
    initialize_log()  # Re-creates empty log with headers
    return True

# Streamlit app configuration
st.set_page_config(page_title="NOM-035 Survey", layout="wide")
st.markdown("""
    <style>
    .main {background-color: #f0f2f6;}
    .stButton>button {background-color: #4CAF50; color: white; border-radius: 8px; margin: 10px 0;}
    .stProgress .st-bo {background-color: #4CAF50;}
    .question {font-size: 18px; margin-bottom: 10px;}
    .tooltip {color: #555; font-size: 14px;}
    .section-header {font-size: 20px; font-weight: bold; margin-top: 20px;}
    .stTextInput, .stSelectbox, .stRadio {margin-bottom: 20px;}
    .stRadio > div {flex-direction: row; flex-wrap: wrap;}
    .radio-group {border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-bottom: 20px;}
    .st-expander {border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px;}
    @media (max-width: 600px) {
        .question {font-size: 16px;}
        .section-header {font-size: 18px;}
        .stRadio > div {flex-direction: column;}
    }
    </style>
""", unsafe_allow_html=True)

# Language selector in sidebar
lang = st.sidebar.selectbox("Language / Idioma", ["Español", "English"], key="language_selector")
lang_code = "es" if lang == "Español" else "en"
t = LANGUAGES[lang_code]

# Valid response options for Guía II and III
VALID_RESPONSES_GUIDE2_3 = [
    t["always"], t["almost_always"], t["sometimes"], 
    t["almost_never"], t["never"]
]

# Sidebar: Download and Refresh Log
with st.sidebar:
    st.subheader(t["download_log"])
    password_download = st.text_input(t["password_prompt"], type="password", key="download_password")
    if st.button(t["download_log"], key="download_button"):
        if action_lock():
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

    st.subheader(t["refresh_log"])
    password_refresh = st.text_input(t["password_prompt"], type="password", key="refresh_password")
    if st.button(t["refresh_log"], key="refresh_button"):
        if action_lock():
            hashed_input = hash_password(password_refresh, SALT)
            if hashed_input == CORRECT_PASSWORD_HASH:
                refresh_log()
                st.success(t["log_refreshed"])
            else:
                st.error(t["incorrect_password"])

# Action lock to prevent rapid clicks
def action_lock():
    current_time = time.time()
    if current_time - st.session_state.last_action_time < 1:  # 1-second debounce
        st.warning(t["please_wait"])
        return False
    st.session_state.last_action_time = current_time
    return True

# Progress calculation
def calculate_progress():
    total_questions = len(GUIDE1_QUESTIONS) + 2  # +2 for name subfields
    if st.session_state.has_trauma:
        total_questions += len(GUIDE2_QUESTIONS) + len(GUIDE3_QUESTIONS)
    
    answered_questions = 0
    required_keys = (
        [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" for subfield in q["subfields"]] +
        [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"]
    )
    if st.session_state.has_trauma:
        required_keys += [q["id"] for q in GUIDE2_QUESTIONS] + [q["id"] for q in GUIDE3_QUESTIONS]
    
    for key in required_keys:
        if key in st.session_state.responses and st.session_state.responses[key] not in [None, "", 0]:
            answered_questions += 1
    
    return answered_questions / total_questions if total_questions > 0 else 0

# Input validation
def validate_responses(responses, guide_questions, is_guide1=False):
    errors = []
    if is_guide1:
        # Validate name fields
        for subfield in GUIDE1_QUESTIONS[0]["subfields"]:
            if subfield["id"] not in responses or not responses[subfield["id"]].strip():
                errors.append(t["missing_field"].format(field=subfield["label" if lang_code == "es" else "label_en"]))
        
        # Validate age
        if "g1_q2" not in responses or not (18 <= responses["g1_q2"] <= 100):
            errors.append(t["invalid_age"])
        
        # Validate years worked
        if "g1_q4" in responses and "g1_q2" in responses:
            if not (0 <= responses["g1_q4"] <= responses["g1_q2"]):
                errors.append(t["invalid_years_worked"])
    
    # Collect required keys
    required_keys = [q["id"] for q in guide_questions]
    if is_guide1:
        # Add subfields for text_group questions
        required_keys += [subfield["id"] for q in guide_questions if q.get("type") == "text_group" for subfield in q["subfields"]]
    
    # Check all required fields
    for key in required_keys:
        if key not in responses or responses[key] is None:
            question_text = next((q["text" if lang_code == "es" else "text_en"] for q in guide_questions if q["id"] == key), key)
            errors.append(t["missing_field"].format(field=question_text))
            if DEBUG_MODE:
                logger.debug(f"Validation failed for {key}: Missing or None")
        elif isinstance(responses[key], str) and not responses[key].strip():
            question_text = next((q["text" if lang_code == "es" else "text_en"] for q in guide_questions if q["id"] == key), key)
            errors.append(t["missing_field"].format(field=question_text))
            if DEBUG_MODE:
                logger.debug(f"Validation failed for {key}: Empty string")
        elif not is_guide1 and responses[key] not in VALID_RESPONSES_GUIDE2_3:
            question_text = next((q["text" if lang_code == "es" else "text_en"] for q in guide_questions if q["id"] == key), key)
            errors.append(t["missing_field"].format(field=question_text))
            if DEBUG_MODE:
                logger.debug(f"Validation failed for {key}: Invalid response '{responses[key]}'")
    
    return errors

# Main app
st.title(t["title"])
st.write(t["welcome"])

# Progress bar
progress = calculate_progress()
st.progress(progress)
st.write(f"{t['progress']}: {int(progress * 100)}%")

# Guía I: Acontecimientos Traumáticos Severos
if not st.session_state.guide1_complete:
    st.header(t["guide1"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide1']}</p>", unsafe_allow_html=True)
    
    # Group questions by section
    guide1_groups = [
        ("personal_info", t["personal_info"], GUIDE1_QUESTIONS[:7]),
        ("traumatic_events", t["traumatic_events"], GUIDE1_QUESTIONS[7:13]),
        ("persistent_memories", t["persistent_memories"], GUIDE1_QUESTIONS[13:15]),
        ("avoidance_efforts", t["avoidance_efforts"], GUIDE1_QUESTIONS[15:22]),
        ("affectation", t["affectation"], GUIDE1_QUESTIONS[22:])
    ]
    
    for group_id, group_label, questions in guide1_groups:
        with st.expander(group_label, expanded=True):
            for q in questions:
                st.markdown(f"<p class='question' id='question-{q['id']}' role='heading' aria-label='{q['text' if lang_code == 'es' else 'text_en']}'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
                if q["type"] == "text_group":
                    for subfield in q["subfields"]:
                        response = st.text_input(
                            subfield["label" if lang_code == "es" else "label_en"], 
                            key=subfield["id"],
                            placeholder=subfield["label" if lang_code == "es" else "label_en"]
                        )
                        st.session_state.responses[subfield["id"]] = response
                elif q["type"] == "number":
                    response = st.number_input(
                        "", min_value=0, max_value=100, step=1, key=q["id"], 
                        format="%d", label_visibility="collapsed"
                    )
                    st.session_state.responses[q["id"]] = response
                elif q["type"] == "select":
                    response = st.selectbox(
                        "", q["options" if lang_code == "es" else "options_en"], 
                        key=q["id"], label_visibility="collapsed",
                        index=None, placeholder="Seleccione / Select"
                    )
                    st.session_state.responses[q["id"]] = response
                elif q["type"] == "yes_no":
                    st.markdown(f"<div class='radio-group' role='radiogroup' aria-describedby='question-{q['id']}'>", unsafe_allow_html=True)
                    response = st.radio(
                        "", [t["yes"], t["no"]], key=q["id"], 
                        label_visibility="collapsed"
                    )
                    st.session_state.responses[q["id"]] = response
                    st.markdown("</div>", unsafe_allow_html=True)
                    if response == t["yes"]:
                        st.session_state.has_trauma = True
    
    # Submit Button
    if st.button(t["submit"], key="submit_guide1"):
        if action_lock():
            errors = validate_responses(st.session_state.responses, GUIDE1_QUESTIONS, is_guide1=True)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.guide1_complete = True
                if not st.session_state.has_trauma:
                    save_responses_to_log()  # Save to log if no trauma
                st.success("Guía I completada / Guide I completed")

# Guía II: Factores de Riesgo Psicosocial (only if trauma detected)
if st.session_state.guide1_complete and st.session_state.has_trauma and not st.session_state.guide2_complete:
    st.header(t["guide2"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide2']}</p>", unsafe_allow_html=True)
    
    # Initialize responses for all Guía II questions
    for q in GUIDE2_QUESTIONS:
        if q["id"] not in st.session_state.responses:
            st.session_state.responses[q["id"]] = None
    
    # Group questions by section
    guide2_groups = [
        ("work_conditions", t["work_conditions"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_conditions"]),
        ("workload_pace", t["workload_pace"], [q for q in GUIDE2_QUESTIONS if q["group"] == "workload_pace"]),
        ("control_decision", t["control_decision"], [q for q in GUIDE2_QUESTIONS if q["group"] == "control_decision"]),
        ("work_relationships", t["work_relationships"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_relationships"]),
        ("work_life_balance", t["work_life_balance"], [q for q in GUIDE2_QUESTIONS if q["group"] == "work_life_balance"])
    ]
    
    for group_id, group_label, questions in guide2_groups:
        with st.expander(group_label, expanded=True):
            for q in questions:
                st.markdown(f"<div class='radio-group' role='radiogroup' aria-describedby='question-{q['id']}'><p class='question' id='question-{q['id']}' role='heading' aria-label='{q['text' if lang_code == 'es' else 'text_en']}'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
                response = st.radio(
                    "", [t["always"], t["almost_always"], t["sometimes"], t["almost_never"], t["never"]], 
                    key=q["id"], label_visibility="collapsed",
                    index=None
                )
                st.session_state.responses[q["id"]] = response
                st.markdown("</div>", unsafe_allow_html=True)
    
    # Submit Button
    if st.button(t["submit"], key="submit_guide2"):
        if action_lock():
            errors = validate_responses(st.session_state.responses, GUIDE2_QUESTIONS)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.guide2_complete = True
                st.success("Guía II completada / Guide II completed")

# Guía III: Entorno Organizacional Favorable (only if trauma detected)
if st.session_state.guide2_complete and st.session_state.has_trauma and not st.session_state.guide3_complete:
    st.header(t["guide3"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide3']}</p>", unsafe_allow_html=True)
    
    # Initialize responses for all Guía III questions
    for q in GUIDE3_QUESTIONS:
        if q["id"] not in st.session_state.responses:
            st.session_state.responses[q["id"]] = None
    
    # Display all questions (no grouping for Guía III)
    for q in GUIDE3_QUESTIONS:
        st.markdown(f"<div class='radio-group' role='radiogroup' aria-describedby='question-{q['id']}'><p class='question' id='question-{q['id']}' role='heading' aria-label='{q['text' if lang_code == 'es' else 'text_en']}'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["always"], t["almost_always"], t["sometimes"], t["almost_never"], t["never"]], 
            key=q["id"], label_visibility="collapsed",
            index=None
        )
        st.session_state.responses[q["id"]] = response
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Submit Button
    if st.button(t["submit"], key="submit_guide3"):
        if action_lock():
            errors = validate_responses(st.session_state.responses, GUIDE3_QUESTIONS)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.guide3_complete = True
                save_responses_to_log()  # Save to log after completing Guía III
                st.success("Guía III completada / Guide III completed")
