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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ACCESS_KEY = os.getenv("NOM035_ACCESS_KEY")
RESET_PASSWORD = os.getenv("NOM035_RESET_PASSWORD")
if not ACCESS_KEY or not RESET_PASSWORD:
    raise ValueError("Environment variables NOM035_ACCESS_KEY and NOM035_RESET_PASSWORD must be set")

# Database setup
DB_FILE = "nom035.db"

def init_db():
    """Initialize SQLite database."""
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
        conn.close()

# Initialize database
init_db()

# Streamlit page configuration
st.set_page_config(page_title="🧠 NOM-035 Guía I, II, III y IV", layout="centered")

# Initialize session state
if "current_step" not in st.session_state:
    st.session_state.current_step = "guia_i"
if "guia_i_responses" not in st.session_state:
    st.session_state.guia_i_responses = None
if "guia_ii_responses" not in st.session_state:
    st.session_state.guia_ii_responses = None
if "response_id" not in st.session_state:
    st.session_state.response_id = None
if "require_guia_iv" not in st.session_state:
    st.session_state.require_guia_iv = False

def sanitize_text(text):
    """Sanitize text inputs, limiting length and removing malicious characters."""
    if not text:
        return ""
    if len(text) > 100:
        raise ValueError("Input exceeds maximum length of 100 characters")
    return re.sub(r'[^\w\s]', '', text)

def validate_number(value, min_value=0):
    """Validate numeric input, ensuring it's an integer >= min_value."""
    try:
        num = float(value)
        if not num.is_integer() or num < min_value:
            return False
        return True
    except (TypeError, ValueError):
        return False

def hash_sensitive_data(text):
    """Hash sensitive data for storage."""
    return hashlib.sha256(text.encode()).hexdigest() if text else ""

def validate_questions(responses, expected_questions):
    """Validate that all required questions are answered."""
    missing = [q for q in expected_questions if q not in responses or responses[q] is None or responses[q] == ""]
    return not missing, missing

def log_response(response, response_id=None):
    """Log response to SQLite database."""
    try:
        if not os.access(os.path.dirname(DB_FILE) or '.', os.W_OK):
            raise PermissionError("No write permission for database directory")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_data = {
            'Timestamp': timestamp,
            'Nombre': hash_sensitive_data(response.get('Nombre')),
            'Apellido Paterno': hash_sensitive_data(response.get('Apellido Paterno')),
            'Apellido Materno': hash_sensitive_data(response.get('Apellido Materno')),
            **{k: v for k, v in response.items() if k not in ['Nombre', 'Apellido Paterno', 'Apellido Materno']}
        }
        data_str = str(log_data)
        if response_id:
            c.execute('UPDATE responses SET timestamp=?, nombre=?, apellido_paterno=?, apellido_materno=?, data=? WHERE id=?',
                      (timestamp, log_data['Nombre'], log_data['Apellido Paterno'], log_data['Apellido Materno'], data_str, response_id))
        else:
            c.execute('INSERT INTO responses (timestamp, nombre, apellido_paterno, apellido_materno, data) VALUES (?, ?, ?, ?, ?)',
                      (timestamp, log_data['Nombre'], log_data['Apellido Paterno'], log_data['Apellido Materno'], data_str))
            response_id = c.lastrowid
        conn.commit()
        return response_id
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        st.error(f"❌ Error: No se puede acceder a la base de datos. Contacte al administrador.")
        return None
    except Exception as e:
        logger.error(f"Error logging response: {str(e)}")
        st.error(f"❌ Error al guardar la respuesta: {str(e)}")
        return None
    finally:
        conn.close()

def reset_data(password):
    """Reset session state and clear database."""
    if password != RESET_PASSWORD:
        st.error("🔐 Contraseña incorrecta para reiniciar datos.")
        return
    try:
        if not os.access(os.path.dirname(DB_FILE) or '.', os.W_OK):
            raise PermissionError("No write permission for database directory")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DELETE FROM responses')
        conn.commit()
        st.session_state.current_step = "guia_i"
        st.session_state.guia_i_responses = None
        st.session_state.guia_ii_responses = None
        st.session_state.response_id = None
        st.session_state.require_guia_iv = False
        st.success("✅ Datos reiniciados exitosamente.")
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        st.error(f"❌ Error: No se puede acceder a la base de datos. Contacte al administrador.")
    except Exception as e:
        logger.error(f"Error resetting data: {str(e)}")
        st.error(f"❌ Error al reiniciar datos: {str(e)}")
    finally:
        conn.close()

# Preguntas Guía I (27 en total)
guia_i_questions = [
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
    {
        "section": "Eventos Traumáticos Severos",
        "items": [
            ("¿Ha presenciado o sufrido un accidente grave?", ["Sí", "No"]),
            ("¿Ha presenciado o sufrido un asalto?", ["Sí", "No"]),
            ("¿Ha presenciado actos violentos con lesiones?", ["Sí", "No"]),
            ("¿Ha presenciado o sufrido un secuestro?", ["Sí", "No"]),
            ("¿Ha recibido amenazas?", ["Sí", "No"]),
            ("¿Otra situación que ponga en riesgo su vida o salud?", ["Sí", "No"]),
        ]
    },
    {
        "section": "Síntomas de Reexperimentación",
        "items": [
            ("¿Recuerdos recurrentes que causan malestar?", ["Sí", "No"]),
            ("¿Sueños recurrentes que causan malestar?", ["Sí", "No"]),
        ]
    },
    {
        "section": "Síntomas de Evitación",
        "items": [
            ("¿Evita sentimientos o situaciones asociadas?", ["Sí", "No"]),
            ("¿Evita actividades o lugares asociados?", ["Sí", "No"]),
            ("¿Dificultad para recordar partes del evento?", ["Sí", "No"]),
        ]
    },
    {
        "section": "Síntomas de Afectación Emocional",
        "items": [
            ("¿Menor interés en actividades cotidianas?", ["Sí", "No"]),
            ("¿Se siente alejado o distante de los demás?", ["Sí", "No"]),
            ("¿Dificultad para expresar sentimientos?", ["Sí", "No"]),
            ("¿Sensación de vida corta o futuro limitado?", ["Sí", "No"]),
        ]
    },
    {
        "section": "Síntomas de Activación",
        "items": [
            ("¿Dificultad para dormir?", ["Sí", "No"]),
            ("¿Irritabilidad o coraje?", ["Sí", "No"]),
            ("¿Dificultad para concentrarse?", ["Sí", "No"]),
            ("¿Nerviosismo o alerta constante?", ["Sí", "No"]),
            ("¿Se sobresalta fácilmente?", ["Sí", "No"]),
        ]
    }
]

