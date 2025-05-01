import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
import uuid

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
            
            # Exportar a Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "Respuestas"
            ws.append(df.columns.tolist())
            for row in df.itertuples(index=False):
                ws.append([str(cell) for cell in row])
            
            excel_io = io.BytesIO()
            wb.save(excel_io)
            excel_io.seek(0)
            
            # Exportar a CSV
            csv_io = io.StringIO()
            df.to_csv(csv_io, index=False)
            csv_io.seek(0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📤 Descargar Excel",
                    data=excel_io,
                    file_name="NOM035_Guia1.xlsx",
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
