import streamlit as st
import pandas as pd
import io
import sqlite3
import os
import tempfile
import numpy as np
from datetime import datetime
import hashlib
import re
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.drawing.image import Image
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ACCESS_KEY = os.getenv("NOM035_ACCESS_KEY")
RESET_PASSWORD = os.getenv("NOM035_RESET_PASSWORD")
if not ACCESS_KEY or not RESET_PASSWORD:
    st.error("""
    **Configuration Error**  
    Please set these environment variables:
    - `NOM035_ACCESS_KEY` for report access
    - `NOM035_RESET_PASSWORD` for admin functions
    
    For local development, create a `.env` file.
    In production, configure them in your hosting platform's settings.
    """)
    st.stop()

# Database setup
DB_FILE = "nom035.db"

def init_db():
    """Initialize SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            nombre TEXT,
            apellido_paterno TEXT,
            apellido_materno TEXT,
            data TEXT
        )''')
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

# Initialize database
init_db()

# Streamlit page configuration
st.set_page_config(
    page_title="🧠 NOM-035 Guía I-IV",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for better buttons
st.markdown("""
    <style>
        div.stButton > button:first-child {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            width: 100%;
        }
        div.stButton > button:first-child:hover {
            background-color: #45a049;
        }
        .secondary-button {
            background-color: #f0f0f0 !important;
            color: #333 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "current_step" not in st.session_state:
    st.session_state.current_step = "guia_i"
if "guia_i_responses" not in st.session_state:
    st.session_state.guia_i_responses = None
if "guia_ii_responses" not in st.session_state:
    st.session_state.guia_ii_responses = None
if "guia_iii_responses" not in st.session_state:
    st.session_state.guia_iii_responses = None
if "response_id" not in st.session_state:
    st.session_state.response_id = None

def sanitize_text(text):
    """Sanitize text inputs."""
    if not text:
        return ""
    if len(text) > 100:
        raise ValueError("Input exceeds maximum length of 100 characters")
    return re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ]', '', text.strip())

def validate_number(value, min_value=0):
    """Validate numeric input."""
    try:
        num = int(value)
        return num >= min_value
    except (ValueError, TypeError):
        return False

def hash_sensitive_data(text):
    """Hash sensitive data for storage."""
    return hashlib.sha256(text.encode()).hexdigest() if text else ""

def validate_questions(responses, expected_questions):
    """Validate all required questions are answered."""
    missing = [q for q in expected_questions if q not in responses or not responses[q]]
    return (not missing, missing)

