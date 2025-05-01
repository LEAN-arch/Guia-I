import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.drawing.image import Image
import matplotlib.pyplot as plt
import seaborn as sns
import tempfile
import numpy as np
from datetime import datetime
import uuid
import os
import re
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
ACCESS_KEY = os.getenv("NOM035_ACCESS_KEY", "NOM035_ACCESS_2025")
RESET_PASSWORD = os.getenv("NOM035_RESET_PASSWORD", "RESET_NOM035_2025")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("nom035_app.log")
    ]
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="🧠 NOM-035 Guía I y II", layout="centered")

# Custom CSS for styling, accessibility, and responsiveness
st.markdown("""
<style>
.stButton>button {
    margin: 5px;
    transition: background-color 0.3s;
    width: 100%;
}
.primary-button {
    background-color: #28a745;
    color: white;
    border-radius: 5px;
}
.primary-button:hover {
    background-color: #218838;
}
.stRadio > div {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}
@media (max-width: 600px) {
    .stButton>button {
        font-size: 14px;
        padding: 8px;
    }
    .stRadio > div {
        flex-direction: column;
    }
}
[role="radiogroup"] {
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    defaults = {
        "responses": [],
        "show_guia_ii": False,
        "guia_i_responses": None,
        "session_initialized": False,
        "form_error": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not st.session_state.session_initialized:
        st.session_state.responses = []
        st.session_state.show_guia_ii = False
        st.session_state.guia_i_responses = None
        st.session_state.session_initialized = True
        logger.info("Session state initialized")

initialize_session_state()

# Questions for Guía I
guia_i_questions = [
    {
        "section": "Información Personal",
        "items": [
            ("Nombre", "text", {"max_length": 50}),
            ("Apellido Paterno", "text", {"max_length": 50}),
            ("Apellido Materno", "text", {"max_length": 50}),
            ("¿Qué edad tienes? (ej. 21)", "number", {"min_value": 18, "max_value": 100}),
            ("¿Cuál es tu género?", ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"], {}),
            ("¿Cuántos años llevas trabajando aquí?", "number", {"min_value": 0, "max_value": 50}),
            ("¿En qué departamento labora?", ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"], {}),
            ("¿Cuál es su función?", ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"], {}),
            ("¿Dónde se encuentra su lugar de trabajo?", ["Planta 1", "Planta 2", "Planta 3"], {}),
        ]
    },
    {
        "section": "Eventos Traumáticos Severos",
        "items": [
            ("¿Ha presenciado o sufrido un accidente grave?", ["Sí", "No"], {}),
            ("¿Ha presenciado o sufrido un asalto?", ["Sí", "No"], {}),
            ("¿Ha presenciado actos violentos con lesiones?", ["Sí", "No"], {}),
            ("¿Ha presenciado o sufrido un secuestro?", ["Sí", "No"], {}),
            ("¿Ha recibido amenazas?", ["Sí", "No"], {}),
            ("¿Otra situación que ponga en riesgo su vida o salud?", ["Sí", "No"], {}),
        ]
    },
    {
        "section": "Síntomas de Reexperimentación",
        "items": [
            ("¿Recuerdos recurrentes que causan malestar?", ["Sí", "No"], {}),
            ("¿Sueños recurrentes que causan malestar?", ["Sí", "No"], {}),
        ]
    },
    {
        "section": "Síntomas de Evitación",
        "items": [
            ("¿Evita sentimientos o situaciones asociadas?", ["Sí", "No"], {}),
            ("¿Evita actividades o lugares asociados?", ["Sí", "No"], {}),
            ("¿Dificultad para recordar partes del evento?", ["Sí", "No"], {}),
        ]
    },
    {
        "section": "Síntomas de Afectación Emocional",
        "items": [
            ("¿Menor interés en actividades cotidianas?", ["Sí", "No"], {}),
            ("¿Se siente alejado o distante de los demás?", ["Sí", "No"], {}),
            ("¿Dificultad para expresar sentimientos?", ["Sí", "No"], {}),
            ("¿Sensación de vida corta o futuro limitado?", ["Sí", "No"], {}),
        ]
    },
    {
        "section": "Síntomas de Activación",
        "items": [
            ("¿Dificultad para dormir?", ["Sí", "No"], {}),
            ("¿Irritabilidad o coraje?", ["Sí", "No"], {}),
            ("¿Dificultad para concentrarse?", ["Sí", "No"], {}),
            ("¿Nerviosismo o alerta constante?", ["Sí", "No"], {}),
            ("¿Se sobresalta fácilmente?", ["Sí", "No"], {}),
        ]
    }
]

# Questions for Guía II
guia_ii_questions = [
    {
        "section": "Condiciones en el Ambiente de Trabajo",
        "items": [
            ("¿El espacio donde trabaja le permite realizar sus actividades de manera segura y cómoda?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Las condiciones de su lugar de trabajo (iluminación, ventilación, temperatura, etc.) son adecuadas?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Los equipos, herramientas y materiales que utiliza están en buenas condiciones?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿El lugar donde trabaja está limpio y ordenado?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    },
    {
        "section": "Carga de Trabajo",
        "items": [
            ("¿La cantidad de trabajo que tiene es razonable para realizarlo en su jornada laboral?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Las tareas que realiza son variadas y le permiten utilizar sus habilidades?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿El ritmo de trabajo es constante y manejable?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Tiene pausas o descansos suficientes durante su jornada laboral?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿El tiempo asignado para realizar sus actividades es suficiente?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Las metas o resultados que le exigen son claros y alcanzables?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿El volumen de trabajo le permite cumplir con sus responsabilidades personales?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    },
    {
        "section": "Falta de Control sobre el Trabajo",
        "items": [
            ("¿Puede decidir cómo realizar sus actividades de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Tiene libertad para tomar decisiones relacionadas con su trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Puede organizar el orden de sus actividades laborales?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Su opinión es tomada en cuenta para mejorar los procesos de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Recibe capacitación suficiente para realizar sus actividades?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Tiene acceso a la información necesaria para realizar su trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    },
    {
        "section": "Jornada de Trabajo",
        "items": [
            ("¿Su jornada laboral le permite tener tiempo para su vida personal?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Trabaja horas extras con frecuencia?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], {}),
            ("¿Sus horarios de trabajo son estables y predecibles?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Puede descansar los días que le corresponden?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    },
    {
        "section": "Interferencia en la Relación Trabajo-Familia",
        "items": [
            ("¿El trabajo le permite atender sus responsabilidades familiares?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Puede desconectarse del trabajo fuera de su horario laboral?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Las demandas del trabajo interfieren con su vida personal?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], {}),
        ]
    },
    {
        "section": "Liderazgo",
        "items": [
            ("¿Recibe instrucciones claras de sus superiores?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Su jefe le apoya para resolver problemas en el trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Su jefe fomenta un ambiente de trabajo positivo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Su jefe reconoce su esfuerzo y desempeño?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Las decisiones de su jefe son justas y transparentes?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    },
    {
        "section": "Relaciones en el Trabajo",
        "items": [
            ("¿El ambiente de trabajo es de respeto y colaboración?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Tiene buenas relaciones con sus compañeros de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Recibe apoyo de sus compañeros cuando lo necesita?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Se siente integrado en su equipo de trabajo?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    },
    {
        "section": "Violencia Laboral",
        "items": [
            ("¿Ha recibido gritos, insultos o burlas en el trabajo?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], {}),
            ("¿Ha sido discriminado por su género, edad u otra característica?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], {}),
            ("¿Ha recibido amenazas o intimidaciones en el trabajo?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], {}),
            ("¿Ha sido ignorado o excluido por sus compañeros o jefes?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], {}),
            ("¿Ha recibido tratos humillantes en el trabajo?", ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], {}),
        ]
    },
    {
        "section": "Reconocimiento del Desempeño",
        "items": [
            ("¿Recibe reconocimiento por su trabajo bien hecho?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Su trabajo es valorado por sus superiores?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Recibe retroalimentación sobre su desempeño?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    },
    {
        "section": "Insuficiente Sentido de Pertenencia e Inestabilidad",
        "items": [
            ("¿Se siente parte de la organización?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿La empresa le informa sobre sus objetivos y resultados?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿Siente que su empleo es estable?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
            ("¿La organización promueve un sentido de pertenencia?", ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"], {}),
        ]
    }
]

# Utility functions
def sanitize_text(text):
    """Sanitize text inputs to prevent CSV/Excel formatting issues."""
    if isinstance(text, str):
        return re.sub(r'[,\n\r\t]', ' ', text.strip())
    return text

def validate_form(responses, questions):
    """Validate form responses for all questions."""
    errors = []
    for section_data in questions:
        for q, tipo, params in section_data["items"]:
            value = responses.get(q)
            if value is None:
                errors.append(f"Falta respuesta para: {q}")
                continue
            if tipo == "text":
                if not value or value.isspace():
                    errors.append(f"El campo {q} no puede estar vacío")
                if params.get("max_length") and len(value) > params["max_length"]:
                    errors.append(f"{q} excede el límite de {params['max_length']} caracteres")
            elif tipo == "number":
                min_val = params.get("min_value", 0)
                max_val = params.get("max_value", float('inf'))
                if value < min_val:
                    errors.append(f"{q} debe ser al menos {min_val}")
                if value > max_val:
                    errors.append(f"{q} no puede exceder {max_val}")
            elif isinstance(tipo, list) and value not in tipo:
                errors.append(f"Selección inválida para: {q}")
    return len(errors) == 0, errors

@st.cache_data
def log_response(response, temp_dir, max_retries=3):
    """Log responses with retry mechanism."""
    for attempt in range(max_retries):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sanitized_response = {k: sanitize_text(v) for k, v in response.items()}
            log_data = {'Timestamp': timestamp, **sanitized_response}
            log_df = pd.DataFrame([log_data])
            log_file = os.path.join(temp_dir, 'responses_log.csv')
            mode = 'a' if os.path.exists(log_file) else 'w'
            header = not os.path.exists(log_file)
            log_df.to_csv(log_file, mode=mode, header=header, index=False)
            logger.info("Response logged successfully")
            return True
        except PermissionError:
            if attempt == max_retries - 1:
                logger.error("Failed to write to log file due to permissions")
                return False
            time.sleep(0.5)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to log response: {str(e)}")
                return False
            time.sleep(0.5)
    return False

def reset_data(password, temp_dir):
    """Reset all data and logs."""
    if password == RESET_PASSWORD:
        st.session_state.responses = []
        st.session_state.show_guia_ii = False
        st.session_state.guia_i_responses = None
        st.session_state.session_initialized = True
        try:
            log_file = os.path.join(temp_dir, 'responses_log.csv')
            with open(log_file, 'w') as f:
                f.write('')
            logger.info("Data and log reset successfully")
            st.success("✅ Datos y log reiniciados exitosamente.")
        except PermissionError:
            logger.error("Failed to reset log due to permissions")
            st.error("❌ Error: No se pudo reiniciar el log debido a permisos.")
        except Exception as e:
            logger.error(f"Failed to reset log: {str(e)}")
            st.error(f"❌ Error al reiniciar el log: {str(e)}")
    else:
        logger.warning("Invalid reset password attempt")
        st.error("🔐 Contraseña incorrecta para reiniciar datos.")

def has_positive_response_guia_i(row):
    """Check for positive responses in Guía I."""
    symptom_cols = [item[0] for section in guia_i_questions[1:] for item in section["items"]]
    return any(row.get(col, 'No') == 'Sí' for col in symptom_cols)

@st.cache_data
def calculate_risk_score_guia_ii(row, guia_ii_cols, domain_questions):
    """Calculate risk score for Guía II."""
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
    
    total_score = 0
    domain_scores = {}
    
    for domain, questions in domain_questions.items():
        domain_score = 0
        for q in questions:
            response = row.get(q, "Siempre")
            score = score_map.get(response, 0)
            if q in reverse_questions:
                score = 4 - score
            domain_score += score
            total_score += score
        domain_scores[domain] = domain_score
    
    if total_score >= 125:
        total_risk = "Muy Alto"
    elif total_score >= 100:
        total_risk = "Alto"
    elif total_score >= 75:
        total_risk = "Medio"
    elif total_score >= 50:
        total_risk = "Bajo"
    else:
        total_risk = "Insignificante"
    
    domain_risk_levels = {}
    for domain, score in domain_scores.items():
        max_score = len(domain_questions[domain]) * 4
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        if percentage >= 80:
            domain_risk_levels[domain] = "Muy Alto"
        elif percentage >= 60:
            domain_risk_levels[domain] = "Alto"
        elif percentage >= 40:
            domain_risk_levels[domain] = "Medio"
        elif percentage >= 20:
            domain_risk_levels[domain] = "Bajo"
        else:
            domain_risk_levels[domain] = "Insignificante"
    
    return total_score, total_risk, domain_scores, domain_risk_levels

@st.cache_data
def generate_recommendations(guia_i_analysis, guia_ii_analysis):
    """Generate recommendations based on analysis."""
    recommendations = []
    total_employees = guia_i_analysis.get('Total Empleados', 1)
    
    positive_responses = guia_i_analysis.get('Empleados con Respuestas Positivas', 0)
    if positive_responses > 0:
        percentage = (positive_responses / total_employees) * 100
        recommendations.append(f"{positive_responses} empleados ({percentage:.1f}%) reportaron eventos traumáticos o síntomas (Guía I). Implementar evaluaciones psicológicas y programas de apoyo.")
    
    high_risk_depts = [dept for dept, count in guia_i_analysis.get('Respuestas Positivas por Departamento', {}).items() if count > 0]
    if high_risk_depts:
        recommendations.append(f"Departamentos con respuestas positivas (Guía I): {', '.join(high_risk_depts)}. Priorizar intervenciones en estas áreas.")
    
    risk_dist = guia_ii_analysis.get('Distribución de Riesgo Total', {})
    high_risk_count = sum(risk_dist.get(level, 0) for level in ["Alto", "Muy Alto"])
    if high_risk_count > 0:
        percentage = (high_risk_count / total_employees) * 100
        recommendations.append(f"{high_risk_count} empleados ({percentage:.1f}%) en riesgo Alto o Muy Alto (Guía II). Revisar condiciones laborales y liderazgo.")
    
    domain_risks = guia_ii_analysis.get('Riesgo por Dominio', {})
    high_risk_domains = [domain for domain, dist in domain_risks.items() if sum(dist.get(level, 0) for level in ["Alto", "Muy Alto"]) > 0]
    if high_risk_domains:
        recommendations.append(f"Dominios con riesgo Alto o Muy Alto (Guía II): {', '.join(high_risk_domains)}. Implementar mejoras específicas en estas áreas.")
    
    return recommendations if recommendations else ["No se identificaron riesgos significativos. Mantener monitoreo regular."]

@st.cache_data
def generate_statistical_analysis(df):
    """Generate statistical analysis for Guía I and II."""
    guia_i_analysis = {}
    guia_ii_analysis = {}
    
    symptom_cols = [item[0] for section in guia_i_questions[1:] for item in section["items"]]
    if any(col in df.columns for col in symptom_cols):
        guia_i_analysis['Total Empleados'] = len(df)
        df['Respuesta Positiva (Guía I)'] = df.apply(has_positive_response_guia_i, axis=1)
        positive_responses = df['Respuesta Positiva (Guía I)'].sum()
        guia_i_analysis['Empleados con Respuestas Positivas'] = positive_responses
        guia_i_analysis['Porcentaje con Respuestas Positivas'] = (positive_responses / len(df)) * 100 if len(df) > 0 else 0
        
        category_counts = {}
        for section in guia_i_questions[1:]:
            section_cols = [item[0] for item in section["items"]]
            category_counts[section["section"]] = df[section_cols].eq('Sí').sum().sum()
        guia_i_analysis['Respuestas Positivas por Categoría'] = category_counts
        
        if '¿En qué departamento labora?' in df.columns:
            dept_positive = df[df['Respuesta Positiva (Guía I)'] == True]['¿En qué departamento labora?'].value_counts().to_dict()
            guia_i_analysis['Respuestas Positivas por Departamento'] = dept_positive
        
        if '¿Cuál es tu género?' in df.columns:
            gender_positive = df[df['Respuesta Positiva (Guía I)'] == True]['¿Cuál es tu género?'].value_counts().to_dict()
            guia_i_analysis['Respuestas Positivas por Género'] = gender_positive
    
    guia_ii_cols = [item[0] for section in guia_ii_questions for item in section["items"]]
    domain_questions = {section["section"]: [item[0] for item in section["items"]] for section in guia_ii_questions}
    
    if any(col in df.columns for col in guia_ii_cols):
        guia_ii_analysis['Total Empleados'] = len(df)
        
        scores = df.apply(lambda row: calculate_risk_score_guia_ii(row, guia_ii_cols, domain_questions), axis=1, result_type='expand')
        df['Puntaje Total (Guía II)'] = scores[0]
        df['Nivel de Riesgo Total (Guía II)'] = scores[1]
        for domain in domain_questions:
            df[f'Puntaje {domain}'] = scores[2].apply(lambda x: x[domain])
            df[f'Nivel de Riesgo {domain}'] = scores[3].apply(lambda x: x[domain])
        
        risk_dist_total = df['Nivel de Riesgo Total (Guía II)'].value_counts().to_dict()
        guia_ii_analysis['Distribución de Riesgo Total'] = risk_dist_total
        
        domain_risks = {}
        for domain in domain_questions:
            domain_risks[domain] = df[f'Nivel de Riesgo {domain}'].value_counts().to_dict()
        guia_ii_analysis['Riesgo por Dominio'] = domain_risks
        
        negative_counts = {}
        for col in guia_ii_cols:
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
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        desc_stats = df[numeric_cols].describe().round(2)
        guia_i_analysis['Descriptivas Numéricas'] = desc_stats.to_dict()
    
    logger.info("Statistical analysis completed")
    return guia_i_analysis, guia_ii_analysis, df

# Visualization functions
def plot_positive_responses_guia_i(guia_i_analysis, temp_dir, palette):
    if 'Porcentaje con Respuestas Positivas' not in guia_i_analysis or guia_i_analysis['Porcentaje con Respuestas Positivas'] == 0:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(['Con Respuestas Positivas', 'Sin Respuestas Positivas'],
           [guia_i_analysis['Porcentaje con Respuestas Positivas'], 100 - guia_i_analysis['Porcentaje con Respuestas Positivas']],
           color=palette[2])
    ax.set_title('Porcentaje de Empleados con Respuestas Positivas (Guía I)')
    ax.set_ylabel('Porcentaje (%)')
    ax.set_ylim(0, 100)
    path = os.path.join(temp_dir, f'positive_responses_guia_i_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Bar', 'Porcentaje Respuestas Positivas (Guía I)', path)

def plot_category_responses_guia_i(guia_i_analysis, temp_dir, palette):
    if 'Respuestas Positivas por Categoría' not in guia_i_analysis or not any(guia_i_analysis['Respuestas Positivas por Categoría'].values()):
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    categories = list(guia_i_analysis['Respuestas Positivas por Categoría'].keys())
    counts = list(guia_i_analysis['Respuestas Positivas por Categoría'].values())
    ax.bar(categories, counts, color=palette[2])
    ax.set_title('Respuestas Positivas por Categoría (Guía I)')
    ax.set_xlabel('Categoría')
    ax.set_ylabel('Número de Respuestas Positivas')
    ax.tick_params(axis='x', rotation=45, labelright=True)
    path = os.path.join(temp_dir, f'category_responses_guia_i_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Bar', 'Respuestas Positivas por Categoría (Guía I)', path)

def plot_dept_positive_guia_i(guia_i_analysis, temp_dir, palette):
    if 'Respuestas Positivas por Departamento' not in guia_i_analysis or not guia_i_analysis['Respuestas Positivas por Departamento']:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    depts = list(guia_i_analysis['Respuestas Positivas por Departamento'].keys())
    counts = list(guia_i_analysis['Respuestas Positivas por Departamento'].values())
    ax.bar(depts, counts, color=palette[2])
    ax.set_title('Respuestas Positivas por Departamento (Guía I)')
    ax.set_xlabel('Departamento')
    ax.set_ylabel('Número de Empleados')
    ax.tick_params(axis='x', rotation=45, labelright=True)
    path = os.path.join(temp_dir, f'dept_positive_guia_i_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Bar', 'Respuestas Positivas por Departamento (Guía I)', path)

def plot_risk_distribution_guia_ii(guia_ii_analysis, temp_dir, palette):
    if 'Distribución de Riesgo Total' not in guia_ii_analysis or not guia_ii_analysis['Distribución de Riesgo Total']:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    risk_counts = pd.Series(guia_ii_analysis['Distribución de Riesgo Total']).reindex(
        ["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"], fill_value=0)
    ax.pie(risk_counts, labels=risk_counts.index, autopct='%1.1f%%', colors=palette)
    ax.set_title('Distribución de Riesgo Psicosocial Total (Guía II)')
    path = os.path.join(temp_dir, f'risk_distribution_guia_ii_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Pie', 'Distribución de Riesgo Total (Guía II)', path)

def plot_negative_responses_guia_ii(guia_ii_analysis, temp_dir, palette):
    if 'Conteo de Respuestas Negativas (Guía II)' not in guia_ii_analysis:
        return None
    domain_negatives = {}
    for section in guia_ii_questions:
        domain = section["section"]
        domain_cols = [item[0] for item in section["items"]]
        domain_negatives[domain] = sum(guia_ii_analysis['Conteo de Respuestas Negativas (Guía II)'].get(col, 0) for col in domain_cols)
    if not any(domain_negatives.values()):
        return None
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(domain_negatives.keys(), domain_negatives.values(), color=palette[2])
    ax.set_title('Respuestas Negativas por Dominio (Guía II)')
    ax.set_xlabel('Dominio')
    ax.set_ylabel('Número de Respuestas Negativas')
    ax.tick_params(axis='x', rotation=45, labelright=True)
    fig.tight_layout()
    path = os.path.join(temp_dir, f'negative_responses_guia_ii_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Bar', 'Respuestas Negativas por Dominio (Guía II)', path)

def plot_age_distribution(df, temp_dir, palette):
    if '¿Qué edad tienes? (ej. 21)' not in df.columns or df['¿Qué edad tienes? (ej. 21)'].isna().all():
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(df['¿Qué edad tienes? (ej. 21)'].dropna(), kde=True, color=palette[3], ax=ax)
    ax.set_title('Distribución de Edad')
    ax.set_xlabel('Edad')
    ax.set_ylabel('Frecuencia')
    path = os.path.join(temp_dir, f'age_distribution_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Histograma', 'Distribución de Edad', path)

def plot_gender_positive_guia_i(guia_i_analysis, temp_dir, palette):
    if 'Respuestas Positivas por Género' not in guia_i_analysis or not guia_i_analysis['Respuestas Positivas por Género']:
        return None
    fig, ax = plt.subplots(figsize=(8, 5))
    genders = list(guia_i_analysis['Respuestas Positivas por Género'].keys())
    counts = list(guia_i_analysis['Respuestas Positivas por Género'].values())
    ax.bar(genders, counts, color=palette[1])
    ax.set_title('Respuestas Positivas por Género (Guía I)')
    ax.set_xlabel('Género')
    ax.set_ylabel('Número de Empleados')
    ax.tick_params(axis='x', rotation=45, labelright=True)
    path = os.path.join(temp_dir, f'gender_positive_guia_i_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Bar', 'Respuestas Positivas por Género (Guía I)', path)

def plot_dept_risk_guia_ii(guia_ii_analysis, temp_dir, palette):
    if 'Riesgo por Departamento (Guía II)' not in guia_ii_analysis or not guia_ii_analysis['Riesgo por Departamento (Guía II)']:
        return None
    dept_risk_df = pd.DataFrame(guia_ii_analysis['Riesgo por Departamento (Guía II)']).T
    dept_risk_df = dept_risk_df.reindex(columns=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"], fill_value=0)
    if dept_risk_df.empty:
        return None
    fig, ax = plt.subplots(figsize=(12, 6))
    dept_risk_df.plot(kind='bar', stacked=True, color=palette, ax=ax)
    ax.set_title('Distribución de Riesgo por Departamento (Guía II)')
    ax.set_xlabel('Departamento')
    ax.set_ylabel('Número de Empleados')
    ax.tick_params(axis='x', rotation=45, labelright=True)
    ax.legend(title='Nivel de Riesgo')
    path = os.path.join(temp_dir, f'dept_risk_guia_ii_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Stacked Bar', 'Distribución de Riesgo por Departamento (Guía II)', path)

def plot_gender_risk_guia_ii(guia_ii_analysis, temp_dir, palette):
    if 'Riesgo por Género (Guía II)' not in guia_ii_analysis or not guia_ii_analysis['Riesgo por Género (Guía II)']:
        return None
    gender_risk_df = pd.DataFrame(guia_ii_analysis['Riesgo por Género (Guía II)']).T
    gender_risk_df = gender_risk_df.reindex(columns=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"], fill_value=0)
    if gender_risk_df.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 5))
    gender_risk_df.plot(kind='bar', stacked=True, color=palette, ax=ax)
    ax.set_title('Distribución de Riesgo por Género (Guía II)')
    ax.set_xlabel('Género')
    ax.set_ylabel('Número de Empleados')
    ax.tick_params(axis='x', rotation=45, labelright=True)
    ax.legend(title='Nivel de Riesgo')
    path = os.path.join(temp_dir, f'gender_risk_guia_ii_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Stacked Bar', 'Distribución de Riesgo por Género (Guía II)', path)

def plot_score_boxplot_dept_guia_ii(df, temp_dir, palette):
    if 'Puntaje Total (Guía II)' not in df.columns or '¿En qué departamento labora?' not in df.columns or df['Puntaje Total (Guía II)'].isna().all():
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(x='¿En qué departamento labora?', y='Puntaje Total (Guía II)', data=df, palette=palette, ax=ax)
    ax.set_title('Distribución de Puntajes Totales por Departamento (Guía II)')
    ax.set_xlabel('Departamento')
    ax.set_ylabel('Puntaje Total')
    ax.tick_params(axis='x', rotation=45, labelright=True)
    path = os.path.join(temp_dir, f'score_boxplot_dept_guia_ii_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Boxplot', 'Distribución de Puntajes Totales por Departamento (Guía II)', path)

def plot_domain_correlation_guia_ii(df, temp_dir, domain_questions):
    domain_cols = [f'Puntaje {domain}' for domain in domain_questions if f'Puntaje {domain}' in df.columns]
    if not domain_cols or df[domain_cols].isna().all().any():
        return None
    fig, ax = plt.subplots(figsize=(12, 8))
    corr_matrix = df[domain_cols].corr()
    sns.heatmap(corr_matrix, annot=True, cmap='Pastel1', vmin=-1, vmax=1, ax=ax)
    ax.set_title('Matriz de Correlación de Puntajes por Dominio (Guía II)')
    path = os.path.join(temp_dir, f'domain_correlation_guia_ii_{uuid.uuid4()}.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return ('Heatmap', 'Matriz de Correlación de Puntajes por Dominio (Guía II)', path)

@st.cache_data
def generate_visualizations(df, temp_dir, guia_i_analysis, guia_ii_analysis):
    """Generate visualizations for analysis."""
    visualizations = []
    sns.set_style("whitegrid")
    n_categories = max(5, len(df['¿En qué departamento labora?'].unique()) if '¿En qué departamento labora?' in df.columns else 5)
    pastel_palette = sns.color_palette("pastel", n_colors=n_categories)
    domain_questions = {section["section"]: [item[0] for item in section["items"]] for section in guia_ii_questions}
    
    viz_functions = [
        (plot_positive_responses_guia_i, (guia_i_analysis, temp_dir, pastel_palette)),
        (plot_category_responses_guia_i, (guia_i_analysis, temp_dir, pastel_palette)),
        (plot_dept_positive_guia_i, (guia_i_analysis, temp_dir, pastel_palette)),
        (plot_risk_distribution_guia_ii, (guia_ii_analysis, temp_dir, pastel_palette)),
        (plot_negative_responses_guia_ii, (guia_ii_analysis, temp_dir, pastel_palette)),
        (plot_age_distribution, (df, temp_dir, pastel_palette)),
        (plot_gender_positive_guia_i, (guia_i_analysis, temp_dir, pastel_palette)),
        (plot_dept_risk_guia_ii, (guia_ii_analysis, temp_dir, pastel_palette)),
        (plot_gender_risk_guia_ii, (guia_ii_analysis, temp_dir, pastel_palette)),
        (plot_score_boxplot_dept_guia_ii, (df, temp_dir, pastel_palette)),
        (plot_domain_correlation_guia_ii, (df, temp_dir, domain_questions))
    ]
    
    for func, args in viz_functions:
        try:
            result = func(*args)
            if result:
                visualizations.append(result)
        except Exception as e:
            logger.error(f"Failed to generate visualization {func.__name__}: {str(e)}")
    
    logger.info(f"Generated {len(visualizations)} visualizations")
    return visualizations

# Sidebar
st.sidebar.image("assets/FOBO2.png", width=100)
st.sidebar.title("Evaluación NOM-035")
section = st.sidebar.radio("Ir a sección:", ["📋 Evaluación", "📥 Descargar Reporte", "🔄 Reiniciar Datos"], key="sidebar_section")

# Evaluation section
if section == "📋 Evaluación":
    st.title("🧠 Evaluación Psicosocial - NOM-035 Guía I y II")
    st.markdown("Por favor responda con honestidad. La información será confidencial.")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        if not st.session_state.show_guia_ii:
            with st.form("guia_i_form"):
                st.header("Guía I: Identificación de Eventos Traumáticos")
                respuestas = st.session_state.guia_i_responses or {}
                
                for section_data in guia_i_questions:
                    st.subheader(section_data["section"])
                    for idx, (q, tipo, params) in enumerate(section_data["items"]):
                        st.markdown(f"**{q}**")
                        if tipo == "text":
                            respuestas[q] = st.text_input("", key=f"gi_q{idx}_{q}", value=respuestas.get(q, ""),
                                                        max_chars=params.get("max_length"), help=f"Ingrese {q.lower()}")
                        elif tipo == "number":
                            min_val = params.get("min_value", 0)
                            default_val = max(min_val, respuestas.get(q, min_val))
                            respuestas[q] = st.number_input("", min_value=min_val,
                                                         max_value=params.get("max_value", 1000), step=1,
                                                         key=f"gi_q{idx}_{q}", value=default_val,
                                                         help=f"Ingrese un número para {q.lower()}")
                        elif isinstance(tipo, list):
                            respuestas[q] = st.radio("", tipo, horizontal=True, key=f"gi_q{idx}_{q}",
                                                   index=tipo.index(respuestas.get(q)) if respuestas.get(q) in tipo else 0,
                                                   help=f"Seleccione una opción para {q.lower()}",
                                                   label_visibility="collapsed")
                
                submit_button = st.form_submit_button("✅ Enviar Guía I", help="Enviar respuestas de Guía I", type="primary")
                
                if submit_button:
                    try:
                        is_valid, errors = validate_form(respuestas, guia_i_questions)
                        if is_valid:
                            st.session_state.guia_i_responses = respuestas
                            has_positive = has_positive_response_guia_i(respuestas)
                            st.session_state.show_guia_ii = has_positive
                            if not has_positive:
                                st.session_state.responses.append(respuestas)
                                if log_response(respuestas, temp_dir):
                                    st.success("✅ ¡Evaluación Guía I completada! No se requiere Guía II.")
                                    st.session_state.guia_i_responses = None
                                else:
                                    st.session_state.form_error = "Error al guardar respuestas, por favor intenta de nuevo."
                                    st.error(st.session_state.form_error)
                            else:
                                st.success("✅ Guía I enviada. Se detectaron respuestas positivas, por favor complete la Guía II.")
                                st.rerun()
                        else:
                            st.warning("⚠️ Corrija los siguientes errores:")
                            for error in errors:
                                st.write(f"- {error}")
                    except Exception as e:
                        logger.error(f"Error processing Guía I submission: {str(e)}")
                        st.session_state.form_error = str(e)
                        st.error(f"❌ Error al procesar la evaluación: {str(e)}")
                
                if st.session_state.form_error:
                    if st.form_submit_button("🔄 Reintentar", help="Reintentar el envío"):
                        st.session_state.form_error = None
                        st.rerun()
        else:
            with st.form("guia_ii_form"):
                st.header("Guía II: Factores de Riesgo Psicosocial")
                respuestas = st.session_state.guia_i_responses.copy() if st.session_state.guia_i_responses else {}
                
                for section_data in guia_ii_questions:
                    st.subheader(section_data["section"])
                    for idx, (q, tipo, params) in enumerate(section_data["items"]):
                        st.markdown(f"**{q}**")
                        respuestas[q] = st.radio("", tipo, horizontal=True, key=f"gii_q{idx}_{q}",
                                               index=tipo.index(respuestas.get(q)) if respuestas.get(q) in tipo else 0,
                                               help=f"Seleccione una opción para {q.lower()}",
                                               label_visibility="collapsed")
                
                submit_button = st.form_submit_button("✅ Enviar Guía II", help="Enviar respuestas de Guía II", type="primary")
                
                if submit_button:
                    try:
                        is_valid, errors = validate_form(respuestas, guia_i_questions + guia_ii_questions)
                        if is_valid:
                            st.session_state.responses.append(respuestas)
                            if log_response(respuestas, temp_dir):
                                st.session_state.show_guia_ii = False
                                st.session_state.guia_i_responses = None
                                st.success("✅ ¡Evaluación Guía I y II completada exitosamente!")
                            else:
                                st.session_state.form_error = "Error al guardar respuestas, por favor intenta de nuevo."
                                st.error(st.session_state.form_error)
                        else:
                            st.warning("⚠️ Corrija los siguientes errores:")
                            for error in errors:
                                st.write(f"- {error}")
                    except Exception as e:
                        logger.error(f"Error processing Guía II submission: {str(e)}")
                        st.session_state.form_error = str(e)
                        st.error(f"❌ Error al procesar la evaluación: {str(e)}")
                
                if st.session_state.form_error:
                    if st.form_submit_button("🔄 Reintentar", help="Reintentar el envío"):
                        st.session_state.form_error = None
                        st.rerun()

# Download report section
elif section == "📥 Descargar Reporte":
    st.title("📥 Reporte Consolidado")
    
    access_key = st.text_input("🔑 Ingrese la clave de acceso:", type="password", help="Ingrese la clave para descargar el reporte")
    
    if st.session_state.responses and access_key == ACCESS_KEY:
        try:
            with st.spinner("Generando reporte..."):
                df = pd.DataFrame(st.session_state.responses)
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    guia_i_analysis, guia_ii_analysis, df = generate_statistical_analysis(df)
                    visualizations = generate_visualizations(df, temp_dir, guia_i_analysis, guia_ii_analysis)
                    recommendations = generate_recommendations(guia_i_analysis, guia_ii_analysis)
                    
                    wb = Workbook()
                    ws_summary = wb.active
                    ws_summary.title = "Resumen Ejecutivo"
                    ws_summary.cell(1, 1).value = "Reporte NOM-035 Guía I y II - Resumen Ejecutivo"
                    ws_summary.cell(2, 1).value = f"Fecha: {datetime.now().strftime('%Y-%m-%d')}"
                    ws_summary.cell(4, 1).value = "Hallazgos Clave:"
                    for i, rec in enumerate(recommendations, start=5):
                        ws_summary.cell(i, 1).value = f"- {rec}"
                    
                    ws_data = wb.create_sheet("Datos Crudos")
                    ws_data.append(df.columns.tolist())
                    for row in df.itertuples(index=False):
                        ws_data.append([sanitize_text(str(cell)) for cell in row])
                    
                    ws_stats = wb.create_sheet("Análisis Estadístico")
                    row = 1
                    
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
                        for r, idx in enumerate(dept_risk_ii.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(dept_risk_ii.columns, start=2):
                                ws_stats.cell(r, c).value = dept_risk_ii.loc[idx, col]
                        row += len(dept_risk_ii) + 2
                    
                    if 'Riesgo por Género (Guía II)' in guia_ii_analysis:
                        ws_stats.cell(row, 1).value = "Riesgo por Género (Guía II)"
                        row += 1
                        gender_risk_ii = pd.DataFrame(guia_ii_analysis['Riesgo por Género (Guía II)'])
                        for r, idx in enumerate(gender_risk_ii.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(gender_risk_ii.columns, start=2):
                                ws_stats.cell(r, c).value = gender_risk_ii.loc[idx, col]
                        row += len(gender_risk_ii) + 2
                    
                    if 'Descriptivas Numéricas' in guia_i_analysis:
                        ws_stats.cell(row, 1).value = "Estadísticas Descriptivas (Numéricas)"
                        row += 1
                        desc_df = pd.DataFrame(guia_i_analysis['Descriptivas Numéricas'])
                        for r, idx in enumerate(desc_df.index, start=row):
                            ws_stats.cell(r, 1).value = idx
                            for c, col in enumerate(desc_df.columns, start=2):
                                ws_stats.cell(r, c).value = desc_df.loc[idx, col]
                        row += len(desc_df) + 2
                    
                    ws_viz = wb.create_sheet("Visualizaciones")
                    row_viz = 1
                    for viz_type, col, img_path in visualizations:
                        ws_viz.cell(row_viz, 1).value = f"{viz_type}: {col}"
                        img = Image(img_path)
                        img.anchor = f'B{row_viz}'
                        ws_viz.add_image(img)
                        row_viz += 30
                    
                    excel_io = io.BytesIO()
                    wb.save(excel_io)
                    excel_io.seek(0)
                    
                    csv_io = io.StringIO()
                    df.to_csv(csv_io, index=False)
                    csv_io.seek(0)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "📤 Descargar Excel",
                            data=excel_io,
                            file_name="NOM035_Guia1y2_Analysis.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Descargar el reporte en formato Excel"
                        )
                    with col2:
                        st.download_button(
                            "📤 Descargar CSV",
                            data=csv_io.getvalue(),
                            file_name="NOM035_Guia1y2.csv",
                            mime="text/csv",
                            help="Descargar el reporte en formato CSV"
                        )
                    logger.info("Report generated successfully")
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            st.error(f"❌ Error al generar el reporte: {str(e)}")
    elif access_key and access_key != ACCESS_KEY:
        logger.warning("Invalid access key attempt")
        st.error("🔐 Clave de acceso incorrecta.")
    else:
        st.warning("⚠️ Ingrese la clave de acceso para descargar los datos.")

# Reset data section
elif section == "🔄 Reiniciar Datos":
    st.title("🔄 Reiniciar Datos")
    st.markdown("Ingrese la contraseña para reiniciar todas las respuestas y el log. Esta acción no se puede deshacer.")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with st.form("reset_form"):
            reset_password = st.text_input("🔑 Contraseña para reiniciar:", type="password", help="Ingrese la contraseña para reiniciar los datos")
            reset_button = st.form_submit_button("🔄 Reiniciar", help="Reiniciar todos los datos")
            
            if reset_button:
                reset_data(reset_password, temp_dir)
