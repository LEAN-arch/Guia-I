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

# Page configuration
st.set_page_config(page_title="🧠 NOM-035 Guía I y II", layout="centered")

# Access keys (Note: Use environment variables in production for security)
ACCESS_KEY = "NOM035_ACCESS_2025"
RESET_PASSWORD = "RESET_NOM035_2025"

# Custom CSS for button styling
st.markdown("""
<style>
.stButton>button {
    margin: 5px;
}
.primary-button {
    background-color: #28a745;
    color: white;
    border-radius: 5px;
}
.secondary-button {
    background-color: #6c757d;
    color: white;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "responses" not in st.session_state:
    st.session_state.responses = []
if "show_guia_ii" not in st.session_state:
    st.session_state.show_guia_ii = False
if "guia_i_responses" not in st.session_state:
    st.session_state.guia_i_responses = None

# Questions for Guía I
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

# Questions for Guía II
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

# Function to log responses
def log_response(response, temp_dir):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_data = {'Timestamp': timestamp, **response}
        log_df = pd.DataFrame([log_data])
        log_file = os.path.join(temp_dir, 'responses_log.csv')
        mode = 'a' if os.path.exists(log_file) else 'w'
        header = not os.path.exists(log_file)
        log_df.to_csv(log_file, mode=mode, header=header, index=False)
    except PermissionError:
        st.error("❌ Error: No se pudo escribir en el archivo de log debido a permisos.")
    except Exception as e:
        st.error(f"❌ Error al guardar en el log: {str(e)}")

# Function to reset data
def reset_data(password, temp_dir):
    if password == RESET_PASSWORD:
        st.session_state.responses = []
        st.session_state.show_guia_ii = False
        st.session_state.guia_i_responses = None
        try:
            log_file = os.path.join(temp_dir, 'responses_log.csv')
            with open(log_file, 'w') as f:
                f.write('')
            st.success("✅ Datos y log reiniciados exitosamente.")
        except PermissionError:
            st.error("❌ Error: No se pudo reiniciar el log debido a permisos.")
        except Exception as e:
            st.error(f"❌ Error al reiniciar el log: {str(e)}")
    else:
        st.error("🔐 Contraseña incorrecta para reiniciar datos.")

# Function to check positive responses in Guía I
def has_positive_response_guia_i(row):
    symptom_cols = [item[0] for section in guia_i_questions[1:] for item in section["items"]]
    return any(row.get(col, 'No') == 'Sí' for col in symptom_cols)

# Function to calculate Guía II risk score
def calculate_risk_score_guia_ii(row, guia_ii_cols, domain_questions):
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
        percentage = (score / max_score) * 100
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

# Function to generate recommendations
def generate_recommendations(guia_i_analysis, guia_ii_analysis):
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

# Function to generate statistical analysis
def generate_statistical_analysis(df):
    guia_i_analysis = {}
    guia_ii_analysis = {}
    
    symptom_cols = [item[0] for section in guia_i_questions[1:] for item in section["items"]]
    if any(col in df.columns for col in symptom_cols):
        guia_i_analysis['Total Empleados'] = len(df)
        df['Respuesta Positiva (Guía I)'] = df.apply(has_positive_response_guia_i, axis=1)
        positive_responses = df['Respuesta Positiva (Guía I)'].sum()
        guia_i_analysis['Empleados con Respuestas Positivas'] = positive_responses
        guia_i_analysis['Porcentaje con Respuestas Positivas'] = (positive_responses / len(df)) * 100
        
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
    
    return guia_i_analysis, guia_ii_analysis, df

# Function to generate visualizations
def generate_visualizations(df, temp_dir, guia_i_analysis, guia_ii_analysis):
    visualizations = []
    sns.set_style("whitegrid")
    pastel_palette = sns.color_palette("pastel", n_colors=5)
    
    if 'Porcentaje con Respuestas Positivas' in guia_i_analysis:
        plt.figure(figsize=(6, 4))
        plt.bar(['Con Respuestas Positivas', 'Sin Respuestas Positivas'], 
                [guia_i_analysis['Porcentaje con Respuestas Positivas'], 100 - guia_i_analysis['Porcentaje con Respuestas Positivas']],
                color=pastel_palette[2])
        plt.title('Porcentaje de Empleados con Respuestas Positivas (Guía I)')
        plt.ylabel('Porcentaje (%)')
        plt.ylim(0, 100)
        path = os.path.join(temp_dir, f'positive_responses_guia_i_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Bar', 'Porcentaje Respuestas Positivas (Guía I)', path))
    
    if 'Respuestas Positivas por Categoría' in guia_i_analysis:
        plt.figure(figsize=(10, 6))
        categories = list(guia_i_analysis['Respuestas Positivas por Categoría'].keys())
        counts = list(guia_i_analysis['Respuestas Positivas por Categoría'].values())
        plt.bar(categories, counts, color=pastel_palette[2])
        plt.title('Respuestas Positivas por Categoría (Guía I)')
        plt.xlabel('Categoría')
        plt.ylabel('Número de Respuestas Positivas')
        plt.xticks(rotation=45, ha='right')
        path = os.path.join(temp_dir, f'category_responses_guia_i_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Bar', 'Respuestas Positivas por Categoría (Guía I)', path))
    
    if 'Respuestas Positivas por Departamento' in guia_i_analysis:
        plt.figure(figsize=(10, 6))
        depts = list(guia_i_analysis['Respuestas Positivas por Departamento'].keys())
        counts = list(guia_i_analysis['Respuestas Positivas por Departamento'].values())
        plt.bar(depts, counts, color=pastel_palette[2])
        plt.title('Respuestas Positivas por Departamento (Guía I)')
        plt.xlabel('Departamento')
        plt.ylabel('Número de Empleados')
        plt.xticks(rotation=45, ha='right')
        path = os.path.join(temp_dir, f'dept_positive_guia_i_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Bar', 'Respuestas Positivas por Departamento (Guía I)', path))
    
    if 'Distribución de Riesgo Total' in guia_ii_analysis:
        plt.figure(figsize=(6, 4))
        risk_counts = pd.Series(guia_ii_analysis['Distribución de Riesgo Total']).reindex(
            ["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"], fill_value=0)
        plt.pie(risk_counts, labels=risk_counts.index, autopct='%1.1f%%', colors=pastel_palette)
        plt.title('Distribución de Riesgo Psicosocial Total (Guía II)')
        path = os.path.join(temp_dir, f'risk_distribution_guia_ii_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Pie', 'Distribución de Riesgo Total (Guía II)', path))
    
    if 'Conteo de Respuestas Negativas (Guía II)' in guia_ii_analysis:
        domain_negatives = {}
        for section in guia_ii_questions:
            domain = section["section"]
            domain_cols = [item[0] for item in section["items"]]
            domain_negatives[domain] = sum(guia_ii_analysis['Conteo de Respuestas Negativas (Guía II)'].get(col, 0) for col in domain_cols)
        
        plt.figure(figsize=(12, 6))
        plt.bar(domain_negatives.keys(), domain_negatives.values(), color=pastel_palette[2])
        plt.title('Respuestas Negativas por Dominio (Guía II)')
        plt.xlabel('Dominio')
        plt.ylabel('Número de Respuestas Negativas')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        path = os.path.join(temp_dir, f'negative_responses_guia_ii_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Bar', 'Respuestas Negativas por Dominio (Guía II)', path))
    
    if '¿Qué edad tienes? (ej. 21)' in df.columns:
        plt.figure(figsize=(6, 4))
        sns.histplot(df['¿Qué edad tienes? (ej. 21)'].dropna(), kde=True, color=pastel_palette[3])
        plt.title('Distribución de Edad')
        plt.xlabel('Edad')
        plt.ylabel('Frecuencia')
        path = os.path.join(temp_dir, f'age_distribution_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Histograma', 'Distribución de Edad', path))
    
    # Additional visualizations for Guía I
    if 'Respuestas Positivas por Género' in guia_i_analysis:
        plt.figure(figsize=(8, 5))
        genders = list(guia_i_analysis['Respuestas Positivas por Género'].keys())
        counts = list(guia_i_analysis['Respuestas Positivas por Género'].values())
        plt.bar(genders, counts, color=pastel_palette[1])
        plt.title('Respuestas Positivas por Género (Guía I)')
        plt.xlabel('Género')
        plt.ylabel('Número de Empleados')
        plt.xticks(rotation=45, ha='right')
        path = os.path.join(temp_dir, f'gender_positive_guia_i_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Bar', 'Respuestas Positivas por Género (Guía I)', path))
    
    # Additional visualizations for Guía II
    if 'Riesgo por Departamento (Guía II)' in guia_ii_analysis:
        plt.figure(figsize=(12, 6))
        dept_risk_df = pd.DataFrame(guia_ii_analysis['Riesgo por Departamento (Guía II)']).T
        dept_risk_df = dept_risk_df.reindex(columns=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"], fill_value=0)
        dept_risk_df.plot(kind='bar', stacked=True, color=pastel_palette, figsize=(12, 6))
        plt.title('Distribución de Riesgo por Departamento (Guía II)')
        plt.xlabel('Departamento')
        plt.ylabel('Número de Empleados')
        plt.xticks(rotation=45, ha='right')
        plt.legend(title='Nivel de Riesgo')
        path = os.path.join(temp_dir, f'dept_risk_guia_ii_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Stacked Bar', 'Distribución de Riesgo por Departamento (Guía II)', path))
    
    if 'Riesgo por Género (Guía II)' in guia_ii_analysis:
        plt.figure(figsize=(8, 5))
        gender_risk_df = pd.DataFrame(guia_ii_analysis['Riesgo por Género (Guía II)']).T
        gender_risk_df = gender_risk_df.reindex(columns=["Insignificante", "Bajo", "Medio", "Alto", "Muy Alto"], fill_value=0)
        gender_risk_df.plot(kind='bar', stacked=True, color=pastel_palette, figsize=(8, 5))
        plt.title('Distribución de Riesgo por Género (Guía II)')
        plt.xlabel('Género')
        plt.ylabel('Número de Empleados')
        plt.xticks(rotation=45, ha='right')
        plt.legend(title='Nivel de Riesgo')
        path = os.path.join(temp_dir, f'gender_risk_guia_ii_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Stacked Bar', 'Distribución de Riesgo por Género (Guía II)', path))
    
    # Boxplot for Guía II scores by department
    if 'Puntaje Total (Guía II)' in df.columns and '¿En qué departamento labora?' in df.columns:
        plt.figure(figsize=(10, 6))
        sns.boxplot(x='¿En qué departamento labora?', y='Puntaje Total (Guía II)', data=df, palette=pastel_palette)
        plt.title('Distribución de Puntajes Totales por Departamento (Guía II)')
        plt.xlabel('Departamento')
        plt.ylabel('Puntaje Total')
        plt.xticks(rotation=45, ha='right')
        path = os.path.join(temp_dir, f'score_boxplot_dept_guia_ii_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Boxplot', 'Distribución de Puntajes Totales por Departamento (Guía II)', path))
    
    # Heatmap for Guía II domain scores
    if any(f'Puntaje {domain}' in df.columns for domain in domain_questions):
        plt.figure(figsize=(12, 8))
        domain_cols = [f'Puntaje {domain}' for domain in domain_questions]
        corr_matrix = df[domain_cols].corr()
        sns.heatmap(corr_matrix, annot=True, cmap='Pastel1', vmin=-1, vmax=1)
        plt.title('Matriz de Correlación de Puntajes por Dominio (Guía II)')
        path = os.path.join(temp_dir, f'domain_correlation_guia_ii_{uuid.uuid4()}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Heatmap', 'Matriz de Correlación de Puntajes por Dominio (Guía II)', path))
    
    return visualizations

# Sidebar
st.sidebar.image("assets/FOBO2.png", width=100)
st.sidebar.title("Evaluación NOM-035")
section = st.sidebar.radio("Ir a sección:", ["📋 Evaluación", "📥 Descargar Reporte", "🔄 Reiniciar Datos"])

# Evaluation section
if section == "📋 Evaluación":
    st.title("🧠 Evaluación Psicosocial - NOM-035 Guía I y II")
    st.markdown("Por favor responda con honestidad. La información será confidencial.")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        if not st.session_state.show_guia_ii:
            with st.form("guia_i_form"):
                respuestas = {}
                for section_data in guia_i_questions:
                    with st.expander(section_data["section"], expanded=True):
                        for idx, (q, tipo) in enumerate(section_data["items"]):
                            st.markdown(f"**{q}**")
                            if tipo == "text":
                                respuestas[q] = st.text_input("", key=f"gi_q{idx}_{q}", value="")
                            elif tipo == "number":
                                respuestas[q] = st.number_input("", min_value=0, step=1, key=f"gi_q{idx}_{q}", value=0)
                            elif isinstance(tipo, list):
                                respuestas[q] = st.radio("", tipo, horizontal=True, key=f"gi_q{idx}_{q}")
                
                col1, col2 = st.columns(2)
                with col1:
                    enviar = st.form_submit_button("✅ Enviar Guía I", help="Enviar respuestas de Guía I", type="primary")
                with col2:
                    cancelar = st.form_submit_button("❌ Cancelar", help="Limpiar formulario", type="secondary")
                
                if enviar:
                    try:
                        if all(v != "" and v is not None for v in respuestas.values()):
                            st.session_state.guia_i_responses = respuestas
                            has_positive = has_positive_response_guia_i(respuestas)
                            if not has_positive:
                                st.session_state.responses.append(respuestas)
                                log_response(respuestas, temp_dir)
                                st.success("✅ ¡Evaluación Guía I completada! No se requiere Guía II.")
                            else:
                                st.session_state.show_guia_ii = True
                                st.success("✅ Guía I enviada. Se detectaron respuestas positivas, por favor complete la Guía II.")
                                st.rerun()  # Automatically move to Guía II
                        else:
                            st.warning("⚠️ Responde todas las preguntas antes de enviar.")
                    except Exception as e:
                        st.error(f"❌ Error al procesar la evaluación: {str(e)}")
                
                if cancelar:
                    st.session_state.guia_i_responses = None
                    st.success("✅ Formulario de Guía I limpiado.")
                    st.rerun()
        else:
            with st.form("guia_ii_form"):
                respuestas = st.session_state.guia_i_responses.copy()
                for section_data in guia_ii_questions:
                    with st.expander(section_data["section"], expanded=True):
                        for idx, (q, tipo) in enumerate(section_data["items"]):
                            st.markdown(f"**{q}**")
                            respuestas[q] = st.radio("", tipo, horizontal=True, key=f"gii_q{idx}_{q}")
                
                col1, col2 = st.columns(2)
                with col1:
                    enviar = st.form_submit_button("✅ Enviar Guía II", help="Enviar respuestas de Guía II", type="primary")
                with col2:
                    cancelar = st.form_submit_button("❌ Cancelar", help="Limpiar formulario", type="secondary")
                
                if enviar:
                    try:
                        if all(v != "" and v is not None for v in respuestas.values()):
                            st.session_state.responses.append(respuestas)
                            log_response(respuestas, temp_dir)
                            st.session_state.show_guia_ii = False
                            st.session_state.guia_i_responses = None
                            st.success("✅ ¡Evaluación Guía I y II completada exitosamente!")
                        else:
                            st.warning("⚠️ Responde todas las preguntas antes de enviar.")
                    except Exception as e:
                        st.error(f"❌ Error al procesar la evaluación: {str(e)}")
                
                if cancelar:
                    st.session_state.guia_i_responses = None
                    st.session_state.show_guia_ii = False
                    st.success("✅ Formulario de Guía II limpiado.")
                    st.rerun()

# Download report section
elif section == "📥 Descargar Reporte":
    st.title("📥 Reporte Consolidado")
    
    access_key = st.text_input("🔑 Ingrese la clave de acceso:", type="password")
    
    if st.session_state.responses and access_key == ACCESS_KEY:
        try:
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
                    ws_data.append([str(cell) for cell in row])
                
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
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                with col2:
                    st.download_button(
                        "📤 Descargar CSV",
                        data=csv_io.getvalue(),
                        file_name="NOM035_Guia1y2.csv",
                        mime="text/csv"
                    )
        except Exception as e:
            st.error(f"❌ Error al generar el reporte: {str(e)}")
    elif access_key and access_key != ACCESS_KEY:
        st.error("🔐 Clave de acceso incorrecta.")
    else:
        st.warning("⚠️ Ingrese la clave de acceso para descargar los datos.")

# Reset data section
elif section == "🔄 Reiniciar Datos":
    st.title("🔄 Reiniciar Datos")
    st.markdown("Ingrese la contraseña para reiniciar todas las respuestas y el log. Esta acción no se puede deshacer.")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with st.form("reset_form"):
            reset_password = st.text_input("🔑 Contraseña para reiniciar:", type="password")
            reset_button = st.form_submit_button("🔄 Reiniciar")
            
            if reset_button:
                reset_data(reset_password, temp_dir)
