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
import filelock
import logging
from typing import Dict, List, Tuple, Optional, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ACCESS_KEY = os.getenv("NOM035_ACCESS_KEY")
RESET_PASSWORD = os.getenv("NOM035_RESET_PASSWORD")
if not ACCESS_KEY or not RESET_PASSWORD:
    raise ValueError("Environment variables NOM035_ACCESS_KEY and NOM035_RESET_PASSWORD must be set")

# Constants
DB_FILE = "nom035.db"
MAX_TEXT_LENGTH = 100
SCORE_MAP = {
    "Siempre": 4, 
    "Casi siempre": 3, 
    "A veces": 2, 
    "Casi nunca": 1, 
    "Nunca": 0
}
REVERSE_QUESTIONS = [
    "¿Trabaja horas extras con frecuencia?",
    "¿Las demandas del trabajo interfieren con su vida personal?",
    "¿Ha recibido gritos, insultos o burlas en el trabajo?",
    "¿Ha sido discriminado por su género, edad u otra característica?",
    "¿Ha recibido amenazas o intimidaciones en el trabajo?",
    "¿Ha sido ignorado o excluido por sus compañeros o jefes?",
    "¿Ha recibido tratos humillantes en el trabajo?"
]

# Database setup
def init_db() -> None:
    """Initialize SQLite database with proper error handling."""
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
    page_title="🧠 NOM-035 Guía I, II, III y IV", 
    layout="centered",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "current_step" not in st.session_state:
    st.session_state.current_step = "guia_i"
if "guia_i_responses" not in st.session_state:
    st.session_state.guia_i_responses = None
if "guia_ii_responses" not in st.session_state:
    st.session_state.guia_ii_responses = None
if "response_id" not in st.session_state:
    st.session_state.response_id = None

def sanitize_text(text: str) -> str:
    """Sanitize text inputs with length and character restrictions."""
    if not text:
        return ""
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Input exceeds maximum length of {MAX_TEXT_LENGTH} characters")
    return re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ]', '', text.strip())

def validate_number(value: Union[str, int, float], min_value: int = 0) -> bool:
    """Validate numeric input is integer >= min_value."""
    try:
        num = int(value)
        return num >= min_value
    except (ValueError, TypeError):
        return False

def hash_sensitive_data(text: str) -> str:
    """Hash sensitive data using SHA-256."""
    if not text:
        return ""
    return hashlib.sha256(text.encode()).hexdigest()

def validate_questions(responses: Dict[str, Any], expected_questions: List[str]) -> Tuple[bool, List[str]]:
    """Validate all required questions are answered."""
    missing = [
        q for q in expected_questions 
        if q not in responses or 
        responses[q] is None or 
        responses[q] == ""
    ]
    return (not missing, missing)

