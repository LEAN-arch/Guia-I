import streamlit as st
import pandas as pd
import smtplib
from email.message import EmailMessage
from io import BytesIO

st.set_page_config(page_title="NOM-035-STPS-2018 - Guía I", layout="wide")
st.title("🛡️ Cuestionario NOM-035-STPS-2018 - Guía I")
st.markdown("Por favor, complete la siguiente información. Sus respuestas se enviarán de forma confidencial al área correspondiente.")

# Definir preguntas
definir_preguntas = [
    ("¿Cuál es su nombre?", ["Nombre", "Apellido Paterno", "Apellido Materno"]),
    ("¿Qué edad tienes? (Solo número)", "Edad"),
    ("¿Cuál es tu género?", ["Femenino", "Masculino", "LGTBTTTIQ+", "Otro"]),
    ("¿Cuántos años llevas trabajando para esta empresa?", "Antigüedad (años)"),
    ("¿En qué departamento labora?", [
        "Mantenimiento", "Control de Calidad", "Manufactura", "Ventas",
        "Producción", "Recursos Humanos", "Ventas y Marketing",
        "Contabilidad y Finanzas", "Administración"
    ]),
    ("¿Cuál es su función?", ["Operador", "Técnico", "Ingeniero", "Analista", "Supervisor", "Gerente", "Director"]),
    ("¿Cuál es su lugar de trabajo?", ["Planta 1", "Planta 2", "Planta 3"])
]

experiencias = {
    "¿Ha presenciado o sufrido un accidente grave?": None,
    "¿Ha sufrido un asalto?": None,
    "¿Ha presenciado actos violentos con lesiones graves?": None,
    "¿Ha sufrido un secuestro?": None,
    "¿Ha recibido amenazas?": None,
    "¿Ha enfrentado otra situación de riesgo grave?": None
}

recuerdos = {
    "¿Tiene recuerdos recurrentes del hecho?": None,
    "¿Sueña repetidamente con el hecho?": None
}

evitar = {
    "¿Evita sentimientos o situaciones relacionadas?": None,
    "¿Evita actividades, lugares o personas relacionadas?": None,
    "¿Tiene dificultad para recordar el evento?": None,
    "¿Ha perdido interés en sus actividades?": None,
    "¿Se siente distante de los demás?": None,
    "¿Tiene dificultad para expresar sentimientos?": None,
    "¿Cree que su vida se acortará o tiene futuro limitado?": None
}

afectacion = {
    "¿Tiene dificultad para dormir?": None,
    "¿Se ha sentido irritable?": None,
    "¿Tiene dificultad para concentrarse?": None,
    "¿Está nervioso o en alerta constantemente?": None,
    "¿Se sobresalta fácilmente?": None
}

# Diccionario para almacenar respuestas
respuestas = {}

# Sección de datos personales
st.subheader("I. Información Personal")
for pregunta in definir_preguntas:
    if isinstance(pregunta[1], list):
        if len(pregunta[1]) > 4:
            respuesta = st.selectbox(pregunta[0], options=pregunta[1])
        else:
            respuesta = st.radio(pregunta[0], options=pregunta[1])
    else:
        respuesta = st.text_input(pregunta[0])
    respuestas[pregunta[0]] = respuesta

# Sección de experiencias
st.subheader("II. Experiencias de Riesgo Laboral")
for pregunta in experiencias.keys():
    experiencias[pregunta] = st.radio(pregunta, ["Sí", "No"])
    respuestas[pregunta] = experiencias[pregunta]

# Sección de recuerdos persistentes
st.subheader("III. Recuerdos Persistentes")
for pregunta in recuerdos.keys():
    recuerdos[pregunta] = st.radio(pregunta, ["Sí", "No"])
    respuestas[pregunta] = recuerdos[pregunta]

# Sección de evitación
st.subheader("IV. Evitación")
for pregunta in evitar.keys():
    evitar[pregunta] = st.radio(pregunta, ["Sí", "No"])
    respuestas[pregunta] = evitar[pregunta]

# Sección de afectación
st.subheader("V. Afectación")
for pregunta in afectacion.keys():
    afectacion[pregunta] = st.radio(pregunta, ["Sí", "No"])
    respuestas[pregunta] = afectacion[pregunta]

# Función para enviar correo
import smtplib
from email.message import EmailMessage

def enviar_respuesta_por_correo(respuestas_dict):
    try:
        mensaje = EmailMessage()
        mensaje["Subject"] = "Nueva respuesta - NOM-035-STPS-2018 Guía I"
        mensaje["From"] = "@gmail.com"
        mensaje["To"] = "contacto@lean2institute.org", "@gmail.com"

        cuerpo = "\n".join([f"{k}: {v}" for k, v in respuestas_dict.items()])
        mensaje.set_content(cuerpo)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login("@gmail.com", "xx")
            smtp.send_message(mensaje)

        return True
    except Exception as e:
        st.error(f"❌ Error al enviar correo: {e}")
        return False

# Exportar como Excel y enviar
if st.button("📤 Enviar respuestas"):
    df = pd.DataFrame.from_dict(respuestas, orient='index', columns=["Respuesta"])
    towrite = BytesIO()
    df.to_excel(towrite, engine='openpyxl')
    towrite.seek(0)

    st.success("✅ Respuestas registradas correctamente.")
    st.download_button(
        label="📥 Descargar respuestas en Excel",
        data=towrite,
        file_name="respuestas_nom035.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    enviado = enviar_respuesta_por_correo(respuestas)
    if enviado:
        st.info("📧 Respuestas enviadas por correo correctamente.")
    else:
        st.warning("⚠️ No se pudo enviar el correo.")
