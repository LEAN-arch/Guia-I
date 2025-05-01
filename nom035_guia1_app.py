import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.drawing.image import Image
import matplotlib.pyplot as plt
import seaborn as sns
import os
import tempfile
import numpy as np
from scipy import stats
from datetime import datetime

# Configuracion de pagina
st.set_page_config(page_title="🧠 NOM-035 Guia I", layout="centered")

# Clave de acceso predeterminada
ACCESS_KEY = "NOM035_G1"

if "responses" not in st.session_state:
    st.session_state.responses = []

# Sidebar
st.sidebar.image("assets/FOBO2.png", width=100)
st.sidebar.title("Evaluacion NOM-035")
section = st.sidebar.radio("Ir a seccion:", ["📋 Evaluacion", "📥 Descargar Reporte"])

# Preguntas (27 en total, organizadas en secciones)
questions = [
    {
        "section": "Informacion Personal",
        "items": [
            ("Nombre", "text"),
            ("Apellido Paterno", "text"),
            ("Apellido Materno", "text"),
            ("¿Que edad tienes? (ej. 21)", "number"),
            ("¿Cual es tu genero?", ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"]),
            ("¿Cuantos anos llevas trabajando aqui?", "number"),
            ("¿En que departamento labora?", ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Produccion", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administracion"]),
            ("¿Cual es su funcion?", ["Operador", "Tecnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"]),
            ("¿Donde se encuentra su lugar de trabajo?", ["Planta 1", "Planta 2", "Planta 3"]),
        ]
    },
    {
        "section": "Eventos Traumaticos Severos",
        "items": [
            ("¿Ha presenciado o sufrido un accidente grave?", ["Si", "No"]),
            ("¿Ha presenciado o sufrido un asalto?", ["Si", "No"]),
            ("¿Ha presenciado actos violentos con lesiones?", ["Si", "No"]),
            ("¿Ha presenciado o sufrido un secuestro?", ["Si", "No"]),
            ("¿Ha recibido amenazas?", ["Si", "No"]),
            ("¿Otra situacion que ponga en riesgo su vida o salud?", ["Si", "No"]),
        ]
    },
    {
        "section": "Sintomas de Reexperimentacion",
        "items": [
            ("¿Recuerdos recurrentes que causan malestar?", ["Si", "No"]),
            ("¿Suenos recurrentes que causan malestar?", ["Si", "No"]),
        ]
    },
    {
        "section": "Sintomas de Evitacion",
        "items": [
            ("¿Evita sentimientos o situaciones asociadas?", ["Si", "No"]),
            ("¿Evita actividades o lugares asociados?", ["Si", "No"]),
            ("¿Dificultad para recordar partes del evento?", ["Si", "No"]),
        ]
    },
    {
        "section": "Sintomas de Afectacion Emocional",
        "items": [
            ("¿Menor interes en actividades cotidianas?", ["Si", "No"]),
            ("¿Se siente alejado o distante de los demas?", ["Si", "No"]),
            ("¿Dificultad para expresar sentimientos?", ["Si", "No"]),
            ("¿Sensacion de vida corta o futuro limitado?", ["Si", "No"]),
        ]
    },
    {
        "section": "Sintomas de Activacion",
        "items": [
            ("¿Dificultad para dormir?", ["Si", "No"]),
            ("¿Irritabilidad o coraje?", ["Si", "No"]),
            ("¿Dificultad para concentrarse?", ["Si", "No"]),
            ("¿Nerviosismo o alerta constante?", ["Si", "No"]),
            ("¿Se sobresalta facilmente?", ["Si", "No"]),
        ]
    }
]

# Funcion para calcular puntaje de riesgo psicosocial
def calculate_risk_score(row, symptom_cols):
    score = sum(1 for col in symptom_cols if row[col] == 'Si')
    if score >= 10:
        return 'Alto'
    elif score >= 5:
        return 'Medio'
    else:
        return 'Bajo'

# Funcion para generar recomendaciones basadas en analisis
def generate_recommendations(analysis, risk_dist):
    recommendations = []
    high_risk = risk_dist.get('Alto', 0)
    if high_risk > 0:
        recommendations.append(f"{high_risk} empleados en riesgo alto. Implementar evaluaciones psicologicas inmediatas y programas de apoyo.")
    
    # Identificar departamentos de alto riesgo
    dept_risk = analysis.get('Riesgo por Departamento', {})
    high_risk_depts = [dept for dept, scores in dept_risk.items() if scores.get('Alto', 0) > 0]
    if high_risk_depts:
        recommendations.append(f"Departamentos con riesgo alto: {', '.join(high_risk_depts)}. Considerar intervenciones especificas.")
    
    # Identificar sintomas prevalentes
    symptom_counts = analysis.get('Conteo de Sintomas', {})
    top_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    if top_symptoms:
        symptoms = [s[0] for s in top_symptoms]
        recommendations.append(f"Sintomas mas comunes: {', '.join(symptoms)}. Enfocar programas de capacitacion en manejo de estres y trauma.")
    
    return recommendations if recommendations else ["No se identificaron riesgos significativos. Mantener monitoreo regular."]