# Preguntas Guía II (46 en total)
guia_ii_questions = [
    {
        "section": "Condiciones en el Ambiente de Trabajo",
        "items": [
            ("¿El espacio donde trabaja le permite realizar sus actividades de manera segura y cómoda?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Las condiciones de su lugar de trabajo (iluminación, ventilación, temperatura, etc.) son adecuadas?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Los equipos, herramientas y materiales que utiliza están en buenas condiciones?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿El lugar donde trabaja está limpio y ordenado?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Carga de Trabajo",
        "items": [
            ("¿La cantidad de trabajo que tiene es razonable para realizarlo en su jornada laboral?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Las tareas que realiza son variadas y le permiten utilizar sus habilidades?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿El ritmo de trabajo es constante y manejable?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Tiene pausas o descansos suficientes durante su jornada laboral?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿El tiempo asignado para realizar sus actividades es suficiente?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Las metas o resultados que le exigen son claros y alcanzables?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿El volumen de trabajo le permite cumplir con sus responsabilidades personales?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Falta de Control sobre el Trabajo",
        "items": [
            ("¿Puede decidir cómo realizar sus actividades de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Tiene libertad para tomar decisiones relacionadas con su trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Puede organizar el orden de sus actividades laborales?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su opinión es tomada en cuenta para mejorar los procesos de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Recibe capacitación suficiente para realizar sus actividades?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Tiene acceso a la información necesaria para realizar su trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Jornada de Trabajo",
        "items": [
            ("¿Su jornada laboral le permite tener tiempo para su vida personal?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Trabaja horas extras con frecuencia?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]),
            ("¿Sus horarios de trabajo son estables y predecibles?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Puede descansar los días que le corresponden?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Interferencia en la Relación Trabajo-Familia",
        "items": [
            ("¿El trabajo le permite atender sus responsabilidades familiares?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Puede desconectarse del trabajo fuera de su horario laboral?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Las demandas del trabajo interfieren con su vida personal?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]),
        ]
    },
    {
        "section": "Liderazgo",
        "items": [
            ("¿Recibe instrucciones claras de sus superiores?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su jefe le apoya para resolver problemas en el trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su jefe fomenta un ambiente de trabajo positivo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su jefe reconoce su esfuerzo y desempeño?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Las decisiones de su jefe son justas y transparentes?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Relaciones en el Trabajo",
        "items": [
            ("¿El ambiente de trabajo es de respeto y colaboración?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Tiene buenas relaciones con sus compañeros de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Recibe apoyo de sus compañeros cuando lo necesita?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Se siente integrado en su equipo de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Violencia Laboral",
        "items": [
            ("¿Ha recibido gritos, insultos o burlas en el trabajo?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]),
            ("¿Ha sido discriminado por su género, edad u otra característica?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]),
            ("¿Ha recibido amenazas o intimidaciones en el trabajo?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]),
            ("¿Ha sido ignorado o excluido por sus compañeros o jefes?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]),
            ("¿Ha recibido tratos humillantes en el trabajo?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]),
        ]
    },
    {
        "section": "Reconocimiento del Desempeño",
        "items": [
            ("¿Recibe reconocimiento por su trabajo bien hecho?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su trabajo es valorado por sus superiores?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Recibe retroalimentación sobre su desempeño?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Insuficiente Sentido de Pertenencia e Inestabilidad",
        "items": [
            ("¿Se siente parte de la organización?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿La empresa le informa sobre sus objetivos y resultados?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Siente que su empleo es estable?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿La organización promueve un sentido de pertenencia?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    }
]

# Preguntas Guía III (26 en total)
guia_iii_questions = [
    {
        "section": "Sentido de Pertenencia",
        "items": [
            ("¿La empresa promueve valores que usted comparte?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Se siente orgulloso de trabajar en esta organización?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿La empresa fomenta la participación en actividades sociales o culturales?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Liderazgo Positivo",
        "items": [
            ("¿Su jefe motiva al equipo para alcanzar objetivos?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su jefe escucha sus ideas y sugerencias?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su jefe actúa con integridad y ética?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Su jefe promueve el desarrollo profesional del equipo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Colaboración y Trabajo en Equipo",
        "items": [
            ("¿Sus compañeros colaboran para resolver problemas?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Hay un ambiente de confianza entre los miembros del equipo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿El equipo comparte conocimientos y experiencias?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Se fomenta la comunicación abierta en su equipo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Reconocimiento y Equidad",
        "items": [
            ("¿La empresa reconoce los logros colectivos del equipo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Se siente tratado con justicia en su lugar de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Las oportunidades de ascenso son claras y equitativas?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿La empresa valora la diversidad en el lugar de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Condiciones de Trabajo Favorables",
        "items": [
            ("¿La empresa proporciona recursos suficientes para su trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿El ambiente de trabajo es seguro y saludable?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿La empresa promueve el equilibrio entre trabajo y vida personal?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Capacitación y Desarrollo",
        "items": [
            ("¿La empresa ofrece oportunidades de capacitación relevantes?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Recibe apoyo para desarrollar nuevas habilidades?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿La capacitación mejora su desempeño laboral?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Comunicación Organizacional",
        "items": [
            ("¿La empresa comunica claramente sus objetivos estratégicos?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Recibe información oportuna sobre cambios en la empresa?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿La empresa fomenta canales de comunicación efectivos?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    },
    {
        "section": "Innovación y Creatividad",
        "items": [
            ("¿La empresa valora las ideas innovadoras de los empleados?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Se le anima a proponer mejoras en los procesos de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    }
]

# Preguntas Guía IV (10 en total)
guia_iv_questions = [
    {
        "section": "Síntomas de Salud y Estrés",
        "items": [
            ("¿Ha sentido fatiga extrema o agotamiento frecuentemente?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha tenido dolores de cabeza o musculares sin causa médica?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha experimentado ansiedad o nerviosismo intenso?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha tenido dificultades para dormir o insomnio?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha sentido tristeza o desánimo persistente?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha notado cambios en su apetito o peso sin razón aparente?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha tenido problemas de concentración o memoria?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha sentido palpitaciones o taquicardia sin esfuerzo físico?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha tenido pensamientos recurrentes de preocupación?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
            ("¿Ha sentido irritabilidad o enojo frecuentemente?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]),
        ]
    }
]

# Sidebar
st.sidebar.image("assets/FOBO2.png", width=100)
st.sidebar.title("Evaluación NOM-035")
section = st.sidebar.radio("Ir a sección:", ["📋 Evaluación", "📥 Descargar Reporte", "🔄 Reiniciar Datos"])

def load_responses():
    """Load all responses from the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT data FROM responses')
        rows = c.fetchall()
        responses = [eval(row[0]) for row in rows]  # Convert stringified dict back to dict
        return pd.DataFrame(responses)
    except Exception as e:
        logger.error(f"Error loading responses: {str(e)}")
        st.error(f"❌ Error al cargar respuestas: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def has_positive_response_guia_i(row, symptom_cols):
    """Check for any positive ('Sí') responses in Guía I symptom questions."""
    return any(row.get(col) == 'Sí' for col in symptom_cols if col in row)

def calculate_risk_score_guia_ii(df, guia_ii_cols, domain_questions):
    """Calculate Guía II risk scores and levels using vectorized operations."""
    score_map = {"Siempre": 4, "Casi siempre": 3, "A veces": 2, "Casi nunca": 1, "Nunca": 0}
    reverse_questions = [
        "¿Trabaja horas extras con frecuencia?",
        "¿Las demandas del trabajo interfieren con su vida personal?",
        "¿Ha recibido gritos, insultos o burlas en el trabajo?",
        "¿Ha sido discriminado por su género, edad u otra característica?",
        "¿Ha recibido amenazas o intimidaciones en el trabajo?",
        "¿Ha sido ignorado o excluido por sus compañeros o jefes?",
        "¿Ha recibido tratos humillantes en el trabajo?"
    ]
    
    total_scores = pd.Series(0, index=df.index)
    domain_scores = {domain: pd.Series(0, index=df.index) for domain in domain_questions}
    
    for col in guia_ii_cols:
        if col in df.columns:
            scores = df[col].map(score_map).fillna(0)
            if col in reverse_questions:
                scores = 4 - scores
            total_scores += scores
            for domain, questions in domain_questions.items():
                if col in questions:
                    domain_scores[domain] += scores
    
    total_risk = pd.cut(
        total_scores,
        bins=[-1, 49, 74, 99, 124, float('inf')],
        labels=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"],
        include_lowest=True
    )
    
    domain_risk_levels = {}
    for domain, scores in domain_scores.items():
        max_score = len(domain_questions[domain]) * 4
        percentage = (scores / max_score) * 100
        domain_risk_levels[domain] = pd.cut(
            percentage,
            bins=[-1, 19, 39, 59, 79, float('inf')],
            labels=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"],
            include_lowest=True
        )
    
    return total_scores, total_risk, domain_scores, domain_risk_levels

def calculate_score_guia_iii(df, guia_iii_cols, domain_questions):
    """Calculate Guía III organizational environment scores and levels."""
    score_map = {"Siempre": 4, "Casi siempre": 3, "A veces": 2, "Casi nunca": 1, "Nunca": 0}
    
    total_scores = pd.Series(0, index=df.index)
    domain_scores = {domain: pd.Series(0, index=df.index) for domain in domain_questions}
    
    for col in guia_iii_cols:
        if col in df.columns:
            scores = df[col].map(score_map).fillna(0)
            total_scores += scores
            for domain, questions in domain_questions.items():
                if col in questions:
                    domain_scores[domain] += scores
    
    total_level = pd.cut(
        total_scores,
        bins=[-1, 49, 69, float('inf')],
        labels=["Desfavorable", "Medio", "Favorable"],
        include_lowest=True
    )
    
    domain_levels = {}
    for domain, scores in domain_scores.items():
        max_score = len(domain_questions[domain]) * 4
        percentage = (scores / max_score) * 100
        domain_levels[domain] = pd.cut(
            percentage,
            bins=[-1, 49, 69, float('inf')],
            labels=["Desfavorable", "Medio", "Favorable"],
            include_lowest=True
        )
    
    return total_scores, total_level, domain_scores, domain_levels

def calculate_risk_score_guia_iv(df, guia_iv_cols):
    """Calculate Guía IV health/stress risk scores and levels."""
    score_map = {"Siempre": 4, "Casi siempre": 3, "A veces": 2, "Casi nunca": 1, "Nunca": 0}
    
    total_scores = pd.Series(0, index=df.index)
    symptom_counts = pd.Series(0, index=df.index)
    
    for col in guia_iv_cols:
        if col in df.columns:
            scores = df[col].map(score_map).fillna(0)
            total_scores += scores
            symptom_counts += (scores >= 2).astype(int)
    
    risk_levels = pd.cut(
        symptom_counts,
        bins=[-1, 2, 4, float('inf')],
        labels=["Bajo", "Medio", "Alto"],
        include_lowest=True
    )
    
    return total_scores, risk_levels, symptom_counts

def generate_recommendations(guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis):
    """Generate NOM-035-compliant recommendations based on analysis."""
    recommendations = []
    total_employees = guia_i_analysis.get('Total Empleados', 1)
    
    # Guía I
    positive_responses = guia_i_analysis.get('Empleados con Respuestas Positivas', 0)
    if positive_responses > 0:
        percentage = (positive_responses / total_employees) * 100
        recommendations.append(f"{positive_responses} empleados ({percentage:.1f}%) reportaron eventos traumáticos o síntomas (Guía I). Implementar evaluaciones psicológicas y programas de apoyo.")
    
    high_risk_depts = [dept for dept, count in guia_i_analysis.get('Respuestas Positivas por Departamento', {}).items() if count > 0]
    if high_risk_depts:
        recommendations.append(f"Departamentos con respuestas positivas (Guía I): {', '.join(high_risk_depts)}. Priorizar intervenciones en estas áreas.")
    
    # Guía II
    risk_dist = guia_ii_analysis.get('Distribución de Riesgo Total', {})
    high_risk_count = sum(risk_dist.get(level, 0) for level in ["Alto", "Muy Alto"])
    if high_risk_count > 0:
        percentage = (high_risk_count / total_employees) * 100
        recommendations.append(f"{high_risk_count} empleados ({percentage:.1f}%) en riesgo Alto o Muy Alto (Guía II). Revisar condiciones laborales, liderazgo y violencia laboral.")
    
    domain_risks = guia_ii_analysis.get('Riesgo por Dominio', {})
    high_risk_domains = [domain for domain, dist in domain_risks.items() if sum(dist.get(level, 0) for level in ["Alto", "Muy Alto"]) > 0]
    if high_risk_domains:
        recommendations.append(f"Dominios con riesgo Alto o Muy Alto (Guía II): {', '.join(high_risk_domains)}. Implementar mejoras específicas en estas áreas.")
    
    # Guía III
    env_dist = guia_iii_analysis.get('Distribución de Entorno Organizacional', {})
    favorable_count = env_dist.get("Favorable", 0)
    if favorable_count > 0:
        percentage = (favorable_count / total_employees) * 100
        recommendations.append(f"{favorable_count} empleados ({percentage:.1f}%) reportan un entorno organizacional Favorable (Guía III). Reforzar estas fortalezas.")
    
    desfavorable_domains = [domain for domain, dist in guia_iii_analysis.get('Entorno por Dominio', {}).items() if dist.get("Desfavorable", 0) > 0]
    if desfavorable_domains:
        recommendations.append(f"Dominios con entorno Desfavorable (Guía III): {', '.join(desfavorable_domains)}. Desarrollar estrategias para mejorar el clima laboral.")
    
    # Guía IV
    iv_risk_dist = guia_iv_analysis.get('Distribución de Riesgo Salud', {})
    high_iv_risk = sum(iv_risk_dist.get(level, 0) for level in ["Medio", "Alto"])
    if high_iv_risk > 0:
        percentage = (high_iv_risk / total_employees) * 100
        recommendations.append(f"{high_iv_risk} empleados ({percentage:.1f}%) con riesgo Medio o Alto en salud/estrés (Guía IV). Coordinar evaluaciones clínicas y apoyo psicológico.")
    
    return recommendations if recommendations else ["No se identificaron riesgos significativos. Mantener monitoreo regular."]

def generate_statistical_analysis(df):
    """Generate statistical analysis for all NOM-035 guías."""
    guia_i_analysis = {}
    guia_ii_analysis = {}
    guia_iii_analysis = {}
    guia_iv_analysis = {}
    
    if df.empty:
        return guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis, df
    
    # Guía I: Análisis de respuestas positivas
    guia_i_symptom_cols = [q["items"][0][0] for q in guia_i_questions[1:]]
    if any(col in df.columns for col in guia_i_symptom_cols):
        guia_i_analysis['Total Empleados'] = len(df)
        df['Respuesta Positiva (Guía I)'] = df[guia_i_symptom_cols].eq('Sí').any(axis=1)
        positive_responses = df['Respuesta Positiva (Guía I)'].sum()
        guia_i_analysis['Empleados con Respuestas Positivas'] = positive_responses
        guia_i_analysis['Porcentaje con Respuestas Positivas'] = (positive_responses / len(df)) * 100 if len(df) > 0 else 0
        
        category_counts = {}
        for section in guia_i_questions[1:]:
            section_cols = [item[0] for item in section["items"] if item[0] in df.columns]
            if section_cols:
                category_counts[section["section"]] = df[section_cols].eq('Sí').sum().sum()
        guia_i_analysis['Respuestas Positivas por Categoría'] = category_counts
        
        if '¿En qué departamento labora?' in df.columns:
            dept_positive = df[df['Respuesta Positiva (Guía I)'] == True]['¿En qué departamento labora?'].value_counts().to_dict()
            guia_i_analysis['Respuestas Positivas por Departamento'] = dept_positive
        
        if '¿Cuál es tu género?' in df.columns:
            gender_positive = df[df['Respuesta Positiva (Guía I)'] == True]['¿Cuál es tu género?'].value_counts().to_dict()
            guia_i_analysis['Respuestas Positivas por Género'] = gender_positive
    
    # Guía II: Análisis de riesgos psicosociales
    guia_ii_cols = [q["items"][0][0] for q in guia_ii_questions for _ in q["items"]]
    domain_questions_ii = {section["section"]: [item[0] for item in section["items"]] for section in guia_ii_questions}
    
    if any(col in df.columns for col in guia_ii_cols):
        guia_ii_analysis['Total Empleados'] = len(df)
        
        total_scores, total_risk, domain_scores, domain_risk_levels = calculate_risk_score_guia_ii(df, guia_ii_cols, domain_questions_ii)
        df['Puntaje Total (Guía II)'] = total_scores
        df['Nivel de Riesgo Total (Guía II)'] = total_risk
        
        for domain in domain_questions_ii:
            df[f'Puntaje {domain}'] = domain_scores.get(domain, pd.Series(0, index=df.index))
            df[f'Nivel de Riesgo {domain}'] = domain_risk_levels.get(domain, pd.Series("Insignificante", index=df.index))
        
        risk_dist_total = df['Nivel de Riesgo Total (Guía II)'].value_counts().to_dict()
        guia_ii_analysis['Distribución de Riesgo Total'] = risk_dist_total
        
        domain_risks = {domain: df[f'Nivel de Riesgo {domain}'].value_counts().to_dict() for domain in domain_questions_ii}
        guia_ii_analysis['Riesgo por Dominio'] = domain_risks
        
        negative_counts = {}
        for col in guia_ii_cols:
            if col in df.columns:
                if col in [
                    "¿Trabaja horas extras con frecuencia?",
                    "¿Las demandas del trabajo interfieren con su vida personal?",
                    "¿Ha recibido gritos, insultos o burlas en el trabajo?",
                    "¿Ha sido discriminado por su género, edad u otra característica?",
                    "¿Ha recibido amenazas o intimidaciones en el trabajo?",
                    "¿Ha sido ignorado o excluido por sus compañeros o jefes?",
                    "¿Ha recibido tratos humillantes en el trabajo?"
                ]:
                    negative_counts[col] = df[col].isin(['Siempre', 'Casi siempre']).sum()
                else:
                    negative_counts[col] = df[col].isin(['Casi nunca', 'Nunca']).sum()
        guia_ii_analysis['Conteo de Respuestas Negativas (Guía II)'] = negative_counts
        
        if '¿En qué departamento labora?' in df.columns:
            dept_risk_total = df.groupby('¿En qué departamento labora?')['Nivel de Riesgo Total (Guía II)'].value_counts().unstack(fill_value=0).to_dict()
            guia_ii_analysis['Riesgo por Departamento (Guía II)'] = dept_risk_total
        
        if '¿Cuál es tu género?' in df.columns:
            gender_risk_total = df.groupby('¿Cuál es tu género?')['Nivel de Riesgo Total (Guía II)'].value_counts().unstack(fill_value=0).to_dict()
            guia_ii_analysis['Riesgo por Género (Guía II)'] = gender_risk_total
    
    # Guía III: Análisis de entorno organizacional
    guia_iii_cols = [q["items"][0][0] for q in guia_iii_questions for _ in q["items"]]
    domain_questions_iii = {section["section"]: [item[0] for item in section["items"]] for section in guia_iii_questions}
    
    if any(col in df.columns for col in guia_iii_cols):
        guia_iii_analysis['Total Empleados'] = len(df)
        
        total_scores, total_level, domain_scores, domain_levels = calculate_score_guia_iii(df, guia_iii_cols, domain_questions_iii)
        df['Puntaje Total (Guía III)'] = total_scores
        df['Nivel Entorno Total (Guía III)'] = total_level
        
        for domain in domain_questions_iii:
            df[f'Puntaje {domain}'] = domain_scores.get(domain, pd.Series(0, index=df.index))
            df[f'Nivel Entorno {domain}'] = domain_levels.get(domain, pd.Series("Desfavorable", index=df.index))
        
        env_dist_total = df['Nivel Entorno Total (Guía III)'].value_counts().to_dict()
        guia_iii_analysis['Distribución de Entorno Organizacional'] = env_dist_total
        
        domain_env = {domain: df[f'Nivel Entorno {domain}'].value_counts().to_dict() for domain in domain_questions_iii}
        guia_iii_analysis['Entorno por Dominio'] = domain_env
        
        if '¿En qué departamento labora?' in df.columns:
            dept_env_total = df.groupby('¿En qué departamento labora?')['Nivel Entorno Total (Guía III)'].value_counts().unstack(fill_value=0).to_dict()
            guia_iii_analysis['Entorno por Departamento (Guía III)'] = dept_env_total
        
        if '¿Cuál es tu género?' in df.columns:
            gender_env_total = df.groupby('¿Cuál es tu género?')['Nivel Entorno Total (Guía III)'].value_counts().unstack(fill_value=0).to_dict()
            guia_iii_analysis['Entorno por Género (Guía III)'] = gender_env_total
    
    # Guía IV: Análisis de salud y estrés
    guia_iv_cols = [q["items"][0][0] for q in guia_iv_questions for _ in q["items"]]
    if any(col in df.columns for col in guia_iv_cols):
        guia_iv_analysis['Total Empleados'] = len(df)
        
        total_scores, risk_levels, symptom_counts = calculate_risk_score_guia_iv(df, guia_iv_cols)
        df['Puntaje Total (Guía IV)'] = total_scores
        df['Nivel Riesgo Salud (Guía IV)'] = risk_levels
        df['Conteo Síntomas (Guía IV)'] = symptom_counts
        
        risk_dist_iv = df['Nivel Riesgo Salud (Guía IV)'].value_counts().to_dict()
        symptom_counts_dict = df[guia_iv_cols].apply(lambda x: x.isin(['A veces', 'Casi siempre', 'Siempre']).sum()).to_dict()
        guia_iv_analysis['Distribución de Riesgo Salud'] = risk_dist_iv
        guia_iv_analysis['Conteo de Síntomas (Guía IV)'] = symptom_counts_dict
        
        if '¿En qué departamento labora?' in df.columns:
            dept_risk_iv = df.groupby('¿En qué departamento labora?')['Nivel Riesgo Salud (Guía IV)'].value_counts().unstack(fill_value=0).to_dict()
            guia_iv_analysis['Riesgo Salud por Departamento (Guía IV)'] = dept_risk_iv
        
        if '¿Cuál es tu género?' in df.columns:
            gender_risk_iv = df.groupby('¿Cuál es tu género?')['Nivel Riesgo Salud (Guía IV)'].value_counts().unstack(fill_value=0).to_dict()
            guia_iv_analysis['Riesgo Salud por Género (Guía IV)'] = gender_risk_iv
    
    # Estadísticas descriptivas
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if not numeric_cols.empty:
        desc_stats = df[numeric_cols].describe().round(2)
        guia_i_analysis['Descriptivas Numéricas'] = desc_stats.to_dict()
    
    return guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis, df

@st.cache_data
def generate_visualizations(df, temp_dir, guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis):
    """Generate visualizations for NOM-035 analysis."""
    visualizations = []
    sns.set_style("whitegrid")
    palette = sns.color_palette("Blues", n_colors=5)
    
    try:
        if df.empty:
            return [('Text', 'No Visualizaciones', 'No hay datos suficientes para generar visualizaciones.')]
        
        # Guía I: Porcentaje de empleados con respuestas positivas
        if 'Porcentaje con Respuestas Positivas' in guia_i_analysis and guia_i_analysis['Total Empleados'] > 0:
            plt.figure(figsize=(8, 5))
            plt.bar(['Con Respuestas Positivas', 'Sin Respuestas Positivas'], 
                    [guia_i_analysis['Porcentaje con Respuestas Positivas'], 100 - guia_i_analysis['Porcentaje con Respuestas Positivas']],
                    color=palette[2])
            plt.title('Porcentaje de Empleados con Respuestas Positivas (Guía I)')
            plt.ylabel('Porcentaje (%)')
            plt.ylim(0, 100)
            guia_i_positive_path = os.path.join(temp_dir, 'positive_responses_guia_i.png')
            plt.savefig(guia_i_positive_path, bbox_inches='tight')
            plt.close()
            visualizations.append(('Bar', 'Porcentaje Respuestas Positivas (Guía I)', guia_i_positive_path))
        
        # Guía I: Respuestas positivas por categoría
        if 'Respuestas Positivas por Categoría' in guia_i_analysis and any(guia_i_analysis['Respuestas Positivas por Categoría'].values()):
            plt.figure(figsize=(12, 6))
            categories = list(guia_i_analysis['Respuestas Positivas por Categoría'].keys())
            counts = list(guia_i_analysis['Respuestas Positivas por Categoría'].values())
            plt.bar(categories, counts, color=palette[2])
            plt.title('Respuestas Positivas por Categoría (Guía I)')
            plt.xlabel('Categoría')
            plt.ylabel('Número de Respuestas Positivas')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            guia_i_category_path = os.path.join(temp_dir, 'category_responses_guia_i.png')
            plt.savefig(guia_i_category_path, bbox_inches='tight')
            plt.close()
            visualizations.append(('Bar', 'Respuestas Positivas por Categoría (Guía I)', guia_i_category_path))
        
        # Guía II: Distribución de riesgo total
        if 'Distribución de Riesgo Total' in guia_ii_analysis and any(guia_ii_analysis['Distribución de Riesgo Total'].values()):
            plt.figure(figsize=(8, 5))
            risk_counts = pd.Series(guia_ii_analysis['Distribución de Riesgo Total']).reindex(
                ["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"], fill_value=0)
            non_zero = risk_counts[risk_counts > 0]
            if not non_zero.empty:
                plt.pie(non_zero, labels=non_zero.index, autopct='%1.1f%%', colors=palette[:len(non_zero)])
                plt.title('Distribución de Riesgo Psicosocial Total (Guía II)')
                risk_path_ii = os.path.join(temp_dir, 'risk_distribution_guia_ii.png')
                plt.savefig(risk_path_ii, bbox_inches='tight')
                plt.close()
                visualizations.append(('Pie', 'Distribución de Riesgo Total (Guía II)', risk_path_ii))
        
        # Guía II: Respuestas negativas por dominio
        if 'Conteo de Respuestas Negativas (Guía II)' in guia_ii_analysis:
            domain_negatives = {}
            for section in guia_ii_questions:
                domain = section["section"]
                domain_cols = [item[0] for item in section["items"]]
                domain_negatives[domain] = sum(guia_ii_analysis['Conteo de Respuestas Negativas (Guía II)'].get(col, 0) for col in domain_cols)
            if any(domain_negatives.values()):
                plt.figure(figsize=(14, 6))
                plt.bar(domain_negatives.keys(), domain_negatives.values(), color=palette[2])
                plt.title('Respuestas Negativas por Dominio (Guía II)')
                plt.xlabel('Dominio')
                plt.ylabel('Número de Respuestas Negativas')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                guia_ii_negative_path = os.path.join(temp_dir, 'negative_responses_guia_ii.png')
                plt.savefig(guia_ii_negative_path, bbox_inches='tight')
                plt.close()
                visualizations.append(('Bar', 'Respuestas Negativas por Dominio (Guía II)', guia_ii_negative_path))
        
        # Guía III: Distribución de entorno organizacional
        if 'Distribución de Entorno Organizacional' in guia_iii_analysis and any(guia_iii_analysis['Distribución de Entorno Organizacional'].values()):
            plt.figure(figsize=(8, 5))
            env_counts = pd.Series(guia_iii_analysis['Distribución de Entorno Organizacional']).reindex(
                ["Favorable", "Medio", "Desfavorable"], fill_value=0)
            non_zero = env_counts[env_counts > 0]
            if not non_zero.empty:
                plt.pie(non_zero, labels=non_zero.index, autopct='%1.1f%%', colors=palette[:len(non_zero)])
                plt.title('Distribución de Entorno Organizacional (Guía III)')
                env_path_iii = os.path.join(temp_dir, 'env_distribution_guia_iii.png')
                plt.savefig(env_path_iii, bbox_inches='tight')
                plt.close()
                visualizations.append(('Pie', 'Distribución de Entorno Organizacional (Guía III)', env_path_iii))
        
        # Guía IV: Prevalencia de síntomas de salud
        if 'Conteo de Síntomas (Guía IV)' in guia_iv_analysis and any(guia_iv_analysis['Conteo de Síntomas (Guía IV)'].values()):
            plt.figure(figsize=(12, 6))
            symptoms = list(guia_iv_analysis['Conteo de Síntomas (Guía IV)'].keys())
            counts = list(guia_iv_analysis['Conteo de Síntomas (Guía IV)'].values())
            plt.bar(symptoms, counts, color=palette[2])
            plt.title('Prevalencia de Síntomas de Salud (Guía IV)')
            plt.xlabel('Síntoma')
            plt.ylabel('Número de Empleados')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            guia_iv_symptom_path = os.path.join(temp_dir, 'symptom_prevalence_guia_iv.png')
            plt.savefig(guia_iv_symptom_path, bbox_inches='tight')
            plt.close()
            visualizations.append(('Bar', 'Prevalencia de Síntomas de Salud (Guía IV)', guia_iv_symptom_path))
        
        # Distribución de edad
        if '¿Qué edad tienes? (ej. 21)' in df.columns and df['¿Qué edad tienes? (ej. 21)'].notna().any():
            plt.figure(figsize=(8, 5))
            sns.histplot(df['¿Qué edad tienes? (ej. 21)'], kde=True, color=palette[3])
            plt.title('Distribución de Edad')
            plt.xlabel('Edad')
            plt.ylabel('Frecuencia')
            age_path = os.path.join(temp_dir, 'age_distribution.png')
            plt.savefig(age_path, bbox_inches='tight')
            plt.close()
            visualizations.append(('Histograma', 'Distribución de Edad', age_path))
    
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}")
        visualizations.append(('Text', 'Error de Visualización', f'Error al generar visualizaciones: {str(e)}'))
    
    return visualizations

# Evaluación
if section == "📋 Evaluación":
    st.title("🧠 Evaluación Psicosocial - NOM-035 Guía I, II, III y IV")
    st.markdown("Por favor responda con honestidad. La información será confidencial.")
    
    # Progress indicator
    steps = ["Guía I", "Guía II", "Guía III", "Guía IV"]
    current_idx = {"guia_i": 0, "guia_ii": 1, "guia_iii": 2, "guia_iv": 3}.get(st.session_state.current_step, 0)
    st.progress(current_idx / (len(steps) - 1))
    st.write(f"Paso {current_idx + 1} de {len(steps)}: {steps[current_idx]}")
    
    if st.session_state.current_step == "guia_i":
        with st.form("guia_i_form"):
            respuestas = {}
            for section_data in guia_i_questions:
                with st.expander(section_data["section"], expanded=True):
                    for idx, (q, tipo) in enumerate(section_data["items"]):
                        st.markdown(f"**{q}**")
                        try:
                            if tipo == "text":
                                respuestas[q] = sanitize_text(st.text_input("", key=f"gi_q{idx}_{q}", max_chars=100))
                            elif tipo == "number":
                                respuestas[q] = st.number_input("", min_value=0, step=1, key=f"gi_q{idx}_{q}")
                            elif isinstance(tipo, list):
                                respuestas[q] = st.radio("", tipo, key=f"gi_q{idx}_{q}")
                        except ValueError as ve:
                            st.warning(f"⚠️ {q}: {str(ve)}")
            
            enviar = st.form_submit_button("✅ Enviar Guía I")
            if enviar:
                try:
                    expected_questions = [item[0] for section in guia_i_questions for item in section["items"]]
                    is_valid, missing = validate_questions(respuestas, expected_questions)
                    if not is_valid:
                        st.warning(f"⚠️ Responde todas las preguntas antes de enviar. Faltan: {', '.join(missing)}")
                    else:
                        for q in ["¿Qué edad tienes? (ej. 21)", "¿Cuántos años llevas trabajando aquí?"]:
                            if q in respuestas and not validate_number(respuestas[q]):
                                st.warning(f"⚠️ {q}: Por favor ingrese un número entero mayor o igual a 0.")
                        return
                        response_id = log_response(respuestas)
                        if response_id:
                            st.session_state.guia_i_responses = respuestas
                            st.session_state.response_id = response_id
                            symptom_cols = [q["items"][0][0] for q in guia_i_questions[1:]]
                            has_positive = any(respuestas.get(col) == "Sí" for col in symptom_cols)
                            if has_positive:
                                st.session_state.current_step = "guia_ii"
                                st.success("✅ Guía I enviada. Por favor complete la Guía II.")
                            else:
                                st.session_state.current_step = "guia_i"
                                st.session_state.guia_i_responses = None
                                st.session_state.response_id = None
                                st.success("✅ ¡Evaluación Guía I completada! No se requiere Guía II.")
                        else:
                            st.error("❌ Error al guardar la respuesta. Intente nuevamente.")
                except Exception as e:
                    logger.error(f"Error processing Guía I: {str(e)}")
                    st.error(f"❌ Error al procesar la evaluación: {str(e)}")
    
    elif st.session_state.current_step == "guia_ii":
        with st.form("guia_ii_form"):
            respuestas = st.session_state.guia_i_responses.copy()
            for section_data in guia_ii_questions:
                with st.expander(section_data["section"], expanded=True):
                    for idx, (q, tipo) in enumerate(section_data["items"]):
                        st.markdown(f"**{q}**")
                        respuestas[q] = st.radio("", tipo, horizontal=True, key=f"gii_q{idx}_{q}")
            
            enviar = st.form_submit_button("✅ Enviar Guía II")
            if enviar:
                try:
                    expected_questions = [item[0] for section in guia_ii_questions for item in section["items"]]
                    is_valid, missing = validate_questions(respuestas, expected_questions)
                    if not is_valid:
                        st.warning(f"⚠️ Responde todas las preguntas antes de enviar. Faltan: {', '.join(missing)}")
                    else:
                        response_id = log_response(respuestas, st.session_state.response_id)
                        if response_id:
                            st.session_state.guia_ii_responses = respuestas
                            st.session_state.response_id = response_id
                            guia_ii_cols = [q["items"][0][0] for q in guia_ii_questions for _ in q["items"]]
                            domain_questions_ii = {section["section"]: [item[0] for item in section["items"]] for section in guia_ii_questions}
                            temp_df = pd.DataFrame([respuestas])
                            total_scores, total_risk, _, _ = calculate_risk_score_guia_ii(temp_df, guia_ii_cols, domain_questions_ii)
                            total_risk = total_risk.iloc[0]
                            if total_risk in ["Insignificante", "Bajo"]:
                                st.session_state.current_step = "guia_iii"
                                st.session_state.require_guia_iv = False
                                st.success("✅ Guía II enviada. Por favor complete la Guía III.")
                            elif total_risk == "Medio":
                                st.session_state.current_step = "guia_iii"
                                st.session_state.require_guia_iv = True
                                st.success("✅ Guía II enviada. Por favor complete la Guía III, seguida de la Guía IV.")
                            elif total_risk in ["Alto", "Muy Alto"]:
                                st.session_state.current_step = "guia_iv"
                                st.session_state.require_guia_iv = False
                                st.success("✅ Guía II enviada. Por favor complete la Guía IV.")
                        else:
                            st.error("❌ Error al guardar la respuesta. Intente nuevamente.")
                except Exception as e:
                    logger.error(f"Error processing Guía II: {str(e)}")
                    st.error(f"❌ Error al procesar la evaluación: {str(e)}")
    
    elif st.session_state.current_step == "guia_iii":
        with st.form("guia_iii_form"):
            respuestas = st.session_state.guia_ii_responses.copy()
            for section_data in guia_iii_questions:
                with st.expander(section_data["section"], expanded=True):
                    for idx, (q, tipo) in enumerate(section_data["items"]):
                        st.markdown(f"**{q}**")
                        respuestas[q] = st.radio("", tipo, horizontal=True, key=f"giii_q{idx}_{q}")
            
            enviar = st.form_submit_button("✅ Enviar Guía III")
            if enviar:
                try:
                    expected_questions = [item[0] for section in guia_iii_questions for item in section["items"]]
                    is_valid, missing = validate_questions(respuestas, expected_questions)
                    if not is_valid:
                        st.warning(f"⚠️ Responde todas las preguntas antes de enviar. Faltan: {', '.join(missing)}")
                    else:
                        response_id = log_response(respuestas, st.session_state.response_id)
                        if response_id:
                            if st.session_state.require_guia_iv:
                                st.session_state.current_step = "guia_iv"
                                st.success("✅ Guía III enviada. Por favor complete la Guía IV.")
                            else:
                                st.session_state.current_step = "guia_i"
                                st.session_state.guia_i_responses = None
                                st.session_state.guia_ii_responses = None
                                st.session_state.response_id = None
                                st.session_state.require_guia_iv = False
                                st.success("✅ ¡Evaluación Guía I, II y III completada exitosamente!")
                        else:
                            st.error("❌ Error al guardar la respuesta. Intente nuevamente.")
                except Exception as e:
                    logger.error(f"Error processing Guía III: {str(e)}")
                    st.error(f"❌ Error al procesar la evaluación: {str(e)}")
    
    elif st.session_state.current_step == "guia_iv":
        with st.form("guia_iv_form"):
            respuestas = st.session_state.guia_ii_responses.copy()
            for section_data in guia_iv_questions:
                with st.expander(section_data["section"], expanded=True):
                    for idx, (q, tipo) in enumerate(section_data["items"]):
                        st.markdown(f"**{q}**")
                        respuestas[q] = st.radio("", tipo, horizontal=True, key=f"giv_q{idx}_{q}")
            
            enviar = st.form_submit_button("✅ Enviar Guía IV")
            if enviar:
                try:
                    expected_questions = [item[0] for section in guia_iv_questions for item in section["items"]]
                    is_valid, missing = validate_questions(respuestas, expected_questions)
                    if not is_valid:
                        st.warning(f"⚠️ Responde todas las preguntas antes de enviar. Faltan: {', '.join(missing)}")
                    else:
                        response_id = log_response(respuestas, st.session_state.response_id)
                        if response_id:
                            st.session_state.current_step = "guia_i"
                            st.session_state.guia_i_responses = None
                            st.session_state.guia_ii_responses = None
                            st.session_state.response_id = None
                            st.session_state.require_guia_iv = False
                            st.success("✅ ¡Evaluación Guía I, II y IV completada exitosamente!")
                        else:
                            st.error("❌ Error al guardar la respuesta. Intente nuevamente.")
                except Exception as e:
                    logger.error(f"Error processing Guía IV: {str(e)}")
                    st.error(f"❌ Error al procesar la evaluación: {str(e)}")

# Reporte Excel
elif section == "📥 Descargar Reporte":
    st.title("📥 Reporte Consolidado")
    
    access_key = st.text_input("🔑 Ingrese la clave de acceso:", type="password")
    
    if access_key == ACCESS_KEY:
        df = load_responses()
        if df.empty:
            st.warning("⚠️ No hay respuestas disponibles para generar el reporte.")
        else:
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis, df = generate_statistical_analysis(df)
                    visualizations = generate_visualizations(df, temp_dir, guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis)
                    recommendations = generate_recommendations(guia_i_analysis, guia_ii_analysis, guia_iii_analysis, guia_iv_analysis)
                    
                    wb = Workbook()
                    
                    # Resumen Ejecutivo
                    ws_summary = wb.active
                    ws_summary.title = "Resumen Ejecutivo"
                    ws_summary.cell(1, 1).value = "Reporte NOM-035 Guía I, II, III y IV - Resumen Ejecutivo"
                    ws_summary.cell(2, 1).value = f"Fecha: {datetime.now().strftime('%Y-%m-%d')}"
                    ws_summary.cell(4, 1).value = "Hallazgos Clave:"
                    for i, rec in enumerate(recommendations, start=5):
                        ws_summary.cell(i, 1).value = f"- {rec}"
                    
                    # Insert visualizations
                    row = len(recommendations) + 6
                    for vis_type, title, path in visualizations:
                        ws_summary.cell(row, 1).value = title
                        if vis_type != 'Text':
                            img = Image(path)
                            img.anchor = f"A{row+1}"
                            ws_summary.add_image(img)
                        else:
                            ws_summary.cell(row+1, 1).value = path
                        row += 20
                    
                    # Datos Crudos
                    ws_data = wb.create_sheet("Datos Crudos")
                    ws_data.append(df.columns.tolist())
                    for row_data in df.itertuples(index=False):
                        ws_data.append([str(cell) for cell in row_data])
                    
                    # Análisis Estadístico
                    ws_stats = wb.create_sheet("Análisis Estadístico")
                    row = 1
                    
                    # Guía I
                    ws_stats.cell(row, 1).value = "Análisis Guía I"
                    row += 1
                    ws_stats.cell(row, 1).value = "Total Empleados"
                    ws_stats.cell(row, 2).value = guia_i_analysis.get('Total Empleados', 0)
                    row += 1
                    ws_stats.cell(row, 1).value = "Empleados con Respuestas Positivas"
                    ws_stats.cell(row, 2).value = guia_i_analysis.get('Empleados con Respuestas Positivas', 0)
                    row += 1
                    ws_stats.cell(row, 1).value = "Porcentaje con Respuestas Positivas"
                    ws_stats.cell(row, 2).value = round(guia_i_analysis.get('Porcentaje con Respuestas Positivas', 0), 1)
                    row += 2
                    
                    ws_stats.cell(row, 1).value = "Respuestas Positivas por Categoría"
                    row += 1
                    for cat, count in guia_i_analysis.get('Respuestas Positivas por Categoría', {}).items():
                        ws_stats.cell(row, 1).value = cat
                        ws_stats.cell(row, 2).value = count
                        row += 1
                    row += 2
                    
                    if 'Respuestas Positivas por Departamento' in guia_i_analysis:
                        ws_stats.cell(row, 1).value = "Respuestas Positivas por Departamento"
                        row += 1
                        for dept, count in guia_i_analysis['Respuestas Positivas por Departamento'].items():
                            ws_stats.cell(row, 1).value = dept
                            ws_stats.cell(row, 2).value = count
                            row += 1
                        row += 2
                    
                    if 'Respuestas Positivas por Género' in guia_i_analysis:
                        ws_stats.cell(row, 1).value = "Respuestas Positivas por Género"
                        row += 1
                        for gender, count in guia_i_analysis['Respuestas Positivas por Género'].items():
                            ws_stats.cell(row, 1).value = gender
                            ws_stats.cell(row, 2).value = count
                            row += 1
                        row += 2
                    
                    # Guía II
                    ws_stats.cell(row, 1).value = "Análisis Guía II"
                    row += 1
                    ws_stats.cell(row, 1).value = "Distribución de Riesgo Total (Guía II)"
                    row += 1
                    for level, count in guia_ii_analysis.get('Distribución de Riesgo Total', {}).items():
                        ws_stats.cell(row, 1).value = level
                        ws_stats.cell(row, 2).value = count
                        row += 1
                    row += 2
                    
                    ws_stats.cell(row, 1).value = "Riesgo por Dominio (Guía II)"
                    row += 1
                    for domain, dist in guia_ii_analysis.get('Riesgo por Dominio', {}).items():
                        ws_stats.cell(row, 1).value = domain
                        row += 1
                        for level, count in dist.items():
                            ws_stats.cell(row, 2).value = level
                            ws_stats.cell(row, 3).value = count
                            row += 1
                        row += 1
                    
                    ws_stats.cell(row, 1).value = "Conteo de Respuestas Negativas (Guía II)"
                    row += 1
                    for col, count in guia_ii_analysis.get('Conteo de Respuestas Negativas (Guía II)', {}).items():
                        ws_stats.cell(row, 1).value = col
                        ws_stats.cell(row, 2).value = count
                        row += 1
                    row += 2
                    
                    if 'Riesgo por Departamento (Guía II)' in guia_ii_analysis:
                        ws_stats.cell(row, 1).value = "Riesgo por Departamento (Guía II)"
                        row += 1
                        dept_risk_ii = pd.DataFrame(guia_ii_analysis['Riesgo por Departamento (Guía II)'])
                        ws_stats.cell(row, 1).value = "Departamento"
                        for c, col in enumerate(dept_risk_ii.columns, start=2):
                            ws_stats.cell(row, c).value = col
                        row += 1
                        for r, idx in enumerate(dept_risk_ii.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(dept_risk_ii.columns, start=2):
                                ws_stats.cell(r, c).value = dept_risk_ii.loc[idx, col]
                        row += len(dept_risk_ii) + 2
                    
                    if 'Riesgo por Género (Guía II)' in guia_ii_analysis:
                        ws_stats.cell(row, 1).value = "Riesgo por Género (Guía II)"
                        row += 1
                        gender_risk_ii = pd.DataFrame(guia_ii_analysis['Riesgo por Género (Guía II)'])
                        ws_stats.cell(row, 1).value = "Género"
                        for c, col in enumerate(gender_risk_ii.columns, start=2):
                            ws_stats.cell(row, c).value = col
                        row += 1
                        for r, idx in enumerate(gender_risk_ii.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(gender_risk_ii.columns, start=2):
                                ws_stats.cell(r, c).value = gender_risk_ii.loc[idx, col]
                        row += len(gender_risk_ii) + 2
                    
                    # Guía III
                    ws_stats.cell(row, 1).value = "Análisis Guía III"
                    row += 1
                    ws_stats.cell(row, 1).value = "Distribución de Entorno Organizacional (Guía III)"
                    row += 1
                    for level, count in guia_iii_analysis.get('Distribución de Entorno Organizacional', {}).items():
                        ws_stats.cell(row, 1).value = level
                        ws_stats.cell(row, 2).value = count
                        row += 1
                    row += 2
                    
                    ws_stats.cell(row, 1).value = "Entorno por Dominio (Guía III)"
                    row += 1
                    for domain, dist in guia_iii_analysis.get('Entorno por Dominio', {}).items():
                        ws_stats.cell(row, 1).value = domain
                        row += 1
                        for level, count in dist.items():
                            ws_stats.cell(row, 2).value = level
                            ws_stats.cell(row, 3).value = count
                            row += 1
                        row += 1
                    
                    if 'Entorno por Departamento (Guía III)' in guia_iii_analysis:
                        ws_stats.cell(row, 1).value = "Entorno por Departamento (Guía III)"
                        row += 1
                        dept_env_iii = pd.DataFrame(guia_iii_analysis['Entorno por Departamento (Guía III)'])
                        ws_stats.cell(row, 1).value = "Departamento"
                        for c, col in enumerate(dept_env_iii.columns, start=2):
                            ws_stats.cell(row, c).value = col
                        row += 1
                        for r, idx in enumerate(dept_env_iii.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(dept_env_iii.columns, start=2):
                                ws_stats.cell(r, c).value = dept_env_iii.loc[idx, col]
                        row += len(dept_env_iii) + 2
                    
                    if 'Entorno por Género (Guía III)' in guia_iii_analysis:
                        ws_stats.cell(row, 1).value = "Entorno por Género (Guía III)"
                        row += 1
                        gender_env_iii = pd.DataFrame(guia_iii_analysis['Entorno por Género (Guía III)'])
                        ws_stats.cell(row, 1).value = "Género"
                        for c, col in enumerate(gender_env_iii.columns, start=2):
                            ws_stats.cell(row, c).value = col
                        row += 1
                        for r, idx in enumerate(gender_env_iii.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(gender_env_iii.columns, start=2):
                                ws_stats.cell(r, c).value = gender_env_iii.loc[idx, col]
                        row += len(gender_env_iii) + 2
                    
                    # Guía IV
                    ws_stats.cell(row, 1).value = "Análisis Guía IV"
                    row += 1
                    ws_stats.cell(row, 1).value = "Distribución de Riesgo Salud (Guía IV)"
                    row += 1
                    for level, count in guia_iv_analysis.get('Distribución de Riesgo Salud', {}).items():
                        ws_stats.cell(row, 1).value = level
                        ws_stats.cell(row, 2).value = count
                        row += 1
                    row += 2
                    
                    ws_stats.cell(row, 1).value = "Conteo de Síntomas (Guía IV)"
                    row += 1
                    for col, count in guia_iv_analysis.get('Conteo de Síntomas (Guía IV)', {}).items():
                        ws_stats.cell(row, 1).value = col
                        ws_stats.cell(row, 2).value = count
                        row += 1
                    row += 2
                    
                    if 'Riesgo Salud por Departamento (Guía IV)' in guia_iv_analysis:
                        ws_stats.cell(row, 1).value = "Riesgo Salud por Departamento (Guía IV)"
                        row += 1
                        dept_risk_iv = pd.DataFrame(guia_iv_analysis['Riesgo Salud por Departamento (Guía IV)'])
                        ws_stats.cell(row, 1).value = "Departamento"
                        for c, col in enumerate(dept_risk_iv.columns, start=2):
                            ws_stats.cell(row, c).value = col
                        row += 1
                        for r, idx in enumerate(dept_risk_iv.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(dept_risk_iv.columns, start=2):
                                ws_stats.cell(r, c).value = dept_risk_iv.loc[idx, col]
                        row += len(dept_risk_iv) + 2
                    
                    if 'Riesgo Salud por Género (Guía IV)' in guia_iv_analysis:
                        ws_stats.cell(row, 1).value = "Riesgo Salud por Género (Guía IV)"
                        row += 1
                        gender_risk_iv = pd.DataFrame(guia_iv_analysis['Riesgo Salud por Género (Guía IV)'])
                        ws_stats.cell(row, 1).value = "Género"
                        for c, col in enumerate(gender_risk_iv.columns, start=2):
                            ws_stats.cell(row, c).value = col
                        row += 1
                        for r, idx in enumerate(gender_risk_iv.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(gender_risk_iv.columns, start=2):
                                ws_stats.cell(row, c).value = col
                                row += 1
                        for r, idx in enumerate(gender_risk_iv.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(gender_risk_iv.columns, start=2):
                                ws_stats.cell(r, c).value = gender_risk_iv.loc[idx, col]
                        row += len(gender_risk_iv) + 2

                    # Save workbook
                    excel_path = os.path.join(temp_dir, "NOM035_Reporte.xlsx")
                    wb.save(excel_path)

                    # Provide download button
                    with open(excel_path, "rb") as file:
                        st.download_button(
                            label="📥 Descargar Reporte Excel",
                            data=file,
                            file_name="NOM035_Reporte.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    # Display recommendations
                    st.subheader("📋 Recomendaciones")
                    for rec in recommendations:
                        st.write(f"- {rec}")

                    # Display visualizations
                    st.subheader("📊 Visualizaciones")
                    for vis_type, title, path in visualizations:
                        st.markdown(f"**{title}**")
                        if vis_type != 'Text':
                            st.image(path, use_column_width=True)
                        else:
                            st.write(path)

            except Exception as e:
                logger.error(f"Error generating report: {str(e)}")
                st.error(f"❌ Error al generar el reporte: {str(e)}")
    else:
        st.error("🔐 Clave de acceso incorrecta. Contacte al administrador.")

# Reiniciar Datos
elif section == "🔄 Reiniciar Datos":
    st.title("🔄 Reiniciar Datos")
    st.warning("⚠️ Esta acción eliminará todas las respuestas almacenadas. Proceda con precaución.")
    
    password = st.text_input("🔑 Ingrese la contraseña de reinicio:", type="password")
    if st.button("🔄 Reiniciar"):
        reset_data(password)

# Footer
st.markdown("---")
st.markdown("Desarrollado por xAI para la evaluación psicosocial conforme a la NOM-035-STPS-2018.")
