import streamlit as st
import pandas as pd
import json
from datetime import datetime
import hashlib
import base64
import os
from io import BytesIO

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
        "next_section": "En la siguiente sección, por favor seleccione la respuesta que mejor aplique en tu experiencia.",
        "persistent_memories": "Recuerdos persistentes sobre el acontecimiento (durante el último mes):",
        "avoidance_efforts": "Esfuerzo por evitar circunstancias parecidas o asociadas al acontecimiento (durante el último mes):",
        "affectation": "Afectación (durante el último mes):"
    },
    "en": {
        "title": "NOM-035-STPS-2018 Survey",
        "welcome": "Welcome to the NOM-035 survey. Please answer all questions honestly.",
        "guide1": "Guide I: Severe Traumatic Events",
        "guide2": "Guide II: Psychosocial Risk Factors",
        "guide3": "Guide III: Favorable Organizational Environment",
        "submit": "Submit",
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
        "next_section": "In the following section, please select the response that best applies to your experience.",
        "persistent_memories": "Persistent memories about the event (during the last month):",
        "avoidance_efforts": "Efforts to avoid circumstances similar to or associated with the event (during the last month):",
        "affectation": "Affectation (during the last month):"
    }
}

# Guía I Questions (as provided)
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
    {"id": "g1_q11", "text": "¿Ha presenciado o sufrido alguna vez, durante o with motivo del trabajo un secuestro?", "text_en": "Have you ever witnessed or suffered, during or due to work, a kidnapping?", "type": "yes_no"},
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

# Sample questions for Guía II and III (replace with full sets)
GUIDE2_QUESTIONS = [
    {"id": "g2_q1", "text": "¿Siente que su carga de trabajo es excesiva?", "text_en": "Do you feel your workload is excessive?"},
    {"id": "g2_q2", "text": "¿Tiene claridad en sus responsabilidades laborales?", "text_en": "Do you have clarity in your job responsibilities?"}
]

GUIDE3_QUESTIONS = [
    {"id": "g3_q1", "text": "¿Recibe reconocimiento por su trabajo?", "text_en": "Do you receive recognition for your work?"},
    {"id": "g3_q2", "text": "¿Siente que hay un ambiente de respeto en su trabajo?", "text_en": "Do you feel there is a respectful environment at work?"}
]