# Funcion para generar analisis estadistico
def generate_statistical_analysis(df):
    analysis = {}
    
    # Estadisticas descriptivas para variables numericas
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if numeric_cols.any():
        desc_stats = df[numeric_cols].describe().round(2)
        analysis['Descriptivas Numericas'] = desc_stats.to_dict()
    
    # Frecuencias para variables categoricas
    categorical_cols = df.select_dtypes(include=['object']).columns
    freq_tables = {}
    for col in categorical_cols:
        freq = df[col].value_counts().to_dict()
        freq_tables[col] = freq
    analysis['Frecuencias Categoricas'] = freq_tables
    
    # Correlacion entre variables numericas
    if len(numeric_cols) > 1:
        correlation = df[numeric_cols].corr().round(2).to_dict()
        analysis['Correlacion'] = correlation
    
    # Analisis de sintomas (Si/No)
    symptom_cols = [q["items"][0][0] for q in questions[1:]]  # Preguntas de Si/No
    symptom_data = df[symptom_cols]
    symptom_counts = symptom_data.apply(lambda x: (x == 'Si').sum())
    analysis['Conteo de Sintomas'] = symptom_counts.to_dict()
    
    # Puntaje de riesgo psicosocial
    df['Nivel de Riesgo'] = df.apply(lambda row: calculate_risk_score(row, symptom_cols), axis=1)
    risk_dist = df['Nivel de Riesgo'].value_counts().to_dict()
    analysis['Distribucion de Riesgo'] = risk_dist
    
    # Riesgo por departamento
    if '¿En que departamento labora?' in df.columns:
        dept_risk = df.groupby('¿En que departamento labora?')['Nivel de Riesgo'].value_counts().unstack(fill_value=0).to_dict()
        analysis['Riesgo por Departamento'] = dept_risk
    
    # Riesgo por genero
    if '¿Cual es tu genero?' in df.columns:
        gender_risk = df.groupby('¿Cual es tu genero?')['Nivel de Riesgo'].value_counts().unstack(fill_value=0).to_dict()
        analysis['Riesgo por Genero'] = gender_risk
    
    return analysis, df

