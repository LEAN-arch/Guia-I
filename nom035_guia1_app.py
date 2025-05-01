```python
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

# Configuración de página
st.set_page_config(page_title="🧠 NOM-035 Guía I", layout="centered")

# Clave de acceso predeterminada
ACCESS_KEY = "NOM035_ACCESS_2025"

if "responses" not in st.session_state:
    st.session_state.responses = []

# Sidebar
st.sidebar.image("assets/FOBO2.png", width=100)
st.sidebar.title("Evaluación NOM-035")
section = st.sidebar.radio("Ir a sección:", ["📋 Evaluación", "📥 Descargar Reporte"])

# Preguntas (27 en total, organizadas en secciones)
questions = [
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

# Función para generar análisis estadístico
def generate_statistical_analysis(df):
    analysis = {}
    
    # Estadísticas descriptivas para variables numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if numeric_cols.any():
        desc_stats = df[numeric_cols].describe().round(2)
        analysis['Descriptivas Numéricas'] = desc_stats.to_dict()
    
    # Frecuencias para variables categóricas
    categorical_cols = df.select_dtypes(include=['object']).columns
    freq_tables = {}
    for col in categorical_cols:
        freq = df[col].value_counts().to_dict()
        freq_tables[col] = freq
    analysis['Frecuencias Categóricas'] = freq_tables
    
    # Correlación entre variables numéricas (si hay más de una)
    if len(numeric_cols) > 1:
        correlation = df[numeric_cols].corr().round(2).to_dict()
        analysis['Correlación'] = correlation
    
    # Análisis de síntomas (Sí/No)
    symptom_cols = [q["items"][0][0] for q in questions[1:]]  # Preguntas de Sí/No
    symptom_data = df[symptom_cols]
    symptom_counts = symptom_data.apply(lambda x: (x == 'Sí').sum())
    analysis['Conteo de Síntomas'] = symptom_counts.to_dict()
    
    return analysis

# Función para generar visualizaciones y guardarlas como imágenes
def generate_visualizations(df, temp_dir):
    visualizations = []
    
    # Histograma para variables numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        plt.figure(figsize=(6, 4))
        sns.histplot(df[col], kde=True)
        plt.title(f'Distribución de {col}')
        plt.xlabel(col)
        plt.ylabel('Frecuencia')
        hist_path = os.path.join(temp_dir, f'hist_{col}.png')
        plt.savefig(hist_path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Histograma', col, hist_path))
    
    # Gráficos de barras para variables categóricas
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
    
    # Heatmap de correlación (si aplica)
    if len(numeric_cols) > 1:
        plt.figure(figsize=(6, 4))
        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap='coolwarm')
        plt.title('Mapa de Calor de Correlaciones')
        corr_path = os.path.join(temp_dir, 'correlation_heatmap.png')
        plt.savefig(corr_path, bbox_inches='tight')
        plt.close()
        visualizations.append(('Heatmap', 'Correlación', corr_path))
    
    return visualizations

# Evaluación
if section == "📋 Evaluación":
    st.title("🧠 Evaluación Psicosocial - NOM-035 Guía I")
    st.markdown("Por favor responda con honestidad. La información será confidencial.")

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

        enviar = st.form_submit_button("✅ Enviar evaluación")
        if enviar:
            try:
                if all(v != "" for v in respuestas.values()):
                    st.session_state.responses.append(respuestas)
                    st.success("✅ ¡Evaluación enviada exitosamente!")
                else:
                    st.warning("⚠️ Responde todas las preguntas antes de enviar.")
            except Exception as e:
                st.error(f"❌ Error al procesar la evaluación: {str(e)}")

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
                # Generar análisis estadístico
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
                
                # Hoja de análisis estadístico
                ws_stats = wb.create_sheet("Análisis Estadístico")
                row = 1
                
                # Descriptivas numéricas
                if 'Descriptivas Numéricas' in analysis:
                    ws_stats.cell(row, 1).value = "Estadísticas Descriptivas (Numéricas)"
                    row += 1
                    desc_df = pd.DataFrame(analysis['Descriptivas Numéricas'])
                    for r, idx in enumerate(desc_df.index, start=row):
                        ws_stats.cell(r, 1).value = idx
                        for c, col in enumerate(desc_df.columns, start=2):
                            ws_stats.cell(r, c).value = desc_df.loc[idx, col]
                    row += len(desc_df) + 2
                
                # Frecuencias categóricas
                ws_stats.cell(row, 1).value = "Frecuencias Categóricas"
                row += 1
                for col, freq in analysis['Frecuencias Categóricas'].items():
                    ws_stats.cell(row, 1).value = col
                    row += 1
                    for k, v in freq.items():
                        ws_stats.cell(row, 2).value = k
                        ws_stats.cell(row, 3).value = v
                        row += 1
                    row += 1
                
                # Correlación
                if 'Correlación' in analysis:
                    ws_stats.cell(row, 1).value = "Correlación"
                    row += 1
                    corr_df = pd.DataFrame(analysis['Correlación'])
                    for r, idx in enumerate(corr_df.index, start=row):
                        ws_stats.cell(r, 1).value = idx
                        for c, col in enumerate(corr_df.columns, start=2):
                            ws_stats.cell(r, c).value = corr_df.loc[idx, col]
                    row += len(corr_df) + 2
                
                # Conteo de síntomas
                ws_stats.cell(row, 1).value = "Conteo de Síntomas (Respuestas 'Sí')"
                row += 1
                for col, count in analysis['Conteo de Síntomas'].items():
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
                    row_viz += 20  # Espacio para imágenes
                
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
```

