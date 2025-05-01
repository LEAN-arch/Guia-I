import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import base64
import secrets
import re

# Language selector and translations
LANGUAGES = {
    "es": {
        "title": "Encuesta NOM-035-STPS-2018",
        "welcome": "Bienvenido a la encuesta NOM-035. Responda todas las preguntas con honestidad.",
        "guide1": "Guía I: Acontecimientos Traumáticos Severos",
        "guide2": "Guía II: Factores de Riesgo Psicosocial",
        "guide3": "Guía III: Entorno Organizacional Favorable",
        "submit": "Enviar",
        "reset": "Reiniciar Respuestas",
        "download_log": "Descargar Registro",
        "password_prompt": "Ingrese la contraseña para descargar el registro:",
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
        "personal_info": "Por favor comparta la siguiente información.",
        "next_section": "En la siguiente sección, seleccione la respuesta que mejor aplique a su experiencia.",
        "persistent_memories": "Recuerdos persistentes sobre el acontecimiento (durante el último mes):",
        "avoidance_efforts": "Esfuerzo por evitar circunstancias parecidas o asociadas al acontecimiento (durante el último mes):",
        "affectation": "Afectación (durante el último mes):",
        "validation_error": "Por favor complete todos los campos requeridos correctamente.",
        "invalid_age": "La edad debe ser un número entre 18 y 100.",
        "invalid_years_worked": "Los años trabajados deben ser un número entre 0 y la edad ingresada."
    },
    "en": {
        "title": "NOM-035-STPS-2018 Survey",
        "welcome": "Welcome to the NOM-035 survey. Please answer all questions honestly.",
        "guide1": "Guide I: Severe Traumatic Events",
        "guide2": "Guide II: Psychosocial Risk Factors",
        "guide3": "Guide III: Favorable Organizational Environment",
        "submit": "Submit",
        "reset": "Reset Responses",
        "download_log": "Download Log",
        "password_prompt": "Enter the password to download the log:",
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
        "personal_info": "Please share the following information.",
        "next_section": "In the following section, select the response that best applies to your experience.",
        "persistent_memories": "Persistent memories about the event (during the last month):",
        "avoidance_efforts": "Efforts to avoid circumstances similar to or associated with the event (during the last month):",
        "affectation": "Affectation (during the last month):",
        "validation_error": "Please complete all required fields correctly.",
        "invalid_age": "Age must be a number between 18 and 100.",
        "invalid_years_worked": "Years worked must be a number between 0 and the entered age."
    }
}