# Funcion para generar visualizaciones
def generate_visualizations(df, temp_dir):
    visualizations = []
    sns.set_style("whitegrid")
    palette = sns.color_palette("Blues", n_colors=5)
    
    # Distribucion de riesgo
    plt.figure(figsize=(6, 4))
    risk_counts = df['Nivel de Riesgo'].value_counts()
    plt.pie(risk_counts, labels=risk_counts.index, autopct='%1.1f%%', colors=palette)
    plt.title('Distribucion de Niveles de Riesgo Psicosocial')
    risk_path = os.path.join(temp_dir, 'risk_distribution.png')
    plt.savefig(risk_path, bbox_inches='tight')
    plt.close()
    visualizations.append(('Pie', 'Distribucion de Riesgo', risk_path))
    
    # Prevalencia de sintomas por categoria
    symptom_cols = [q["items"][0][0] for q in questions[1:]]
    symptom_counts = df[symptom_cols].apply(lambda x: (x == 'Si').sum())
    plt.figure(figsize=(8, 5))
    symptom_counts.plot(kind='bar', color=palette[2])
    plt.title('Prevalencia de Sintomas (Respuestas "Si")')
    plt.xlabel('Sintomas')
    plt.ylabel('Numero de Empleados')
    plt.xticks(rotation=45, ha='right')
    symptom_path = os.path.join(temp_dir, 'symptom_prevalence.png')
    plt.savefig(symptom_path, bbox_inches='tight')
    plt.close()
    visualizations.append(('Bar', 'Prevalencia de Sintomas', symptom_path))
    
    # Riesgo por departamento
    if '¿En que departamento labora?' in df.columns:
        plt.figure(figsize=(8, 5))
        sns.countplot(data=df, x='¿En que departamento labora?', hue='Nivel de Riesgo', palette=palette)
        plt.title('Nivel de Riesgo por Departamento')
        plt.xlabel('Departamento')
        plt.ylabel('Conteo')
        plt.xticks(rotation=45, ha='right')
        plt.legend(title='Nivel de Riesgo')
        dept_path = os.path.join(temp_dir, 'risk_by_department.png')
        plt.savefig(dept_path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Bar', 'Riesgo por Departamento', dept_path))
    
    # Distribucion de edad
    if '¿Que edad tienes? (ej. 21)' in df.columns:
        plt.figure(figsize=(6, 4))
        sns.histplot(df['¿Que edad tienes? (ej. 21)'], kde=True, color=palette[3])
        plt.title('Distribucion de Edad')
        plt.xlabel('Edad')
        plt.ylabel('Frecuencia')
        age_path = os.path.join(temp_dir, 'age_distribution.png')
        plt.savefig(age_path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Histograma', 'Distribucion de Edad', age_path))
    
    # Heatmap de correlacion
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 1:
        plt.figure(figsize=(6, 4))
        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap='Blues', vmin=-1, vmax=1)
        plt.title('Mapa de Calor de Correlaciones')
        corr_path = os.path.join(temp_dir, 'correlation_heatmap.png')
        plt.savefig(corr_path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Heatmap', 'Correlacion', corr_path))
    
    return visualizations

# Evaluacion
if section == "📋 Evaluacion":
    st.title("🧠 Evaluacion Psicosocial - NOM-035 Guia I")
    st.markdown("Por favor responda con honestidad. La informacion sera confidencial.")

    with st.form("nom035_form"):
        respuestas = {}
        for section_data in questions:
            with st.expander(section_data["section"], expanded=True):
                for idx, (q, tipo) in enumerate(section_data["items"]):
                    st.markdown(f"**{q}**")
                    if tipo == "text":
                        respuestas[q] = st.text_input("", key=f"q{idx}_{q}")
                    elif tipo == "number":
                        respuestas[q] = st.number_input("", min_value=0, step=1, key=f"q{idx}_{q}")
                    elif isinstance(tipo, list):
                        respuestas[q] = st.radio("", tipo, horizontal=True, key=f"q{idx}_{q}")

        enviar = st.form_submit_button("✅ Enviar evaluacion")
        if enviar:
            try:
                if all(v != "" for v in respuestas.values()):
                    st.session_state.responses.append(respuestas)
                    st.success("✅ ¡Evaluacion enviada exitosamente!")
                else:
                    st.warning("⚠️ Responde todas las preguntas antes de enviar.")
            except Exception as e:
                st.error(f"❌ Error al procesar la evaluacion: {str(e)}")

# Reporte Excel/CSV
if section == "📥 Descargar Reporte":
    st.title("📥 Reporte Consolidado")
    
    # Solicitar clave de acceso
    access_key = st.text_input("🔑 Ingrese la clave de acceso:", type="password")
    
    if st.session_state.responses and access_key == ACCESS_KEY:
        try:
            df = pd.DataFrame(st.session_state.responses)
            
            # Crear directorio temporal para visualizaciones
            with tempfile.TemporaryDirectory() as temp_dir:
                # Generar analisis estadistico
                analysis, df = generate_statistical_analysis(df)
                
                # Generar visualizaciones
                visualizations = generateස
                visualizations = generate_visualizations(df, temp_dir)
                
                # Generar recomendaciones
                recommendations = generate_recommendations(analysis, analysis.get('Distribucion de Riesgo', {}))
                
                # Exportar a Excel
                wb = Workbook()
                
                # Hoja de resumen
                ws_summary = wb.active
                ws_summary.title = "Resumen Ejecutivo"
                ws_summary.cell(1, 1).value = "Reporte NOM-035 Guia I - Resumen Ejecutivo"
                ws_summary.cell(2, 1).value = f"Fecha: {datetime.now().strftime('%Y-%m-%d')}"
                ws_summary.cell(4, 1).value = "Hallazgos Clave:"
                for i, rec in enumerate(recommendations, start=5):
                    ws_summary.cell(i, 1).value = f"- {rec}"
                
                # Hoja de datos crudos
                ws_data = wb.create_sheet("Datos Crudos")
                ws_data.append(df.columns.tolist())
                for row in df.itertuples(index=False):
                    ws_data.append([str(cell) for cell in row])
                
                # Hoja de analisis estadistico
                ws_stats = wb.create_sheet("Analisis Estadistico")
                row = 1
                
                # Distribucion de riesgo
                ws_stats.cell(row, 1).value = "Distribucion de Niveles de Riesgo"
                row += 1
                risk_dist = analysis.get('Distribucion de Riesgo', {})
                for level, count in risk_dist.items():
                    ws_stats.cell(row, 1).value = level
                    ws_stats.cell(row, 2).value = count
                    row += 1
                row += 2
                
                # Descriptivas numericas
                if 'Descriptivas Numericas' in analysis:
                    ws_stats.cell(row, 1).value = "Estadisticas Descriptivas (Numericas)"
                    row += 1
                    desc_df = pd.DataFrame(analysis['Descriptivas Numericas'])
                    for r, idx in enumerate(desc_df.index, start=row):
                        ws_stats.cell(r, 1).value = idx
                        for c, col in enumerate(desc_df.columns, start=2):
                            ws_stats.cell(r, c).value = desc_df.loc[idx, col]
                    row += len(desc_df) + 2
                
                # Frecuencias categoricas
                ws_stats.cell(row, 1).value = "Frecuencias Categoricas"
                row += 1
                for col, freq in analysis['Frecuencias Categoricas'].items():
                    ws_stats.cell(row, 1).value = col
                    row += 1
                    for k, v in freq.items():
                        ws_stats.cell(row, 2).value = k
                        ws_stats.cell(row, 3).value = v
                        row += 1
                    row += 1
                
                # Correlacion
                if 'Correlacion' in analysis:
                    ws_stats.cell(row, 1).value = "Correlacion"
                    row += 1
                    corr_df = pd.DataFrame(analysis['Correlacion'])
                    for r, idx in enumerate(corr_df.index, start=row):
                        ws_stats.cell(r, 1).value = idx
                        for c, col in enumerate(corr_df.columns, start=2):
                            ws_stats.cell(r, c).value = corr_df.loc[idx, col]
                    row += len(corr_df) + 2
                
                # Conteo de sintomas
                ws_stats.cell(row, 1).value = "Conteo de Sintomas (Respuestas 'Si')"
                row += 1
                for col, count in analysis['Conteo de Sintomas'].items():
                    ws_stats.cell(row, 1).value = col
                    ws_stats.cell(row, 2).value = count
                    row += 1
                
                # Riesgo por departamento
                if 'Riesgo por Departamento' in analysis:
                    ws_stats.cell(row, 1).value = "Riesgo por Departamento"
                    row += 1
                    dept_risk = pd.DataFrame(analysis['Riesgo por Departamento'])
                    for r, idx in enumerate(dept_risk.index, start=row):
                        ws_stats.cell(r, 1).value = idx
                        for c, col in enumerate(dept_risk.columns, start=2):
                            ws_stats.cell(r, c).value = dept_risk.loc[idx, col]
                    row += len(dept_risk) + 2
                
                # Riesgo por genero
                if 'Riesgo por Genero' in analysis:
                    ws_stats.cell(row, 1).value = "Riesgo por Genero"
                    row += 1
                    gender_risk = pd.DataFrame(analysis['Riesgo por Genero'])
                    for r, idx in enumerate(gender_risk.index, start=row):
                        ws_stats.cell(r, 1).value = idx
                        for c, col in enumerate(gender_risk.columns, start=2):
                            ws_stats.cell(r, c).value = gender_risk.loc[idx, col]
                
                # Hoja de visualizaciones
                ws_viz = wb.create_sheet("Visualizaciones")
                row_viz = 1
                for viz_type, col, img_path in visualizations:
                    ws_viz.cell(row_viz, 1).value = f"{viz_type}: {col}"
                    img = Image(img_path)
                    img.anchor = f'B{row_viz}'
                    ws_viz.add_image(img)
                    row_viz += 25  # Aumentar espacio para imagenes
                
                # Guardar Excel
                excel_io = io.BytesIO()
                wb.save(excel_io)
                excel_io.seek(0)
                
                # Exportar a CSV (solo datos crudos)
                csv_io = io.StringIO()
                df.to_csv(csv_io, index=False)
                csv_io.seek(0)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📤 Descargar Excel",
                        data=excel_io,
                        file_name="NOM035_Guia1_Analysis.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                with col2:
                    st.download_button(
                        "📤 Descargar CSV",
                        data=csv_io.getvalue(),
                        file_name="NOM035_Guia1.csv",
                        mime="text/csv"
                    )
        except Exception as e:
            st.error(f"❌ Error al generar el reporte: {str(e)}")
    elif access_key and access_key != ACCESS_KEY:
        st.error("🔐 Clave de acceso incorrecta.")
    else:
        st.warning("⚠️ Ingrese la clave de acceso para descargar los datos.")
