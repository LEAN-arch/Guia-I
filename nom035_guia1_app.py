
# nom035_guia1_app.py - Aplicación Streamlit robusta y libre de errores para NOM-035-STPS-2018 Guía I

import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook

st.set_page_config(page_title="🧠 NOM-035 Guía I - Evaluación Psicosocial", layout="centered")

if "responses" not in st.session_state:
    st.session_state.responses = []

# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/ios-filled/100/mental-health.png", width=60)
st.sidebar.title("Evaluación NOM-035")
section = st.sidebar.radio("Ir a sección:", ["📋 Evaluación", "📥 Descargar Reporte"])

# Cuestionario estructurado
questions = [
    ("Nombre", "text"),
    ("Apellido Paterno", "text"),
    ("Apellido Materno", "text"),
    ("¿Qué edad tienes? (Solo número, ej. 21)", "number"),
    ("¿Cuál es tu género?", ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"]),
    ("¿Cuántos años llevas trabajando para esta empresa? (ej. 3)", "number"),
    ("¿En qué departamento labora?", ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"]),
    ("¿Cuál es su función?", ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"]),
    ("¿Dónde se encuentra su lugar de trabajo?", ["Planta 1", "Planta 2", "Planta 3"]),

    ("¿Ha presenciado o sufrido algún accidente grave en el trabajo?", ["Sí", "No"]),
    ("¿Ha presenciado o sufrido un asalto en el trabajo?", ["Sí", "No"]),
    ("¿Ha presenciado actos violentos con lesiones graves?", ["Sí", "No"]),
    ("¿Ha presenciado o sufrido un secuestro?", ["Sí", "No"]),
    ("¿Ha recibido amenazas en el trabajo?", ["Sí", "No"]),
    ("¿Ha vivido otra situación que ponga en riesgo su vida o salud?", ["Sí", "No"]),

    ("¿Ha tenido recuerdos recurrentes del evento con malestar?", ["Sí", "No"]),
    ("¿Ha tenido sueños recurrentes del evento con malestar?", ["Sí", "No"]),

    ("¿Evita sentimientos, conversaciones o situaciones relacionadas al evento?", ["Sí", "No"]),
    ("¿Evita actividades, lugares o personas relacionadas al evento?", ["Sí", "No"]),
    ("¿Dificultad para recordar partes importantes del evento?", ["Sí", "No"]),
    ("¿Ha disminuido su interés en actividades cotidianas?", ["Sí", "No"]),
    ("¿Se ha sentido alejado o distante de los demás?", ["Sí", "No"]),
    ("¿Dificultad para expresar sentimientos?", ["Sí", "No"]),
    ("¿Siente que su vida se va a acortar o tiene futuro limitado?", ["Sí", "No"]),

    ("¿Dificultades para dormir?", ["Sí", "No"]),
    ("¿Irritabilidad o arranques de coraje?", ["Sí", "No"]),
    ("¿Dificultad para concentrarse?", ["Sí", "No"]),
    ("¿Nerviosismo o alerta constante?", ["Sí", "No"]),
    ("¿Se sobresalta fácilmente?", ["Sí", "No"])
]

if section == "📋 Evaluación":
    st.title("🧠 Evaluación Psicosocial - Guía I NOM-035")
    st.markdown("""
    Esta herramienta permite evaluar factores de riesgo psicosocial conforme a la **Guía I** de la NOM-035-STPS-2018.
    Complete cada campo de forma clara y precisa. Su información será tratada con confidencialidad.
    """)

    with st.form("guia1_form"):
        respuestas = {}
        for idx, (q_text, q_type) in enumerate(questions):
            st.markdown(f"#### {q_text}")
            if q_type == "text":
                respuestas[q_text] = st.text_input("", key=f"q{idx}")
            elif q_type == "number":
                respuestas[q_text] = st.number_input("", min_value=0, step=1, key=f"q{idx}")
            elif isinstance(q_type, list):
                respuestas[q_text] = st.radio("", q_type, horizontal=True, key=f"q{idx}")
            else:
                respuestas[q_text] = ""

        submitted = st.form_submit_button("✅ Enviar evaluación")
        if submitted:
            if all(value != "" for value in respuestas.values()):
                st.session_state.responses.append(respuestas)
                st.success("¡Gracias! Tu evaluación ha sido registrada con éxito.")
            else:
                st.warning("⚠️ Por favor, completa todas las preguntas antes de enviar.")

    if st.session_state.responses:
        with st.expander("📊 Ver respuestas enviadas"):
            st.dataframe(pd.DataFrame(st.session_state.responses), use_container_width=True)

if section == "📥 Descargar Reporte":
    st.title("📥 Reporte Consolidado - Guía I")
    st.markdown("Descargue todas las respuestas recopiladas en formato Excel.")

    if st.session_state.responses:
        try:
            df = pd.DataFrame(st.session_state.responses)
            wb = Workbook()
            ws = wb.active
            ws.title = "Guía I Respuestas"

            ws.append(df.columns.tolist())
            for _, row in df.iterrows():
                ws.append(row.astype(str).tolist())

            file_io = io.BytesIO()
            wb.save(file_io)
            file_io.seek(0)

            st.download_button("📤 Descargar archivo Excel", data=file_io, file_name="NOM035_GuiaI_Extendida.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"❌ Error al generar el archivo Excel: {str(e)}")
    else:
        st.warning("⚠️ Aún no hay datos para descargar.")
