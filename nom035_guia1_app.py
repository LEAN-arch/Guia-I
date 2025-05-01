# nom035_guia1_app.py - Aplicación Streamlit para NOM-035 Guía I

import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
import smtplib
from email.message import EmailMessage

# Configuración de página
st.set_page_config(page_title="🧠 NOM-035 Guía I", layout="centered")

EMAIL_DESTINO = "contacto@lean2institute.org"

if "responses" not in st.session_state:
    st.session_state.responses = []

# Sidebar
st.sidebar.image("https://img.icons8.com/ios-filled/100/mental-health.png", width=60)
st.sidebar.title("Evaluación NOM-035")
section = st.sidebar.radio("Ir a sección:", ["📋 Evaluación", "📥 Descargar Reporte"])

# Preguntas
questions = [
    ("Nombre", "text"),
    ("Apellido Paterno", "text"),
    ("Apellido Materno", "text"),
    ("¿Qué edad tienes? (ej. 21)", "number"),
    ("¿Cuál es tu género?", ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"]),
    ("¿Cuántos años llevas trabajando aquí?", "number"),
    ("¿En qué departamento labora?", ["Mantenimiento", "Control de Calidad", "Manufactura", "Ventas", "Producción", "Recursos Humanos", "Ventas y Marketing", "Contabilidad y Finanzas", "Administración"]),
    ("¿Cuál es su función?", ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"]),
    ("¿Dónde se encuentra su lugar de trabajo?", ["Planta 1", "Planta 2", "Planta 3"]),
    ("¿Ha presenciado o sufrido un accidente grave?", ["Sí", "No"]),
    ("¿Ha presenciado o sufrido un asalto?", ["Sí", "No"]),
    ("¿Ha presenciado actos violentos con lesiones?", ["Sí", "No"]),
    ("¿Ha presenciado o sufrido un secuestro?", ["Sí", "No"]),
    ("¿Ha recibido amenazas?", ["Sí", "No"]),
    ("¿Otra situación que ponga en riesgo su vida o salud?", ["Sí", "No"]),
    ("¿Recuerdos recurrentes que causan malestar?", ["Sí", "No"]),
    ("¿Sueños recurrentes que causan malestar?", ["Sí", "No"]),
    ("¿Evita sentimientos o situaciones asociadas?", ["Sí", "No"]),
    ("¿Evita actividades o lugares asociados?", ["Sí", "No"]),
    ("¿Dificultad para recordar partes del evento?", ["Sí", "No"]),
    ("¿Menor interés en actividades cotidianas?", ["Sí", "No"]),
    ("¿Se siente alejado o distante de los demás?", ["Sí", "No"]),
    ("¿Dificultad para expresar sentimientos?", ["Sí", "No"]),
    ("¿Sensación de vida corta o futuro limitado?", ["Sí", "No"]),
    ("¿Dificultad para dormir?", ["Sí", "No"]),
    ("¿Irritabilidad o coraje?", ["Sí", "No"]),
    ("¿Dificultad para concentrarse?", ["Sí", "No"]),
    ("¿Nerviosismo o alerta constante?", ["Sí", "No"]),
    ("¿Se sobresalta fácilmente?", ["Sí", "No"])
]

# Función para enviar por correo
def enviar_correo(destinatario, data):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Nueva respuesta - NOM-035 Guía I"
        msg["From"] = "noreply@lean2institute.org"
        msg["To"] = destinatario
        cuerpo = "\n".join(f"{k}: {v}" for k, v in data.items())
        msg.set_content(f"Se recibió una nueva respuesta:\n\n{cuerpo}")

        with smtplib.SMTP("localhost") as server:
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"❌ Error al enviar correo: {str(e)}")
        return False

# Evaluación
if section == "📋 Evaluación":
    st.title("🧠 Evaluación Psicosocial - NOM-035 Guía I")
    st.markdown("Por favor responda con honestidad. La información será confidencial.")

    with st.form("nom035_form"):
        respuestas = {}
        for idx, (q, tipo) in enumerate(questions):
            st.markdown(f"#### {q}")
            if tipo == "text":
                respuestas[q] = st.text_input("", key=f"q{idx}")
            elif tipo == "number":
                respuestas[q] = st.number_input("", min_value=0, step=1, key=f"q{idx}")
            elif isinstance(tipo, list):
                respuestas[q] = st.radio("", tipo, horizontal=True, key=f"q{idx}")

        enviar = st.form_submit_button("✅ Enviar evaluación")
        if enviar:
            if all(v != "" for v in respuestas.values()):
                st.session_state.responses.append(respuestas)
                enviado = enviar_correo(EMAIL_DESTINO, respuestas)
                if enviado:
                    st.success("✅ ¡Evaluación enviada exitosamente!")
            else:
                st.warning("⚠️ Responde todas las preguntas antes de enviar.")

    if st.session_state.responses:
        with st.expander("📊 Ver respuestas anteriores"):
            st.dataframe(pd.DataFrame(st.session_state.responses), use_container_width=True)

# Reporte Excel
if section == "📥 Descargar Reporte":
    st.title("📥 Reporte Consolidado")
    if st.session_state.responses:
        df = pd.DataFrame(st.session_state.responses)
        wb = Workbook()
        ws = wb.active
        ws.title = "Respuestas"

        ws.append(df.columns.tolist())
        for row in df.itertuples(index=False):
            ws.append([str(cell) for cell in row])

        file_io = io.BytesIO()
        wb.save(file_io)
        file_io.seek(0)

        st.download_button(
            "📤 Descargar Excel",
            data=file_io,
            file_name="NOM035_Guia1.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ Aún no hay datos para descargar.")
