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
from enum import Enum
from dataclasses import dataclass

# --------------------------
# CONSTANTS & CONFIGURATION
# --------------------------

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ACCESS_KEY = os.getenv("NOM035_ACCESS_KEY")
RESET_PASSWORD = os.getenv("NOM035_RESET_PASSWORD")

# Constants
DB_FILE = "nom035.db"
MAX_TEXT_LENGTH = 100
MAX_IMAGE_WIDTH = 800
COLOR_PRIMARY = "#3498db"
COLOR_SECONDARY = "#2ecc71"
COLOR_DANGER = "#e74c3c"
COLOR_WARNING = "#f39c12"
COLOR_SUCCESS = "#2ecc71"
FONT_FAMILY = "Arial, sans-serif"

# --------------------------
# DATA MODELS
# --------------------------

class GuideType(Enum):
    GUIA_I = "guia_i"
    GUIA_II = "guia_ii"
    GUIA_III = "guia_iii"
    GUIA_IV = "guia_iv"

@dataclass
class Question:
    text: str
    input_type: str
    options: Optional[List[str]] = None
    required: bool = True

@dataclass
class Section:
    title: str
    questions: List[Question]
    description: Optional[str] = None

# --------------------------
# UI COMPONENTS
# --------------------------

def setup_page_config():
    """Configure Streamlit page settings with custom styling."""
    st.set_page_config(
        page_title="🧠 Evaluación Psicosocial NOM-035",
        page_icon="🧠",
        layout="centered",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown(f"""
        <style>
            .stApp {{
                font-family: {FONT_FAMILY};
            }}
            .stProgress > div > div > div {{
                background-color: {COLOR_PRIMARY};
            }}
            .st-bb {{
                background-color: {COLOR_PRIMARY};
            }}
            .st-at {{
                background-color: {COLOR_PRIMARY};
            }}
            .st-eb {{
                border-color: {COLOR_PRIMARY};
            }}
            .section-header {{
                color: {COLOR_PRIMARY};
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 1rem;
            }}
            .question-text {{
                font-weight: 600;
                margin-bottom: 0.5rem;
            }}
            .success-box {{
                background-color: #d4edda;
                color: #155724;
                padding: 1rem;
                border-radius: 0.25rem;
                margin: 1rem 0;
            }}
            .warning-box {{
                background-color: #fff3cd;
                color: #856404;
                padding: 1rem;
                border-radius: 0.25rem;
                margin: 1rem 0;
            }}
            .error-box {{
                background-color: #f8d7da;
                color: #721c24;
                padding: 1rem;
                border-radius: 0.25rem;
                margin: 1rem 0;
            }}
            .card {{
                border: 1px solid #dee2e6;
                border-radius: 0.25rem;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
            }}
        </style>
    """, unsafe_allow_html=True)

def render_progress_bar(current_step: GuideType):
    """Render a visual progress bar with step indicators."""
    steps = {
        GuideType.GUIA_I: {"label": "Guía I", "description": "Información básica y eventos traumáticos"},
        GuideType.GUIA_II: {"label": "Guía II", "description": "Factores de riesgo psicosocial"},
        GuideType.GUIA_III: {"label": "Guía III", "description": "Entorno organizacional"},
        GuideType.GUIA_IV: {"label": "Guía IV", "description": "Síntomas de salud"}
    }
    
    step_order = [GuideType.GUIA_I, GuideType.GUIA_II, GuideType.GUIA_III, GuideType.GUIA_IV]
    current_index = step_order.index(current_step)
    
    # Progress bar
    progress = (current_index + 1) / len(step_order)
    st.progress(progress)
    
    # Step indicators
    cols = st.columns(len(step_order))
    for i, step in enumerate(step_order):
        with cols[i]:
            is_current = current_step == step
            is_completed = i < current_index
            status = "✅" if is_completed else "➡️" if is_current else "🔘"
            st.markdown(f"""
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem;">{status}</div>
                    <div style="font-weight: {'bold' if is_current else 'normal'}">
                        {steps[step]['label']}
                    </div>
                    <div style="font-size: 0.8rem; color: #666;">
                        {steps[step]['description']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

def render_question(question: Question, key: str):
    """Render a single question with appropriate input type."""
    st.markdown(f'<div class="question-text">{question.text}</div>', unsafe_allow_html=True)
    
    if question.input_type == "text":
        return st.text_input("", key=key, max_chars=MAX_TEXT_LENGTH, label_visibility="collapsed")
    elif question.input_type == "number":
        return st.number_input("", min_value=0, step=1, key=key, label_visibility="collapsed")
    elif question.input_type == "radio" and question.options:
        return st.radio("", question.options, horizontal=True, key=key, label_visibility="collapsed")
    elif question.input_type == "select" and question.options:
        return st.selectbox("", question.options, key=key, label_visibility="collapsed")
    return None

def render_section(section: Section, responses: Dict[str, Any], prefix: str = ""):
    """Render a section of questions with expandable container."""
    with st.expander(section.title, expanded=True):
        if section.description:
            st.markdown(f"*{section.description}*")
        
        for i, question in enumerate(section.questions):
            key = f"{prefix}_q{i}_{question.text[:20]}"
            responses[question.text] = render_question(question, key)

def show_success(message: str):
    """Show a success message with consistent styling."""
    st.markdown(f'<div class="success-box">✅ {message}</div>', unsafe_allow_html=True)

def show_warning(message: str):
    """Show a warning message with consistent styling."""
    st.markdown(f'<div class="warning-box">⚠️ {message}</div>', unsafe_allow_html=True)

def show_error(message: str):
    """Show an error message with consistent styling."""
    st.markdown(f'<div class="error-box">❌ {message}</div>', unsafe_allow_html=True)

# --------------------------
# DATA MANAGEMENT
# --------------------------

class DatabaseManager:
    """Handles all database operations with proper connection management."""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self._ensure_db_directory()
        self._init_db()
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists and is writable."""
        db_dir = os.path.dirname(self.db_file) or '.'
        os.makedirs(db_dir, exist_ok=True)
        if not os.access(db_dir, os.W_OK):
            raise PermissionError(f"No write permission for database directory: {db_dir}")
    
    def _init_db(self):
        """Initialize the database with required tables."""
        with self._get_connection() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                nombre TEXT,
                apellido_paterno TEXT,
                apellido_materno TEXT,
                data TEXT
            )''')
            conn.commit()
    
    def _get_connection(self):
        """Get a database connection with error handling."""
        try:
            return sqlite3.connect(self.db_file)
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def log_response(self, response_data: Dict[str, Any], response_id: Optional[int] = None) -> Optional[int]:
        """Log a response to the database."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Prepare data for storage
                log_data = {
                    'Timestamp': timestamp,
                    'Nombre': hash_sensitive_data(response_data.get('Nombre', '')),
                    'Apellido Paterno': hash_sensitive_data(response_data.get('Apellido Paterno', '')),
                    'Apellido Materno': hash_sensitive_data(response_data.get('Apellido Materno', '')),
                    **{k: v for k, v in response_data.items() 
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
                
        except Exception as e:
            logger.error(f"Error logging response: {str(e)}")
            show_error(f"Error al guardar la respuesta: {str(e)}")
            return None
    
    def load_responses(self) -> pd.DataFrame:
        """Load all responses from the database."""
        try:
            with self._get_connection() as conn:
                df = pd.read_sql('SELECT data FROM responses', conn)
                if not df.empty:
                    df['data'] = df['data'].apply(eval)  # Convert stringified dict to dict
                    return pd.json_normalize(df['data'])
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading responses: {str(e)}")
            show_error(f"Error al cargar respuestas: {str(e)}")
            return pd.DataFrame()
    
    def reset_data(self, password: str) -> bool:
        """Reset all data in the database."""
        if password != RESET_PASSWORD:
            show_error("Contraseña incorrecta para reiniciar datos.")
            return False
            
        try:
            with self._get_connection() as conn:
                conn.execute('DELETE FROM responses')
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error resetting data: {str(e)}")
            show_error(f"Error al reiniciar datos: {str(e)}")
            return False

# --------------------------
# APPLICATION LOGIC
# --------------------------

class NOM035Assessment:
    """Main application class for NOM-035 assessment."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.session = st.session_state
        
        # Initialize session state
        if 'current_step' not in self.session:
            self.session.current_step = GuideType.GUIA_I
        if 'responses' not in self.session:
            self.session.responses = {}
        if 'response_id' not in self.session:
            self.session.response_id = None
    
    def get_guia_i_sections(self) -> List[Section]:
        """Return Guía I sections with questions."""
        return [
            Section(
                title="Información Personal",
                description="Información básica del empleado",
                questions=[
                    Question("Nombre", "text"),
                    Question("Apellido Paterno", "text"),
                    Question("Apellido Materno", "text"),
                    Question("¿Qué edad tienes? (ej. 21)", "number"),
                    Question("¿Cuál es tu género?", "radio", ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"]),
                    Question("¿Cuántos años llevas trabajando aquí?", "number"),
                    Question("¿En qué departamento labora?", "select", 
                            ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", 
                             "Producción", "Recursos Humanos", "Ventas y Marketing", 
                             "Contabilidad y Finanzas", "Administración"]),
                    Question("¿Cuál es su función?", "select", 
                            ["Operador", "Técnico", "Ingeniero", "Analista", 
                             "Supervisor", "Gerente", "Director"]),
                    Question("¿Dónde se encuentra su lugar de trabajo?", "radio", 
                            ["Planta 1", "Planta 2", "Planta 3"]),
                ]
            ),
            # ... other sections for Guía I
        ]
    
    def render_guia_i(self):
        """Render the Guía I assessment form."""
        st.markdown('<div class="section-header">Guía I: Información Básica y Eventos Traumáticos</div>', 
                   unsafe_allow_html=True)
        
        with st.form("guia_i_form"):
            responses = {}
            for section in self.get_guia_i_sections():
                render_section(section, responses, "gi")
            
            if st.form_submit_button("📤 Enviar Guía I", use_container_width=True):
                self.handle_guia_i_submission(responses)
    
    def handle_guia_i_submission(self, responses: Dict[str, Any]):
        """Process Guía I form submission."""
        # Validate all required questions are answered
        required_questions = [q.text for section in self.get_guia_i_sections() 
                            for q in section.questions if q.required]
        missing = [q for q in required_questions if q not in responses or not responses[q]]
        
        if missing:
            show_warning(f"Por favor responde todas las preguntas requeridas. Faltan: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
            return
        
        # Validate numeric fields
        numeric_fields = ["¿Qué edad tienes? (ej. 21)", "¿Cuántos años llevas trabajando aquí?"]
        for field in numeric_fields:
            if not validate_number(responses.get(field)):
                show_warning(f"El campo {field} debe ser un número entero positivo")
                return
        
        # Save responses
        response_id = self.db.log_response(responses, self.session.response_id)
        if not response_id:
            return
        
        # Update session state
        self.session.responses = responses
        self.session.response_id = response_id
        
        # Determine next step
        has_positive = any(responses.get(q.text) == "Sí" 
                          for section in self.get_guia_i_sections()[1:]  # Skip personal info section
                          for q in section.questions)
        
        if has_positive:
            self.session.current_step = GuideType.GUIA_II
            show_success("Guía I completada. Por favor continúa con la Guía II.")
            st.experimental_rerun()
        else:
            self.reset_session()
            show_success("¡Evaluación completada! No se requiere la Guía II.")
    
    def reset_session(self):
        """Reset the session state after completion."""
        self.session.current_step = GuideType.GUIA_I
        self.session.responses = {}
        self.session.response_id = None
    
    def render_current_step(self):
        """Render the current assessment step based on session state."""
        render_progress_bar(self.session.current_step)
        
        if self.session.current_step == GuideType.GUIA_I:
            self.render_guia_i()
        elif self.session.current_step == GuideType.GUIA_II:
            self.render_guia_ii()
        elif self.session.current_step == GuideType.GUIA_III:
            self.render_guia_iii()
        elif self.session.current_step == GuideType.GUIA_IV:
            self.render_guia_iv()
    
    def render_report_section(self):
        """Render the report generation section."""
        st.markdown('<div class="section-header">📊 Reporte Consolidado</div>', 
                   unsafe_allow_html=True)
        
        with st.expander("🔐 Acceso a Reportes", expanded=True):
            access_key = st.text_input("Ingrese la clave de acceso:", type="password")
            
            if access_key == ACCESS_KEY:
                self.generate_and_download_report()
            elif access_key:  # Only show warning if they actually tried to enter something
                show_warning("Clave de acceso incorrecta")
    
    def generate_and_download_report(self):
        """Generate and download the assessment report."""
        df = self.db.load_responses()
        if df.empty:
            show_warning("No hay respuestas disponibles para generar el reporte.")
            return
        
        try:
            with st.spinner("Generando reporte..."):
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Generate analysis and visualizations
                    analysis_results = self.generate_analysis(df)
                    visualizations = self.generate_visualizations(df, temp_dir, analysis_results)
                    
                    # Generate Excel report
                    excel_buffer = self.generate_excel_report(df, analysis_results, visualizations)
                    
                    # Download button
                    st.download_button(
                        label="📥 Descargar Reporte Completo",
                        data=excel_buffer,
                        file_name=f"Reporte_NOM035_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    show_success("Reporte generado exitosamente")
        
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            show_error(f"Error al generar el reporte: {str(e)}")

# --------------------------
# MAIN APPLICATION
# --------------------------

def main():
    """Main application entry point."""
    setup_page_config()
    
    # Initialize application
    app = NOM035Assessment()
    
    # Sidebar navigation
    with st.sidebar:
        st.image("assets/FOBO2.png", width=120)
        st.title("Evaluación NOM-035")
        
        nav_option = st.radio(
            "Navegación",
            ["📋 Evaluación", "📊 Reportes", "⚙️ Administración"],
            label_visibility="collapsed"
        )
    
    # Main content area
    if nav_option == "📋 Evaluación":
        app.render_current_step()
    elif nav_option == "📊 Reportes":
        app.render_report_section()
    elif nav_option == "⚙️ Administración":
        render_admin_section(app.db)

def render_admin_section(db: DatabaseManager):
    """Render the administration section."""
    st.markdown('<div class="section-header">⚙️ Administración</div>', 
               unsafe_allow_html=True)
    
    with st.expander("🔄 Reiniciar Datos", expanded=False):
        st.warning("Esta acción eliminará todos los datos existentes. Use con precaución.")
        password = st.text_input("Contraseña de administrador:", type="password")
        
        if st.button("Reiniciar Todos los Datos", type="secondary"):
            if db.reset_data(password):
                show_success("Todos los datos han sido reiniciados exitosamente")
            else:
                show_error("No se pudieron reiniciar los datos")

if __name__ == "__main__":
    if not ACCESS_KEY or not RESET_PASSWORD:
        show_error("Error de configuración: Las variables de entorno NOM035_ACCESS_KEY y NOM035_RESET_PASSWORD deben estar configuradas")
        st.stop()
    
    main()