### Changes Made:
1. **Statistical Analysis**:
   - **Descriptive Statistics**: For numerical columns (e.g., age, years working), includes mean, std, min, max, quartiles.
   - **Frequency Tables**: For categorical columns (e.g., gender, department, Sí/No questions), provides counts of each category.
   - **Correlation Analysis**: For numerical variables, computes Pearson correlation matrix (if multiple numerical columns exist).
   - **Symptom Counts**: Counts the number of "Sí" responses for symptom-related questions to highlight prevalence.

2. **Visualizations**:
   - **Histograms**: For numerical variables, showing distribution with kernel density estimation.
   - **Bar Plots**: For categorical variables, showing frequency of each category.
   - **Correlation Heatmap**: For numerical variables, visualizing correlations (if applicable).
   - Visualizations are saved as PNG files in a temporary directory and embedded in the Excel file’s "Visualizaciones" sheet.

3. **Excel Structure**:
   - **Datos Crudos**: Raw data as collected.
   - **Análisis Estadístico**: Includes descriptive stats, frequency tables, correlations, and symptom counts in a structured format.
   - **Visualizaciones**: Embeds visualization images with labels for each plot.

4. **CSV Output**:
   - Remains limited to raw data due to CSV’s text-based nature, which doesn’t support embedded images or complex formatting.

5. **Error Handling**:
   - Robust error handling around statistical computations and file operations to prevent crashes.

6. **Dependencies**:
   - Added `matplotlib`, `seaborn`, `scipy`, and `openpyxl` for statistical analysis and visualization.

### Notes:
- Ensure `matplotlib`, `seaborn`, `scipy`, and `openpyxl` are installed in your environment (`pip install matplotlib seaborn scipy openpyxl`).
- Visualizations are embedded in the Excel file, but their size and placement may need adjustment depending on your needs (modify `row_viz += 20` for spacing).
- The CSV file only includes raw data, as statistical summaries and images are not feasible in CSV format.
- The analysis assumes sufficient data for meaningful statistics; with very few responses, some visualizations (e.g., histograms) may be less informative.

This code provides a professional, comprehensive report tailored for Spanish-speaking professionals, with advanced analytics and visualizations embedded in the Excel output.