# Guía I Questions
GUIDE1_QUESTIONS = [
    {"id": "g1_q1", "text": "¿Cuál es su nombre?", "text_en": "What is your name?", "type": "text_group", "subfields": [
        {"id": "g1_q1_nombre", "label": "Nombre", "label_en": "First Name"},
        {"id": "g1_q1_apellido", "label": "Apellido", "label_en": "Last Name"},
        {"id": "g1_q1_segundo_apellido", "label": "Segundo apellido", "label_en": "Second Last Name"}
    ]},
    {"id": "g1_q2", "text": "¿Qué edad tienes? (Solo incluye el número de años e.g. 21)", "text_en": "How old are you? (Only include the number of years, e.g., 21)", "type": "number"},
    {"id": "g1_q3", "text": "¿Cuál es tu género?", "text_en": "What is your gender?", "type": "select", "options": ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"], "options_en": ["Female", "Male", "LGTBTTTIQ+", "Other"]},
    {"id": "g1_q4", "text": "¿Cuántos años llevas trabajando para esta empresa? (Solo incluye el número de años e.g. 3)", "text_en": "How many years have you been working for this company? (Only include the number of years, e.g., 3)", "type": "number"},
    {"id": "g1_q5", "text": "¿En qué departamento labora? ¿De qué departamento es parte?", "text_en": "In which department do you work? Which department are you part of?", "type": "select", "options": ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"], "options_en": ["Maintenance", "Quality Control", "Manufacturing", "Sales", "Production", "Human Resources", "Sales and Marketing", "Accounting and Finance", "Administration"]},
    {"id": "g1_q6", "text": "¿Cuál es su función?", "text_en": "What is your role?", "type": "select", "options": ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"], "options_en": ["Operator", "Technician", "Engineer", "Analyst", "Supervisor", "Manager", "Director"]},
    {"id": "g1_q7", "text": "¿Cuál es su lugar de trabajo? ¿Dónde se encuentra su lugar de trabajo? (Seleccione el lugar donde pase mayormente su tiempo)", "text_en": "What is your workplace? Where is your workplace located? (Select the place where you spend most of your time)", "type": "select", "options": ["Planta 1", "Planta 2", "Planta 3"], "options_en": ["Plant 1", "Plant 2", "Plant 3"]},
    {"id": "g1_q8", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo un accidente que tenga como consecuencia la muerte, la pérdida de un miembro o una lesión grave?", "text_en": "Have you ever witnessed or suffered, during or due to work, an accident resulting in death, loss of a limb, or a serious injury?", "type": "yes_no"},
    {"id": "g1_q9", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo un asalto?", "text_en": "Have you ever witnessed or suffered, during or due to work, an assault?", "type": "yes_no"},
    {"id": "g1_q10", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo actos violentos que derivaron en lesiones graves?", "text_en": "Have you ever witnessed or suffered, during or due to work, violent acts that resulted in serious injuries?", "type": "yes_no"},
    {"id": "g1_q11", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo un secuestro?", "text_en": "Have you ever witnessed or suffered, during or due to work, a kidnapping?", "type": "yes_no"},
    {"id": "g1_q12", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo amenazas?", "text_en": "Have you ever witnessed or suffered, during or due to work, threats?", "type": "yes_no"},
    {"id": "g1_q13", "text": "¿Ha presenciado o sufrido alguna vez, durante o con motivo del trabajo cualquier otra situación que ponga en riesgo su vida o salud, y/o la de otras personas?", "text_en": "Have you ever witnessed or suffered, during or due to work, any other situation that puts your life or health, and/or that of others, at risk?", "type": "yes_no"},
    {"id": "g1_q14", "text": "¿Ha tenido recuerdos recurrentes sobre el acontecimiento que le provocan malestar?", "text_en": "Have you had recurrent memories of the event that cause you discomfort?", "type": "yes_no"},
    {"id": "g1_q15", "text": "¿Ha tenido sueños de carácter recurrente sobre el acontecimiento, que le producen malestar?", "text_en": "Have you had recurrent dreams about the event that cause you discomfort?", "type": "yes_no"},
    {"id": "g1_q16", "text": "¿Se ha esforzado por evitar todo tipo de sentimientos, conversaciones o situaciones que le puedan recordar el acontecimiento?", "text_en": "Have you made an effort to avoid all kinds of feelings, conversations, or situations that might remind you of the event?", "type": "yes_no"},
    {"id": "g1_q17", "text": "¿Se ha esforzado por evitar todo tipo de actividades, lugares o personas que motivan recuerdos del acontecimiento?", "text_en": "Have you made an effort to avoid all kinds of activities, places, or people that trigger memories of the event?", "type": "yes_no"},
    {"id": "g1_q18", "text": "¿Ha tenido dificultad para recordar alguna parte importante del evento?", "text_en": "Have you had difficulty remembering some important part of the event?", "type": "yes_no"},
    {"id": "g1_q19", "text": "¿Ha disminuido su interés en sus actividades cotidianas?", "text_en": "Has your interest in your daily activities decreased?", "type": "yes_no"},
    {"id": "g1_q20", "text": "¿Se ha sentido usted alejado o distante de los demás?", "text_en": "Have you felt distant or detached from others?", "type": "yes_no"},
    {"id": "g1_q21", "text": "¿Ha notado que tiene dificultad para expresar sus sentimientos?", "text_en": "Have you noticed difficulty expressing your feelings?", "type": "yes_no"},
    {"id": "g1_q22", "text": "¿Ha tenido la impresión de que su vida se va a acortar, que va a morir antes que otras personas o que tiene un futuro limitado?", "text_en": "Have you had the impression that your life will be shortened, that you will die before others, or that you have a limited future?", "type": "yes_no"},
    {"id": "g1_q23", "text": "¿Ha tenido usted dificultades o problemas para dormir?", "text_en": "Have you had difficulties or problems sleeping?", "type": "yes_no"},
    {"id": "g1_q24", "text": "¿Ha estado particularmente irritable o le han dado arranques de coraje?", "text_en": "Have you been particularly irritable or had outbursts of anger?", "type": "yes_no"},
    {"id": "g1_q25", "text": "¿Ha tenido dificultad para concentrarse?", "text_en": "Have you had difficulty concentrating?", "type": "yes_no"},
    {"id": "g1_q26", "text": "¿Ha estado nervioso o constantemente en alerta?", "text_en": "Have you been nervous or constantly on alert?", "type": "yes_no"},
    {"id": "g1_q27", "text": "¿Se ha sobresaltado o sentido nervioso fácilmente por cualquier cosa?", "text_en": "Have you been easily startled or felt nervous about anything?", "type": "yes_no"}
]

# Guía II Questions (Factores de Riesgo Psicosocial)
GUIDE2_QUESTIONS = [
    {"id": "g2_q1", "text": "Mi trabajo me exige hacer gran esfuerzo físico.", "text_en": "My job requires me to make significant physical effort."},
    {"id": "g2_q2", "text": "Siento que estoy expuesto(a) a riesgos físicos en mi lugar de trabajo.", "text_en": "I feel exposed to physical risks in my workplace."},
    {"id": "g2_q3", "text": "Manejo herramientas o equipo que representa riesgo para mi integridad física.", "text_en": "I handle tools or equipment that pose a risk to my physical integrity."},
    {"id": "g2_q4", "text": "Trabajo en un lugar donde hay ruidos fuertes o constantes.", "text_en": "I work in a place with loud or constant noise."},
    {"id": "g2_q5", "text": "Trabajo en un lugar donde hay temperaturas extremas (muy altas o muy bajas).", "text_en": "I work in a place with extreme temperatures (very high or very low)."},
    {"id": "g2_q6", "text": "Estoy expuesto(a) a sustancias químicas o materiales peligrosos en mi trabajo.", "text_en": "I am exposed to chemicals or hazardous materials in my job."},
    {"id": "g2_q7", "text": "Mi trabajo requiere que esté de pie por largos periodos.", "text_en": "My job requires me to stand for long periods."},
    {"id": "g2_q8", "text": "Realizo movimientos repetitivos durante mi jornada laboral.", "text_en": "I perform repetitive movements during my workday."},
    {"id": "g2_q9", "text": "Mi trabajo requiere que adopte posturas incómodas o forzadas.", "text_en": "My job requires me to adopt uncomfortable or forced postures."},
    {"id": "g2_q10", "text": "Tengo que cargar o mover objetos pesados en mi trabajo.", "text_en": "I have to lift or move heavy objects in my job."},
    {"id": "g2_q11", "text": "Mi trabajo me permite tomar pausas cuando las necesito.", "text_en": "My job allows me to take breaks when I need them."},
    {"id": "g2_q12", "text": "Puedo decidir la cantidad de trabajo que realizo durante la jornada laboral.", "text_en": "I can decide the amount of work I do during the workday."},
    {"id": "g2_q13", "text": "Tengo libertad para decidir cómo realizar mi trabajo.", "text_en": "I have the freedom to decide how to perform my job."},
    {"id": "g2_q14", "text": "Mi trabajo requiere que tome decisiones difíciles.", "text_en": "My job requires me to make difficult decisions."},
    {"id": "g2_q15", "text": "Tengo que atender varias tareas al mismo tiempo en mi trabajo.", "text_en": "I have to handle multiple tasks at the same time in my job."},
    {"id": "g2_q16", "text": "Mi trabajo requiere un alto nivel de concentración.", "text_en": "My job requires a high level of concentration."},
    {"id": "g2_q17", "text": "La cantidad de trabajo que tengo que hacer es excesiva.", "text_en": "The amount of work I have to do is excessive."},
    {"id": "g2_q18", "text": "Tengo que trabajar horas extras con frecuencia.", "text_en": "I have to work overtime frequently."},
    {"id": "g2_q19", "text": "Mi trabajo me exige estar disponible fuera de mi horario laboral.", "text_en": "My job requires me to be available outside my working hours."},
    {"id": "g2_q20", "text": "Siento que mi ritmo de trabajo es muy acelerado.", "text_en": "I feel that my work pace is very fast."},
    {"id": "g2_q21", "text": "Mi jefe me presiona para cumplir con los objetivos de trabajo.", "text_en": "My boss pressures me to meet work goals."},
    {"id": "g2_q22", "text": "Recibo órdenes contradictorias de diferentes personas en mi trabajo.", "text_en": "I receive contradictory orders from different people at work."},
    {"id": "g2_q23", "text": "Mi jefe me da instrucciones claras sobre lo que debo hacer.", "text_en": "My boss gives me clear instructions about what I should do."},
    {"id": "g2_q24", "text": "Mi jefe me apoya cuando enfrento problemas en el trabajo.", "text_en": "My boss supports me when I face problems at work."},
    {"id": "g2_q25", "text": "Siento que mi jefe confía en mi capacidad para realizar mi trabajo.", "text_en": "I feel that my boss trusts my ability to perform my job."},
    {"id": "g2_q26", "text": "Mi jefe me trata con respeto.", "text_en": "My boss treats me with respect."},
    {"id": "g2_q27", "text": "En mi trabajo me siento valorado(a) por mis compañeros.", "text_en": "At work, I feel valued by my colleagues."},
    {"id": "g2_q28", "text": "Tengo buena comunicación con mis compañeros de trabajo.", "text_en": "I have good communication with my coworkers."},
    {"id": "g2_q29", "text": "En mi trabajo existe un ambiente de colaboración entre compañeros.", "text_en": "There is a collaborative environment among colleagues at my workplace."},
    {"id": "g2_q30", "text": "Recibo críticas o comentarios negativos de mis compañeros con frecuencia.", "text_en": "I frequently receive criticism or negative comments from my colleagues."},
    {"id": "g2_q31", "text": "Siento que mis compañeros me excluyen o ignoran.", "text_en": "I feel that my colleagues exclude or ignore me."},
    {"id": "g2_q32", "text": "En mi trabajo he sido víctima de burlas o bromas pesadas.", "text_en": "At work, I have been a victim of teasing or heavy-handed jokes."},
    {"id": "g2_q33", "text": "He sido testigo o víctima de discriminación en mi lugar de trabajo.", "text_en": "I have witnessed or been a victim of discrimination in my workplace."},
    {"id":劝": "g2_q34", "text": "Mi trabajo interfiere con mis responsabilidades familiares.", "text_en": "My job interferes with my family responsibilities."},
    {"id": "g2_q35", "text": "Siento que mi trabajo afecta negativamente mi vida personal.", "text_en": "I feel that my job negatively affects my personal life."},
    {"id": "g2_q36", "text": "Tengo tiempo suficiente para realizar mis actividades personales fuera del trabajo.", "text_en": "I have enough time to carry out my personal activities outside of work."},
    {"id": "g2_q37", "text": "Mi horario de trabajo es flexible.", "text_en": "My work schedule is flexible."},
    {"id": "g2_q38", "text": "Recibo capacitación para realizar mejor mi trabajo.", "text_en": "I receive training to perform my job better."},
    {"id": "g2_q39", "text": "Tengo oportunidades de crecimiento profesional en mi trabajo.", "text_en": "I have opportunities for professional growth in my job."},
    {"id": "g2_q40", "text": "Siento que mi trabajo es estable.", "text_en": "I feel that my job is stable."},
    {"id": "g2_q41", "text": "Mi salario es adecuado para las responsabilidades que tengo.", "text_en": "My salary is adequate for the responsibilities I have."},
    {"id": "g2_q42", "text": "Recibo beneficios adicionales (como bonos o prestaciones) por mi trabajo.", "text_en": "I receive additional benefits (such as bonuses or perks) for my job."},
    {"id": "g2_q43", "text": "Siento que mi trabajo es importante para la empresa.", "text_en": "I feel that my job is important to the company."},
    {"id": "g2_q44", "text": "Me siento motivado(a) para realizar mi trabajo.", "text_en": "I feel motivated to perform my job."},
    {"id": "g2_q45", "text": "Mi trabajo me permite desarrollar nuevas habilidades.", "text_en": "My job allows me to develop new skills."},
    {"id": "g2_q46", "text": "Siento que mi trabajo tiene un propósito claro.", "text_en": "I feel that my job has a clear purpose."}
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
def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    salted_password = password + salt
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    return hashed, salt

# Predefined hashed password and salt (replace with your own)
PASSWORD = "securepassword123"  # Change in production
CORRECT_PASSWORD_HASH, SALT = hash_password(PASSWORD)

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
    @media (max-width: 600px) {
        .question {font-size: 16px;}
        .section-header {font-size: 18px;}
    }
    </style>
""", unsafe_allow_html=True)

# Language selector
lang = st.sidebar.selectbox("Language / Idioma", ["Español", "English"], key="language_selector")
lang_code = "es" if lang == "Español" else "en"
t = LANGUAGES[lang_code]

# Reset responses
def reset_responses():
    st.session_state.responses = {}
    st.session_state.guide1_complete = False
    st.session_state.guide2_complete = False
    st.session_state.guide3_complete = False
    st.session_state.has_trauma = False

# Main app
st.title(t["title"])
st.write(t["welcome"])

# Progress bar
total_questions = len(GUIDE1_QUESTIONS) + 2  # +2 for name subfields (3 total - 1 for the group)
if st.session_state.has_trauma:
    total_questions += len(GUIDE2_QUESTIONS) + len(GUIDE3_QUESTIONS)
answered_questions = len(st.session_state.responses)
progress = answered_questions / total_questions if total_questions > 0 else 0
st.progress(progress)
st.write(f"{t['progress']}: {int(progress * 100)}%")

# Input validation
def validate_responses(responses, guide_questions, is_guide1=False):
    errors = []
    if is_guide1:
        # Validate name fields
        for subfield in GUIDE1_QUESTIONS[0]["subfields"]:
            if subfield["id"] not in responses or not responses[subfield["id"]].strip():
                errors.append(f"{subfield['label' if lang_code == 'es' else 'label_en']} es requerido.")
        
        # Validate age
        if "g1_q2" not in responses or not (18 <= responses["g1_q2"] <= 100):
            errors.append(t["invalid_age"])
        
        # Validate years worked
        if "g1_q4" in responses and "g1_q2" in responses:
            if not (0 <= responses["g1_q4"] <= responses["g1_q2"]):
                errors.append(t["invalid_years_worked"])
    
    # Check all required fields
    required_keys = [q["id"] for q in guide_questions if q["type"] != "text_group"]
    if is_guide1:
        required_keys += [subfield["id"] for q in guide_questions if q["type"] == "text_group" for subfield in q["subfields"]]
    for key in required_keys:
        if key not in responses or responses[key] is None:
            errors.append(t["validation_error"])
    
    return errors

# Guía I: Acontecimientos Traumáticos Severos
if not st.session_state.guide1_complete:
    st.header(t["guide1"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide1']}</p>", unsafe_allow_html=True)
    
    # Personal Information Section
    st.markdown(f"<p class='section-header' role='region' aria-label='Personal Information'>{t['personal_info']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[:7]:  # Questions 1-7
        st.markdown(f"<p class='question' role='heading' aria-label='Question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
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
    
    # Traumatic Events Section
    st.markdown(f"<p class='section-header' role='region' aria-label='Traumatic Events'>{t['next_section']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[7:13]:  # Questions 8-13
        st.markdown(f"<p class='question' role='heading' aria-label='Question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    # Persistent Memories Section
    st.markdown(f"<p class='section-header' role='region' aria-label='Persistent Memories'>{t['persistent_memories']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[13:15]:  # Questions 14-15
        st.markdown(f"<p class='question' role='heading' aria-label='Question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    # Avoidance Efforts Section
    st.markdown(f"<p class='section-header' role='region' aria-label='Avoidance Efforts'>{t['avoidance_efforts']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[15:22]:  # Questions 16-22
        st.markdown(f"<p class='question' role='heading' aria-label='Question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    # Affectation Section
    st.markdown(f"<p class='section-header' role='region' aria-label='Affectation'>{t['affectation']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[22:]:  # Questions 23-27
        st.markdown(f"<p class='question' role='heading' aria-label='Question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    # Submit and Reset Buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t["submit"], key="submit_guide1"):
            errors = validate_responses(st.session_state.responses, GUIDE1_QUESTIONS, is_guide1=True)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.guide1_complete = True
                st.success("Guía I completada / Guide I completed")
    with col2:
        if st.button(t["reset"], key="reset_guide1"):
            reset_responses()
            st.experimental_rerun()

# Guía II: Factores de Riesgo Psicosocial (only if trauma detected)
if st.session_state.guide1_complete and st.session_state.has_trauma and not st.session_state.guide2_complete:
    st.header(t["guide2"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide2']}</p>", unsafe_allow_html=True)
    
    for q in GUIDE2_QUESTIONS:
        st.markdown(f"<p class='question' role='heading' aria-label='Question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["always"], t["almost_always"], t["sometimes"], t["almost_never"], t["never"]], 
            key=q["id"], label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t["submit"], key="submit_guide2"):
            errors = validate_responses(st.session_state.responses, GUIDE2_QUESTIONS)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.guide2_complete = True
                st.success("Guía II completada / Guide II completed")
    with col2:
        if st.button(t["reset"], key="reset_guide2"):
            for key in [q["id"] for q in GUIDE2_QUESTIONS]:
                st.session_state.responses.pop(key, None)
            st.experimental_rerun()

# Guía III: Entorno Organizacional Favorable (only if trauma detected)
if st.session_state.guide2_complete and st.session_state.has_trauma and not st.session_state.guide3_complete:
    st.header(t["guide3"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide3']}</p>", unsafe_allow_html=True)
    
    for q in GUIDE3_QUESTIONS:
        st.markdown(f"<p class='question' role='heading' aria-label='Question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["always"], t["almost_always"], t["sometimes"], t["almost_never"], t["never"]], 
            key=q["id"], label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t["submit"], key="submit_guide3"):
            errors = validate_responses(st.session_state.responses, GUIDE3_QUESTIONS)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.guide3_complete = True
                st.success("Guía III completada / Guide III completed")
    with col2:
        if st.button(t["reset"], key="reset_guide3"):
            for key in [q["id"] for q in GUIDE3_QUESTIONS]:
                st.session_state.responses.pop(key, None)
            st.experimental_rerun()

# Save responses to CSV
def save_responses():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    responses = st.session_state.responses.copy()
    responses["timestamp"] = timestamp
    df = pd.DataFrame([responses])
    return df, timestamp

# Download log
if st.session_state.guide1_complete and (not st.session_state.has_trauma or st.session_state.guide3_complete):
    st.header(t["download_log"])
    password = st.text_input(t["password_prompt"], type="password", key="download_password")
    if st.button("Descargar / Download", key="download_button"):
        hashed_input, _ = hash_password(password, SALT)
        if hashed_input == CORRECT_PASSWORD_HASH:
            df, timestamp = save_responses()
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="nom035_responses_{timestamp}.csv" role="button" aria-label="Download CSV">Descargar CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.error(t["incorrect_password"])
