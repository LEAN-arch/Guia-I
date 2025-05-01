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

# Configuracion de pagina
st.set_page_config(page_title="🧠 NOM-035 Guia I", layout="centered")

# Clave de acceso predeterminada
ACCESS_KEY = "NOM035G1"

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
    
    # Correlacion entre variables numericas (si hay mas de una)
    if len(numeric_cols) > 1:
        correlation = df[numeric_cols].corr().round(2).to_dict()
        analysis['Correlacion'] = correlation
    
    # Analisis de sintomas (Si/No)
    symptom_cols = [q["items"][0][0] for q in questions[1:]]  # Preguntas de Si/No
    symptom_data = df[symptom_cols]
    symptom_counts = symptom_data.apply(lambda x: (x == 'Si').sum())
    analysis['Conteo de Sintomas'] = symptom_counts.to_dict()
    
    return analysis

# Funcion para generar visualizaciones y guardarlas como imagenes
def generate_visualizations(df, temp_dir):
    visualizations = []
    
    # Histograma para variables numericas
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        plt.figure(figsize=(6, 4))
        sns.histplot(df[col], kde=True)
        plt.title(f'Distribucion de {col}')
        plt.xlabel(col)
        plt.ylabel('Frecuencia')
        hist_path = os.path.join(temp_dir, f'hist_{col}.png')
        plt.savefig(hist_path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Histograma', col, hist_path))
    
    # Graficos de barras para variables categoricas
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        plt.figure(figsize=(6, 4))
        sns.countplot(data=df, x=col)
        plt.title(f'Frecuencia de {col}')
        plt.xlabel(col)
        plt.ylabel('Conteo')
        plt.xticks(rotation=45)
        bar_path = os.path.join(temp_dir, f'bar_{col}.png')
        plt.savefig(bar_path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Barra', col, bar_path))
    
    # Heatmap de correlacion (si aplica)
    if len(numeric_cols) > 1:
        plt.figure(figsize=(6, 4))
        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap='coolwarm')
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
                analysis = generate_statistical_analysis(df)
                
                # Generar visualizaciones
                visualizations = generate_visualizations(df, temp_dir)
                
                # Exportar a Excel
                wb = Workbook()
                
                # Hoja de datos crudos
                ws_data = wb.active
                ws_data.title = "Datos Crudos"
                ws_data.append(df.columns.tolist())
                for row in df.itertuples(index=False):
                    ws_data.append([str(cell) for cell in row])
                
                # Hoja de analisis estadistico
                ws_stats = wb.create_sheet("Analisis Estadistico")
                row = 1
                
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
                
                # Hoja de visualizaciones
                ws_viz = wb.create_sheet("Visualizaciones")
                row_viz = 1
                for viz_type, col, img_path in visualizations:
                    ws_viz.cell(row_viz, 1).value = f"{viz_type}: {col}"
                    img = Image(img_path)
                    ws_viz.add_image(img, f'B{row_viz}')
                    row_viz += 20  # Espacio para imagenes
                
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