def log_response(response, response_id=None):
    """Log response to SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_data = {
            'Timestamp': timestamp,
            'Nombre': hash_sensitive_data(response.get('Nombre', '')),
            'Apellido Paterno': hash_sensitive_data(response.get('Apellido Paterno', '')),
            'Apellido Materno': hash_sensitive_data(response.get('Apellido Materno', '')),
            **{k: v for k, v in response.items() 
               if k not in ['Nombre', 'Apellido Paterno', 'Apellido Materno']}
        }
        
        if response_id:
            c.execute('''UPDATE responses 
                      SET timestamp=?, nombre=?, apellido_paterno=?, apellido_materno=?, data=?
                      WHERE id=?''',
                      (timestamp, log_data['Nombre'], log_data['Apellido Paterno'], 
                       log_data['Apellido Materno'], str(log_data), response_id))
        else:
            c.execute('''INSERT INTO responses 
                      (timestamp, nombre, apellido_paterno, apellido_materno, data) 
                      VALUES (?, ?, ?, ?, ?)''',
                      (timestamp, log_data['Nombre'], log_data['Apellido Paterno'], 
                       log_data['Apellido Materno'], str(log_data)))
            response_id = c.lastrowid
        
        conn.commit()
        return response_id
        
    except Exception as e:
        logger.error(f"Error logging response: {str(e)}")
        st.error(f"❌ Error al guardar la respuesta: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def reset_data(password):
    """Reset session state and clear database."""
    if password != RESET_PASSWORD:
        st.error("🔐 Contraseña incorrecta para reiniciar datos.")
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DELETE FROM responses')
        conn.commit()
        
        st.session_state.current_step = "guia_i"
        st.session_state.guia_i_responses = None
        st.session_state.guia_ii_responses = None
        st.session_state.guia_iii_responses = None
        st.session_state.response_id = None
        
        st.success("✅ Datos reiniciados exitosamente.")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting data: {str(e)}")
        st.error(f"❌ Error al reiniciar datos: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

# [Keep all your question definitions here - guia_i_questions, guia_ii_questions, etc.]

def render_guia_i():
    """Render Guía I form with improved navigation."""
    st.markdown("### Guía I: Información Básica y Eventos Traumáticos")
    
    with st.form("guia_i_form"):
        respuestas = {}
        for section_data in guia_i_questions:
            with st.expander(section_data["section"], expanded=True):
                for idx, (q, tipo) in enumerate(section_data["items"]):
                    st.markdown(f"**{q}**")
                    try:
                        if tipo == "text":
                            respuestas[q] = sanitize_text(
                                st.text_input("", key=f"gi_q{idx}_{q}", max_chars=100, label_visibility="collapsed")
                            )
                        elif tipo == "number":
                            respuestas[q] = st.number_input(
                                "", min_value=0, step=1, key=f"gi_q{idx}_{q}", label_visibility="collapsed"
                            )
                        elif isinstance(tipo, list):
                            respuestas[q] = st.radio(
                                "", tipo, horizontal=True, key=f"gi_q{idx}_{q}", label_visibility="collapsed"
                            )
                    except ValueError as e:
                        st.error(f"❌ Error en {q}: {str(e)}")

        col1, col2 = st.columns([1, 2])
        with col1:
            if st.form_submit_button("Continuar a Guía II →", type="primary"):
                handle_guia_i_submission(respuestas)
        with col2:
            if st.form_submit_button("Guardar y salir", type="secondary"):
                if log_response(respuestas, st.session_state.response_id):
                    st.success("Respuestas guardadas. Puede continuar más tarde.")

def handle_guia_i_submission(responses):
    """Process Guía I form submission."""
    expected_questions = [item[0] for section in guia_i_questions for item in section["items"]]
    is_valid, missing = validate_questions(responses, expected_questions)
    
    if not is_valid:
        st.warning(f"⚠️ Faltan preguntas requeridas: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
        return
        
    if not validate_number(responses.get("¿Qué edad tienes? (ej. 21)")) or \
       not validate_number(responses.get("¿Cuántos años llevas trabajando aquí?")):
        st.warning("⚠️ Los campos numéricos deben ser enteros positivos")
        return
        
    response_id = log_response(responses, st.session_state.response_id)
    if not response_id:
        return
        
    st.session_state.guia_i_responses = responses
    st.session_state.response_id = response_id
    st.session_state.current_step = "guia_ii"
    st.experimental_rerun()

def render_guia_ii():
    """Render Guía II form with improved navigation."""
    st.markdown("### Guía II: Factores de Riesgo Psicosocial")
    
    with st.form("guia_ii_form"):
        respuestas = st.session_state.guia_i_responses.copy()
        for section_data in guia_ii_questions:
            with st.expander(section_data["section"], expanded=True):
                for idx, (q, tipo) in enumerate(section_data["items"]):
                    st.markdown(f"**{q}**")
                    respuestas[q] = st.radio(
                        "", tipo, horizontal=True, key=f"gii_q{idx}_{q}", label_visibility="collapsed"
                    )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.form_submit_button("← Volver a Guía I", type="secondary"):
                st.session_state.current_step = "guia_i"
                st.experimental_rerun()
        with col2:
            if st.form_submit_button("Continuar a Guía III →", type="primary"):
                handle_guia_ii_submission(respuestas)
        with col3:
            if st.form_submit_button("Guardar y salir", type="secondary"):
                if log_response(respuestas, st.session_state.response_id):
                    st.success("Respuestas guardadas. Puede continuar más tarde.")

def handle_guia_ii_submission(responses):
    """Process Guía II form submission."""
    expected_questions = [item[0] for section in guia_ii_questions for item in section["items"]]
    is_valid, missing = validate_questions(responses, expected_questions)
    
    if not is_valid:
        st.warning(f"⚠️ Faltan preguntas requeridas: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
        return
        
    response_id = log_response(responses, st.session_state.response_id)
    if not response_id:
        return
        
    st.session_state.guia_ii_responses = responses
    st.session_state.response_id = response_id
    st.session_state.current_step = "guia_iii"
    st.experimental_rerun()

def render_guia_iii():
    """Render Guía III form with improved navigation."""
    st.markdown("### Guía III: Entorno Organizacional")
    
    with st.form("guia_iii_form"):
        respuestas = st.session_state.guia_ii_responses.copy()
        for section_data in guia_iii_questions:
            with st.expander(section_data["section"], expanded=True):
                for idx, (q, tipo) in enumerate(section_data["items"]):
                    st.markdown(f"**{q}**")
                    respuestas[q] = st.radio(
                        "", tipo, horizontal=True, key=f"giii_q{idx}_{q}", label_visibility="collapsed"
                    )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.form_submit_button("← Volver a Guía II", type="secondary"):
                st.session_state.current_step = "guia_ii"
                st.experimental_rerun()
        with col2:
            if st.form_submit_button("Continuar a Guía IV →", type="primary"):
                handle_guia_iii_submission(respuestas)
        with col3:
            if st.form_submit_button("Guardar y salir", type="secondary"):
                if log_response(respuestas, st.session_state.response_id):
                    st.success("Respuestas guardadas. Puede continuar más tarde.")

def handle_guia_iii_submission(responses):
    """Process Guía III form submission."""
    expected_questions = [item[0] for section in guia_iii_questions for item in section["items"]]
    is_valid, missing = validate_questions(responses, expected_questions)
    
    if not is_valid:
        st.warning(f"⚠️ Faltan preguntas requeridas: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
        return
        
    response_id = log_response(responses, st.session_state.response_id)
    if not response_id:
        return
        
    st.session_state.guia_iii_responses = responses
    st.session_state.response_id = response_id
    st.session_state.current_step = "guia_iv"
    st.experimental_rerun()

def render_guia_iv():
    """Render Guía IV form with improved navigation."""
    st.markdown("### Guía IV: Síntomas de Salud y Estrés")
    
    with st.form("guia_iv_form"):
        respuestas = st.session_state.guia_iii_responses.copy()
        for section_data in guia_iv_questions:
            with st.expander(section_data["section"], expanded=True):
                for idx, (q, tipo) in enumerate(section_data["items"]):
                    st.markdown(f"**{q}**")
                    respuestas[q] = st.radio(
                        "", tipo, horizontal=True, key=f"giv_q{idx}_{q}", label_visibility="collapsed"
                    )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.form_submit_button("← Volver a Guía III", type="secondary"):
                st.session_state.current_step = "guia_iii"
                st.experimental_rerun()
        with col2:
            if st.form_submit_button("Finalizar Evaluación", type="primary"):
                handle_guia_iv_submission(respuestas)
        with col3:
            if st.form_submit_button("Guardar y salir", type="secondary"):
                if log_response(respuestas, st.session_state.response_id):
                    st.success("Respuestas guardadas. Puede continuar más tarde.")

def handle_guia_iv_submission(responses):
    """Process Guía IV form submission."""
    expected_questions = [item[0] for section in guia_iv_questions for item in section["items"]]
    is_valid, missing = validate_questions(responses, expected_questions)
    
    if not is_valid:
        st.warning(f"⚠️ Faltan preguntas requeridas: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
        return
        
    if log_response(responses, st.session_state.response_id):
        # Reset session state
        st.session_state.current_step = "guia_i"
        st.session_state.guia_i_responses = None
        st.session_state.guia_ii_responses = None
        st.session_state.guia_iii_responses = None
        st.session_state.response_id = None
        
        st.success("🎉 ¡Evaluación completada exitosamente!")
        st.balloons()

# [Keep all your analysis functions here - load_responses(), calculate_risk_score_guia_ii(), etc.]

def main():
    """Main application flow."""
    # Sidebar navigation
    st.sidebar.image("assets/FOBO2.png", width=120)
    st.sidebar.title("Evaluación NOM-035")
    
    section = st.sidebar.radio(
        "Navegación",
        ["📋 Evaluación", "📊 Reportes", "⚙️ Administración"],
        label_visibility="collapsed"
    )
    
    # Main content
    if section == "📋 Evaluación":
        st.title("🧠 Evaluación Psicosocial NOM-035")
        
        # Progress tracker
        steps = ["Guía I", "Guía II", "Guía III", "Guía IV"]
        current_idx = {"guia_i": 0, "guia_ii": 1, "guia_iii": 2, "guia_iv": 3}.get(st.session_state.current_step, 0)
        
        st.progress((current_idx + 1)/len(steps))
        st.caption(f"Progreso: {current_idx + 1} de {len(steps)} pasos completados")
        
        # Render current step
        if st.session_state.current_step == "guia_i":
            render_guia_i()
        elif st.session_state.current_step == "guia_ii":
            render_guia_ii()
        elif st.session_state.current_step == "guia_iii":
            render_guia_iii()
        elif st.session_state.current_step == "guia_iv":
            render_guia_iv()
    
    elif section == "📊 Reportes":
        st.title("📊 Reportes y Análisis")
        access_key = st.text_input("🔑 Ingrese la clave de acceso:", type="password")
        
        if access_key == ACCESS_KEY:
            # [Add your report generation code here]
            st.success("Acceso concedido")
        else:
            st.warning("Clave de acceso incorrecta")
    
    elif section == "⚙️ Administración":
        st.title("⚙️ Administración")
        st.warning("Esta sección es solo para administradores")
        
        password = st.text_input("🔑 Contraseña de administrador:", type="password")
        if st.button("Reiniciar todos los datos", type="secondary"):
            if reset_data(password):
                st.experimental_rerun()

if __name__ == "__main__":
    main()
