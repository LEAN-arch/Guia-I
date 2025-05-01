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
        "tooltip_guide3": "Evalúe el entorno organizacional en su lugar de trabajo."
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
        "tooltip_guide3": "Assess the organizational environment in your workplace."
    }
}

# Sample questions (replace with full NOM-035 question sets from DOF)
GUIDE1_QUESTIONS = [
    {"id": "g1_q1", "text": "¿Ha experimentado un accidente grave en el trabajo?", "text_en": "Have you experienced a serious workplace accident?"},
    {"id": "g1_q2", "text": "¿Ha sido víctima de violencia laboral?", "text_en": "Have you been a victim of workplace violence?"}
]

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
    
    for q in GUIDE1_QUESTIONS:
        st.markdown(f"<p class='question'>{q['text' if lang_code == 'es' else 'text_en']}</p>", unsafe_allow_html=True)
        response = st.radio(
            "", [t["yes"], t["no"]], key=q["id"], 
            label_visibility="collapsed"
        )
        st.session_state.responses[q["id"]] = response
        if response == t["yes"]:
            st.session_state.has_trauma = True
    
    if st.button(t["submit"], key="submit_guide1"):
        if len(st.session_state.responses) >= len(GUIDE1_QUESTIONS):
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