# Password hashing for secure log download
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Predefined hashed password (replace with your own)
CORRECT_PASSWORD_HASH = hash_password("securepassword123")  # Change this in production

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
    .stButton>button {background-color: #4CAF50; color: white; border-radius: 8px;}
    .stProgress .st-bo {background-color: #4CAF50;}
    .question {font-size: 18px; margin-bottom: 10px;}
    .tooltip {color: #555; font-size: 14px;}
    .section-header {font-size: 20px; font-weight: bold; margin-top: 20px;}
    </style>
""", unsafe_allow_html=True)

# Language selector
lang = st.sidebar.selectbox("Language / Idioma", ["Español", "English"])
lang_code = "es" if lang == "Español" else "en"
t = LANGUAGES[lang_code]

# Main app
st.title(t["title"])
st.write(t["welcome"])

# Progress bar
total_questions = len(GUIDE1_QUESTIONS)
if st.session_state.has_trauma:
    total_questions += len(GUIDE2_QUESTIONS) + len(GUIDE3_QUESTIONS)
answered_questions = len(st.session_state.responses)
progress = answered_questions / total_questions if total_questions > 0 else 0
st.progress(progress)
st.write(f"{t['progress']}: {int(progress * 100)}%")

# Guía I: Acontecimientos Traumáticos Severos
if not st.session_state.guide1_complete:
    st.header(t["guide1"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide1']}</p>", unsafe_allow_html=True)
    
    # Personal Information Section
    st.markdown(f"<p class='section-header'>{t['personal_info']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[:7]:  # Questions 1-7
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        if q["type"] == "text_group":
            for subfield in q["subfields"]:
                response = st.text_input(
                    subfield["label" if lang_code == "es" else "label_en"], 
                    key=subfield["id"]
                )
                st.session_state.responses[subfield["id"]] = response
        elif q["type"] == "number":
            response = st.number_input(
                "", min_value=0, step=1, key=q["id"], 
                format="%d"
            )
            st.session_state.responses[q["id"]] = response
        elif q["type"] == "select":
            response = st.selectbox(
                "", q["options" if lang_code == "es" else "options_en"], 
                key=q["id"], label_visibility="collapsed"
            )
            st.session_state.responses[q["id"]] = response
    
    # Traumatic Events Section
    st.markdown(f"<p class='section-header'>{t['next_section']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[7:13]:  # Questions 8-13
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    # Persistent Memories Section
    st.markdown(f"<p class='section-header'>{t['persistent_memories']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[13:15]:  # Questions 14-15
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    # Avoidance Efforts Section
    st.markdown(f"<p class='section-header'>{t['avoidance_efforts']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[15:22]:  # Questions 16-22
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    # Affectation Section
    st.markdown(f"<p class='section-header'>{t['affectation']}</p>", unsafe_allow_html=True)
    for q in GUIDE1_QUESTIONS[22:]:  # Questions 23-27
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    if st.button(t["submit"], key="submit_guide1"):
        required_keys = [q["id"] for q in GUIDE1_QUESTIONS if q["type"] != "text_group"]
        required_keys += [subfield["id"] for q in GUIDE1_QUESTIONS if q["type"] == "text_group" for subfield in q["subfields"]]
        if all(key in st.session_state.responses for key in required_keys):
            st.session_state.guide1_complete = True
            st.success("Guía I completada / Guide I completed")
        else:
            st.error("Por favor responda todas las preguntas / Please answer all questions")

# Guía II: Factores de Riesgo Psicosocial (only if trauma detected)
if st.session_state.guide1_complete and st.session_state.has_trauma and not st.session_state.guide2_complete:
    st.header(t["guide2"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide2']}</p>", unsafe_allow_html=True)
    
    for q in GUIDE2_QUESTIONS:
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["always"], t["almost_always"], t["sometimes"], t["almost_never"], t["never"]], 
            key=q["id"], label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
    
    if st.button(t["submit"], key="submit_guide2"):
        if len(st.session_state.responses) >= len(GUIDE1_QUESTIONS) + len(GUIDE2_QUESTIONS):
            st.session_state.guide2_complete = True
            st.success("Guía II completada / Guide II completed")
        else:
            st.error("Por favor responda todas las preguntas / Please answer all questions")

# Guía III: Entorno Organizacional Favorable (only if trauma detected)
if st.session_state.guide2_complete and st.session_state.has_trauma and not st.session_state.guide3_complete:
    st.header(t["guide3"])
    st.markdown(f"<p class='tooltip'>{t['tooltip_guide3']}</p>", unsafe_allow_html=True)
    
    for q in GUIDE3_QUESTIONS:
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["always"], t["almost_always"], t["sometimes"], t["almost_never"], t["never"]], 
            key=q["id"], label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
    
    if st.button(t["submit"], key="submit_guide3"):
        if len(st.session_state.responses) >= len(GUIDE1_QUESTIONS) + len(GUIDE2_QUESTIONS) + len(GUIDE3_QUESTIONS):
            st.session_state.guide3_complete = True
            st.success("Guía III completada / Guide III completed")
        else:
            st.error("Por favor responda todas las preguntas / Please answer all questions")

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
    password = st.text_input(t["password_prompt"], type="password")
    if st.button("Descargar / Download"):
        if hash_password(password) == CORRECT_PASSWORD_HASH:
            df, timestamp = save_responses()
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="nom035_responses_{timestamp}.csv">Descargar CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.error(t["incorrect_password"])