def log_response(response: Dict[str, Any], response_id: Optional[int] = None) -> Optional[int]:
    """Log response to SQLite database with transaction handling."""
    conn = None
    try:
        if not os.access(os.path.dirname(DB_FILE) or '.', os.W_OK):
            raise PermissionError("No write permission for database directory")
            
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare data for storage
        log_data = {
            'Timestamp': timestamp,
            'Nombre': hash_sensitive_data(response.get('Nombre', '')),
            'Apellido Paterno': hash_sensitive_data(response.get('Apellido Paterno', '')),
            'Apellido Materno': hash_sensitive_data(response.get('Apellido Materno', '')),
            **{k: v for k, v in response.items() 
               if k not in ['Nombre', 'Apellido Paterno', 'Apellido Materno']}
        }
        
        if response_id:  # Update existing record
            c.execute('''UPDATE responses 
                      SET timestamp=?, nombre=?, apellido_paterno=?, apellido_materno=?, data=?
                      WHERE id=?''',
                      (timestamp, log_data['Nombre'], log_data['Apellido Paterno'], 
                       log_data['Apellido Materno'], str(log_data), response_id))
        else:  # Insert new record
            c.execute('''INSERT INTO responses 
                      (timestamp, nombre, apellido_paterno, apellido_materno, data) 
                      VALUES (?, ?, ?, ?, ?)''',
                      (timestamp, log_data['Nombre'], log_data['Apellido Paterno'], 
                       log_data['Apellido Materno'], str(log_data)))
            response_id = c.lastrowid
            
        conn.commit()
        return response_id
        
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        st.error("❌ Error: No se puede acceder a la base de datos. Contacte al administrador.")
        return None
    except Exception as e:
        logger.error(f"Error logging response: {str(e)}")
        st.error(f"❌ Error al guardar la respuesta: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def reset_data(password: str) -> None:
    """Reset session state and clear database with proper validation."""
    if password != RESET_PASSWORD:
        st.error("🔐 Contraseña incorrecta para reiniciar datos.")
        return
        
    conn = None
    try:
        if not os.access(os.path.dirname(DB_FILE) or '.', os.W_OK):
            raise PermissionError("No write permission for database directory")
            
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DELETE FROM responses')
        conn.commit()
        
        # Reset session state
        st.session_state.current_step = "guia_i"
        st.session_state.guia_i_responses = None
        st.session_state.guia_ii_responses = None
        st.session_state.response_id = None
        
        st.success("✅ Datos reiniciados exitosamente.")
        
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        st.error("❌ Error: No se puede acceder a la base de datos. Contacte al administrador.")
    except Exception as e:
        logger.error(f"Error resetting data: {str(e)}")
        st.error(f"❌ Error al reiniciar datos: {str(e)}")
    finally:
        if conn:
            conn.close()

# Question definitions (moved to separate functions for better organization)
def get_guia_i_questions() -> List[Dict[str, Any]]:
    """Return Guía I question structure."""
    return [
        {
            "section": "Información Personal",
            "items": [
                ("Nombre", "text"),
                ("Apellido Paterno", "text"),
                ("Apellido Materno", "text"),
                ("¿Qué edad tienes? (ej. 21)", "number"),
                ("¿Cuál es tu género?", ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"]),
                ("¿Cuántos años llevas trabajando aquí?", "number"),
                ("¿En qué departamento labora?", ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"]),
                ("¿Cuál es su función?", ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"]),
                ("¿Dónde se encuentra su lugar de trabajo?", ["Planta 1", "Planta 2", "Planta 3"]),
            ]
        },
        # ... (rest of Guía I questions)
    ]

def load_responses() -> pd.DataFrame:
    """Load all responses from database with error handling."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql('SELECT data FROM responses', conn)
        if not df.empty:
            df['data'] = df['data'].apply(eval)  # Convert stringified dict to dict
            return pd.json_normalize(df['data'])
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error loading responses: {str(e)}")
        st.error(f"❌ Error al cargar respuestas: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def calculate_risk_score_guia_ii(
    df: pd.DataFrame, 
    guia_ii_cols: List[str], 
    domain_questions: Dict[str, List[str]]
) -> Tuple[pd.Series, pd.Series, Dict[str, pd.Series], Dict[str, pd.Series]]:
    """Calculate Guía II risk scores with vectorized operations."""
    # Create a scoring DataFrame
    score_df = pd.DataFrame(index=df.index)
    
    for col in guia_ii_cols:
        if col in df.columns:
            score_df[col] = df[col].map(SCORE_MAP).fillna(0)
            if col in REVERSE_QUESTIONS:
                score_df[col] = 4 - score_df[col]
    
    # Calculate total scores
    total_scores = score_df.sum(axis=1)
    total_risk = pd.cut(
        total_scores,
        bins=[-1, 49, 74, 99, 124, float('inf')],
        labels=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"],
        include_lowest=True
    )
    
    # Calculate domain scores
    domain_scores = {}
    domain_risk_levels = {}
    
    for domain, questions in domain_questions.items():
        domain_cols = [q for q in questions if q in score_df.columns]
        if domain_cols:
            domain_scores[domain] = score_df[domain_cols].sum(axis=1)
            max_score = len(domain_cols) * 4
            percentage = (domain_scores[domain] / max_score) * 100
            domain_risk_levels[domain] = pd.cut(
                percentage,
                bins=[-1, 19, 39, 59, 79, float('inf')],
                labels=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"],
                include_lowest=True
            )
    
    return total_scores, total_risk, domain_scores, domain_risk_levels

# ... (similar optimizations for other calculation functions)

def generate_excel_report(
    df: pd.DataFrame,
    guia_i_analysis: Dict[str, Any],
    guia_ii_analysis: Dict[str, Any],
    guia_iii_analysis: Dict[str, Any],
    guia_iv_analysis: Dict[str, Any],
    visualizations: List[Tuple[str, str, str]],
    recommendations: List[str]
) -> io.BytesIO:
    """Generate Excel report in memory."""
    wb = Workbook()
    
    # Summary sheet
    ws_summary = wb.active
    ws_summary.title = "Resumen Ejecutivo"
    
    # Add content to sheets...
    
    # Save to in-memory buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# Main application logic
def render_guia_i_form() -> None:
    """Render Guía I form and handle submission."""
    with st.form("guia_i_form"):
        respuestas = {}
        for section_data in get_guia_i_questions():
            with st.expander(section_data["section"], expanded=True):
                for idx, (q, tipo) in enumerate(section_data["items"]):
                    st.markdown(f"**{q}**")
                    try:
                        if tipo == "text":
                            respuestas[q] = sanitize_text(
                                st.text_input("", key=f"gi_q{idx}_{q}", max_chars=MAX_TEXT_LENGTH)
                            )
                        elif tipo == "number":
                            respuestas[q] = st.number_input(
                                "", min_value=0, step=1, key=f"gi_q{idx}_{q}"
                            )
                        elif isinstance(tipo, list):
                            respuestas[q] = st.radio(
                                "", tipo, horizontal=True, key=f"gi_q{idx}_{q}"
                            )
                    except ValueError as e:
                        st.error(f"❌ Error en {q}: {str(e)}")

        if st.form_submit_button("✅ Enviar Guía I"):
            handle_guia_i_submission(respuestas)

def handle_guia_i_submission(responses: Dict[str, Any]) -> None:
    """Process Guía I form submission."""
    expected_questions = [item[0] for section in get_guia_i_questions() for item in section["items"]]
    is_valid, missing = validate_questions(responses, expected_questions)
    
    if not is_valid:
        st.warning(f"⚠️ Responde todas las preguntas antes de enviar. Faltan: {', '.join(missing)}")
        return
        
    if not validate_number(responses.get("¿Qué edad tienes? (ej. 21)")) or \
       not validate_number(responses.get("¿Cuántos años llevas trabajando aquí?")):
        st.warning("⚠️ Los valores numéricos deben ser enteros mayores o iguales a 0.")
        return
        
    response_id = log_response(responses)
    if not response_id:
        return
        
    st.session_state.guia_i_responses = responses
    st.session_state.response_id = response_id
    
    symptom_cols = [q["items"][0][0] for q in get_guia_i_questions()[1:]]
    has_positive = any(responses.get(col) == "Sí" for col in symptom_cols)
    
    if has_positive:
        st.session_state.current_step = "guia_ii"
        st.success("✅ Guía I enviada. Por favor complete la Guía II.")
    else:
        st.session_state.current_step = "guia_i"
        st.session_state.guia_i_responses = None
        st.session_state.response_id = None
        st.success("✅ ¡Evaluación Guía I completada! No se requiere Guía II.")

# Similar functions for other guides...

def main() -> None:
    """Main application entry point."""
    # Sidebar navigation
    st.sidebar.image("assets/FOBO2.png", width=100)
    st.sidebar.title("Evaluación NOM-035")
    section = st.sidebar.radio(
        "Ir a sección:", 
        ["📋 Evaluación", "📥 Descargar Reporte", "🔄 Reiniciar Datos"]
    )

    if section == "📋 Evaluación":
        render_evaluation_section()
    elif section == "📥 Descargar Reporte":
        render_report_section()
    elif section == "🔄 Reiniciar Datos":
        render_reset_section()

def render_evaluation_section() -> None:
    """Render the evaluation section based on current step."""
    st.title("🧠 Evaluación Psicosocial - NOM-035 Guía I, II, III y IV")
    st.markdown("Por favor responda con honestidad. La información será confidencial.")
    
    # Progress indicator
    steps = ["Guía I", "Guía II", "Guía III", "Guía IV"]
    step_mapping = {
        "guia_i": 0, 
        "guia_ii": 1, 
        "guia_iii": 2, 
        "guia_iv": 3
    }
    current_idx = step_mapping.get(st.session_state.current_step, 0)
    
    st.progress((current_idx + 1) / len(steps))
    st.write(f"Paso {current_idx + 1} de {len(steps)}: {steps[current_idx]}")
    
    if st.session_state.current_step == "guia_i":
        render_guia_i_form()
    elif st.session_state.current_step == "guia_ii":
        render_guia_ii_form()
    elif st.session_state.current_step == "guia_iii":
        render_guia_iii_form()
    elif st.session_state.current_step == "guia_iv":
        render_guia_iv_form()

def render_report_section() -> None:
    """Render the report generation section."""
    st.title("📥 Reporte Consolidado")
    access_key = st.text_input("🔑 Ingrese la clave de acceso:", type="password")
    
    if access_key != ACCESS_KEY:
        st.warning("🔐 Clave de acceso incorrecta")
        return
        
    df = load_responses()
    if df.empty:
        st.warning("⚠️ No hay respuestas disponibles para generar el reporte.")
        return
        
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Perform analysis
            guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis, df = (
                generate_statistical_analysis(df)
            )
            
            # Generate visualizations
            visualizations = generate_visualizations(
                df, temp_dir, 
                guia_i_analysis, guia_ii_analysis, 
                guia_iii_analysis, guia_iv_analysis
            )
            
            # Generate recommendations
            recommendations = generate_recommendations(
                guia_i_analysis, guia_ii_analysis, 
                guia_iii_analysis, guia_iv_analysis
            )
            
            # Generate Excel report
            excel_buffer = generate_excel_report(
                df,
                guia_i_analysis,
                guia_ii_analysis,
                guia_iii_analysis,
                guia_iv_analysis,
                visualizations,
                recommendations
            )
            
            # Download button
            st.download_button(
                label="📥 Descargar Reporte Excel",
                data=excel_buffer,
                file_name=f"Reporte_NOM035_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("✅ Reporte generado exitosamente.")
            
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        st.error(f"❌ Error al generar el reporte: {str(e)}")

def render_reset_section() -> None:
    """Render the data reset section."""
    st.title("🔄 Reiniciar Datos")
    password = st.text_input("🔐 Ingrese la contraseña de administrador:", type="password")
    if st.button("Reiniciar Datos"):
        reset_data(password)

if __name__ == "__main__":
    main()
