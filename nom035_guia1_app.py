import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf2 import FPDF
import base64
import io
import numpy as np
import seaborn as sns

# Custom CSS for engagement and visual appeal
st.markdown("""
    <style>
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            transition: background-color 0.3s;
        }
        .main {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            animation: fadeIn 0.5s;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .stButton>button {
            background-color: #005b96;
            color: white;
            border-radius: 5px;
            padding: 10px 20px;
            font-weight: bold;
            transition: background-color 0.3s, transform 0.2s;
        }
        .stButton>button:hover {
            background-color: #003366;
            transform: scale(1.05);
        }
        .stRadio>label {
            background-color: #e6f0fa;
            padding: 8px;
            border-radius: 5px;
            margin: 5px 0;
            transition: background-color 0.3s;
        }
        .stRadio>label:hover {
            background-color: #d1e6ff;
        }
        .header {
            color: #005b96;
            font-size: 2.5em;
            text-align: center;
            margin-bottom: 20px;
        }
        .subheader {
            color: #333;
            font-size: 1.5em;
            margin-top: 20px;
        }
        .sidebar .sidebar-content {
            background-color: #f0f4f8;
            border-radius: 10px;
            padding: 20px;
        }
        .download-link {
            color: #005b96;
            font-weight: bold;
            text-decoration: none;
        }
        .download-link:hover {
            color: #003366;
            text-decoration: underline;
        }
        .error {
            color: #d32f2f;
            font-weight: bold;
        }
        .success {
            color: #2e7d32;
            font-weight: bold;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        .dark-theme {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        .dark-theme .main {
            background-color: #2e2e2e;
            box-shadow: 0 4px 8px rgba(255, 255, 255, 0.1);
        }
        .dark-theme .stButton>button {
            background-color: #0288d1;
        }
        .dark-theme .stButton>button:hover {
            background-color: #01579b;
        }
        .dark-theme .stRadio>label {
            background-color: #424242;
            color: #e0e0e0;
        }
        .dark-theme .stRadio>label:hover {
            background-color: #616161;
        }
        .dark-theme .header, .dark-theme .subheader {
            color: #0288d1;
        }
        .milestone {
            text-align: center;
            font-size: 1.2em;
            color: #2e7d32;
            margin: 10px 0;
        }
    </style>
    <script>
        // Confetti animation for milestones
        function triggerConfetti() {
            if (typeof confetti === 'function') {
                confetti({
                    particleCount: 100,
                    spread: 70,
                    origin: { y: 0.6 }
                });
            }
        }
    </script>
""", unsafe_allow_html=True)

# Include confetti.js for animations
st.markdown('<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>', unsafe_allow_html=True)

# Set page configuration
st.set_page_config(page_title="Ethical Lean Audit", layout="wide", initial_sidebar_state="expanded")

# Theme selection
theme = st.sidebar.selectbox("Theme / Tema", ["Light", "Dark"], help="Choose your preferred theme / Elige tu tema preferido")
if theme == "Dark":
    st.markdown('<style>body, .main { background-color: #1e1e1e; color: #e0e0e0; } .main { background-color: #2e2e2e; }</style>', unsafe_allow_html=True)

# Bilingual support
LANG = st.sidebar.selectbox("Language / Idioma", ["English", "Español"], help="Select your preferred language / Selecciona tu idioma preferido", key="lang_select")

# Likert scale labels
labels = {
    "English": ["Not Practiced", "Rarely Practiced", "Partially Implemented", "Mostly Practiced", "Fully Integrated"],
    "Español": ["No practicado", "Raramente practicado", "Parcialmente implementado", "Mayormente practicado", "Totalmente integrado"]
}

# Audit categories and questions
questions = {
    "Employee Empowerment and Engagement": {
        "English": [
            "Are employees actively involved in decision-making processes that directly impact their daily work and job satisfaction?",
            "Do employees feel their contributions to continuous improvement are valued and recognized by leadership?",
            "Is there a structured feedback system where employees can openly express concerns and suggest improvements?",
            "Are all employees given equal access to training and career development opportunities?",
            "Is there a culture of trust and respect where employees are encouraged to suggest innovations?"
        ],
        "Español": [
            "¿Están los empleados activamente involucrados en los procesos de toma de decisiones que impactan directamente en su trabajo diario y satisfacción laboral?",
            "¿Sienten los empleados que sus contribuciones a la mejora continua son valoradas y reconocidas por el liderazgo?",
            "¿Existe un sistema estructurado de retroalimentación donde los empleados puedan expresar abiertamente preocupaciones y sugerir mejoras?",
            "¿Tienen todos los empleados igual acceso a oportunidades de capacitación y desarrollo profesional?",
            "¿Hay una cultura de confianza y respeto donde se fomenta que los empleados sugieran innovaciones?"
        ]
    },
    "Operational Integrity and Continuous Improvement": {
        "English": [
            "Are Lean processes regularly assessed for compliance with ethical standards?",
            "Is there a link between Lean waste reduction and environmental/social responsibility?",
            "Are bottlenecks proactively identified and addressed?",
            "Does the Lean system adapt based on internal/external feedback?",
            "Are digital tools integrated to ensure transparency and traceability?"
        ],
        "Español": [
            "¿Se evalúan regularmente los procesos Lean para garantizar el cumplimiento de los estándares éticos?",
            "¿Existe una conexión entre la reducción de desperdicios Lean y la responsabilidad ambiental/social?",
            "¿Se identifican y abordan proactivamente los cuellos de botella?",
            "¿Se adapta el sistema Lean en función de retroalimentación interna/externa?",
            "¿Se integran herramientas digitales para garantizar transparencia y trazabilidad?"
        ]
    },
    "Customer Satisfaction and Value": {
        "English": [
            "Is customer satisfaction a key metric for Lean success?",
            "Is feedback integrated into continuous improvement?",
            "Do Lean processes prioritize value over efficiency?",
            "Is customer satisfaction regularly measured?",
            "Are product/service improvements validated by customers?"
        ],
        "Español": [
            "¿Es la satisfacción del cliente una métrica clave para el éxito de Lean?",
            "¿Se integra la retroalimentación en la mejora continua?",
            "¿Priorizan los procesos Lean el valor sobre la eficiencia?",
            "¿Se mide regularmente la satisfacción del cliente?",
            "¿Se validan las mejoras de productos/servicios con los clientes?"
        ]
    },
    "Ethical Leadership and Decision-Making": {
        "English": [
            "Does leadership model ethical behavior and transparency?",
            "Are ethical considerations part of Lean tool implementation?",
            "Is the workforce impact of Lean transparent to stakeholders?",
            "Are social and ethical Lean impacts tracked and addressed?",
            "Are leaders accountable for ethical Lean implementation?"
        ],
        "Español": [
            "¿Modela el liderazgo un comportamiento ético y transparencia?",
            "¿Forman parte las consideraciones éticas de la implementación de herramientas Lean?",
            "¿Es transparente el impacto de Lean en la fuerza laboral para las partes interesadas?",
            "¿Se rastrean y abordan los impactos sociales y éticos de Lean?",
            "¿Son los líderes responsables de la implementación ética de Lean?"
        ]
    },
    "Sustainability and Long-Term Impact": {
        "English": [
            "Does Lean focus on long-term sustainable practices?",
            "Are Lean principles part of CSR strategies?",
            "Is carbon footprint reduction part of Lean?",
            "Are sustainability metrics part of Lean performance?",
            "Is there a scaling plan that maintains ethics and sustainability?"
        ],
        "Español": [
            "¿Se enfoca Lean en prácticas sostenibles a largo plazo?",
            "¿Forman parte los principios Lean de las estrategias de responsabilidad social corporativa?",
            "¿Es la reducción de la huella de carbono parte de Lean?",
            "¿Forman parte las métricas de sostenibilidad del rendimiento Lean?",
            "¿Existe un plan de escalado que mantenga la ética y la sostenibilidad?"
        ]
    },
    "Supplier and Partner Relationships": {
        "English": [
            "Are Lean principles applied fairly to suppliers?",
            "Does Lean avoid unfair labor or environmental harm in supply chains?",
            "Do suppliers collaborate in Lean process improvements?",
            "Are ethical suppliers prioritized?",
            "Are supplier ethics regularly assessed?"
        ],
        "Español": [
            "¿Se aplican los principios Lean de manera justa a los proveedores?",
            "¿Evita Lean el daño laboral o ambiental injusto en las cadenas de suministro?",
            "¿Colaboran los proveedores en las mejoras de procesos Lean?",
            "¿Se priorizan los proveedores éticos?",
            "¿Se evalúan regularmente la ética de los proveedores?"
        ]
    },
    "Lean System Transparency and Adaptability": {
        "English": [
            "Are Lean processes transparent to stakeholders?",
            "Is the Lean system flexible to change?",
            "Are Lean strategies regularly reviewed?",
            "Can employees propose Lean process changes?",
            "Is continuous learning fostered in Lean culture?"
        ],
        "Español": [
            "¿Son los procesos Lean transparentes para las partes interesadas?",
            "¿Es el sistema Lean flexible al cambio?",
            "¿Se revisan regularmente las estrategias Lean?",
            "¿Pueden los empleados proponer cambios en los procesos Lean?",
            "¿Se fomenta el aprendizaje continuo en la cultura Lean?"
        ]
    },
    "Cultural Alignment and Organizational Health": {
        "English": [
            "Is Lean aligned with organizational mission and culture?",
            "Are Lean tools adapted to company culture?",
            "Is cross-departmental collaboration promoted?",
            "Are voices from all levels heard in Lean?",
            "Is psychological safety encouraged?"
        ],
        "Español": [
            "¿Está Lean alineado con la misión y la cultura organizacional?",
            "¿Se adaptan las herramientas Lean a la cultura de la empresa?",
            "¿Se promueve la colaboración interdepartamental?",
            "¿Se escuchan las voces de todos los niveles en Lean?",
            "¿Se fomenta la seguridad psicológica?"
        ]
    },
    "Employee Well-Being and Work-Life Balance": {
        "English": [
            "Is employee well-being prioritized in Lean?",
            "Are stress and burnout monitored?",
            "Are workloads regularly assessed and adjusted?",
            "Is there a culture of empathy and support?",
            "Is Lean performance measured holistically (efficiency + satisfaction)?"
        ],
        "Español": [
            "¿Se prioriza el bienestar de los empleados en Lean?",
            "¿Se monitorean el estrés y el agotamiento?",
            "¿Se evalúan y ajustan regularmente las cargas de trabajo?",
            "¿Hay una cultura de empatía y apoyo?",
            "¿Se mide el rendimiento Lean de manera holística (eficiencia + satisfacción)?"
        ]
    },
    "Ethical Decision-Making and Transparency in Metrics": {
        "English": [
            "Are ethical frameworks used in Lean performance evaluation?",
            "Are KPIs aligned with ethical values?",
            "Are Lean outcomes celebrated fairly?",
            "Are ethical implications reviewed before Lean decisions?",
            "Are Lean metrics shared externally for accountability?"
        ],
        "Español": [
            "¿Se utilizan marcos éticos en la evaluación del rendimiento Lean?",
            "¿Están los KPI alineados con valores éticos?",
            "¿Se celebran los resultados Lean de manera justa?",
            "¿Se revisan las implicaciones éticas antes de las decisiones Lean?",
            "¿Se comparten las métricas Lean externamente para rendir cuentas?"
        ]
    }
}

# Initialize session state
if 'responses' not in st.session_state:
    st.session_state.responses = {cat: [0] * len(questions[cat][LANG]) for cat in questions}
if 'current_category' not in st.session_state:
    st.session_state.current_category = 0
if 'completed_categories' not in st.session_state:
    st.session_state.completed_categories = set()

# Reset session state button
if st.sidebar.button("Reset Session" if LANG == "English" else "Restablecer Sesión", key="reset_session"):
    st.session_state.clear()
    st.rerun()

# Main title with logo
st.markdown('<div class="header">Ethical Lean Audit</div>' if LANG == "English" else '<div class="header">Auditoría Lean Ética</div>', unsafe_allow_html=True)
st.markdown("![Logo](https://via.placeholder.com/100x50?text=Your+Logo)" if LANG == "English" else "![Logo](https://via.placeholder.com/100x50?text=Tu+Logo)", unsafe_allow_html=True)

# Progress bar with milestones
categories = list(questions.keys())
progress = (st.session_state.current_category / len(categories)) * 100
st.progress(progress)
completed_count = len(st.session_state.completed_categories)
if completed_count > 0 and completed_count % 3 == 0:
    st.markdown(f'<div class="milestone">🎉 Milestone: {completed_count} categories completed!</div>', unsafe_allow_html=True)
    st.markdown('<script>triggerConfetti();</script>', unsafe_allow_html=True)

# Category navigation
st.sidebar.subheader("Progress" if LANG == "English" else "Progreso")
category_index = st.sidebar.slider(
    "Select Category / Seleccionar Categoría",
    0, len(categories) - 1, st.session_state.current_category,
    disabled=False,
    key="category_slider"
)
st.session_state.current_category = category_index
category = categories[category_index]

# Collect responses with dynamic score preview
st.markdown(f'<div class="subheader">{category}</div>', unsafe_allow_html=True)
current_scores = st.session_state.responses[category]
score_sum = sum(score for score in current_scores if isinstance(score, int) and 1 <= score <= 5)
max_score = len(questions[category][LANG]) * 5
score_percent = (score_sum / max_score) * 100 if max_score > 0 else 0
st.write(f"Current Category Score: {score_sum}/{max_score} ({score_percent:.1f}%)" if LANG == "English" else f"Puntuación Actual de la Categoría: {score_sum}/{max_score} ({score_percent:.1f}%)")

for idx, q in enumerate(questions[category][LANG]):
    score = st.radio(
        f"{q}",
        list(range(1, 6)),
        format_func=lambda x: f"{x} - {labels[LANG][x-1]}",
        key=f"{category}_{idx}",
        horizontal=True,
        label_visibility="visible"
    )
    st.session_state.responses[category][idx] = score

# Mark category as completed if all questions answered
if all(isinstance(score, int) and 1 <= score <= 5 for score in current_scores):
    st.session_state.completed_categories.add(category)
    st.markdown(f'<div class="success">Category completed! Great job!</div>' if LANG == "English" else f'<div class="success">¡Categoría completada! ¡Buen trabajo!</div>', unsafe_allow_html=True)

# Navigation buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("Previous Category" if LANG == "English" else "Categoría Anterior", disabled=category_index == 0, key="prev_category"):
        st.session_state.current_category -= 1
        st.rerun()
with col2:
    if st.button("Next Category" if LANG == "English" else "Siguiente Categoría", disabled=category_index == len(categories) - 1, key="next_category"):
        st.session_state.current_category += 1
        st.rerun()

# Generate report
if st.button("Generate Report" if LANG == "English" else "Generar Informe", key="generate_report"):
    # Validate responses
    incomplete_categories = [cat for cat, scores in st.session_state.responses.items() if not all(isinstance(score, int) and 1 <= score <= 5 for score in scores)]
    if incomplete_categories:
        st.markdown(f'<div class="error">Please complete all questions for: {", ".join(incomplete_categories)}</div>', unsafe_allow_html=True)
        st.stop()

    st.markdown(f'<div class="subheader">{"Audit Results" if LANG == "English" else "Resultados de la Auditoría"}</div>', unsafe_allow_html=True)
    
    # Calculate scores and create DataFrame
    results = {}
    for cat, scores in st.session_state.responses.items():
        try:
            total_score = sum(scores)
            results[cat] = {"Score": total_score, "Percent": (total_score / (len(scores) * 5)) * 100}
        except Exception as e:
            st.error(f"Error calculating scores for {cat}: {str(e)}")
            st.stop()

    df = pd.DataFrame.from_dict(results, orient="index")
    df.index.name = "Category"
    
    # Debug: Display DataFrame contents
    st.write("Debug: DataFrame contents")
    st.dataframe(df)
    
    # Display results
    st.dataframe(df.style.format({"Score": "{:.0f}", "Percent": "{:.1f}%"}))
    
    # Visualization selection
    viz_type = st.selectbox("Select Visualization" if LANG == "English" else "Seleccionar Visualización", ["Radar Chart", "Bar Plot"], key="viz_select")
    
    if viz_type == "Radar Chart":
        st.markdown(f'<div class="subheader">{"Audit Results Visualization" if LANG == "English" else "Visualización de Resultados de la Auditoría"}</div>', unsafe_allow_html=True)
        
        categories = list(df.index)
        values = df["Percent"].values.tolist()
        
        try:
            fig, ax = plt.subplots(figsize=(12, 8), subplot_kw=dict(polar=True))
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            values += values[:1]
            angles += angles[:1]
            
            ax.plot(angles, values, linewidth=2, linestyle='solid', label='Score', color='#005b96')
            ax.fill(angles, values, '#e6f0fa', alpha=0.5)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=10, wrap=True, color='#333')
            ax.set_yticklabels([])
            ax.set_title("Ethical Lean Audit Radar" if LANG == "English" else "Radar de Auditoría Lean Ética", size=18, pad=20, color='#005b96')
            ax.grid(True, color='#ccc', linestyle='--')
            plt.tight_layout()
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error generating radar chart: {str(e)}")
    
    else:  # Bar Plot
        st.markdown(f'<div class="subheader">{"Audit Results Visualization" if LANG == "English" else "Visualización de Resultados de la Auditoría"}</div>', unsafe_allow_html=True)
        
        try:
            summary = df.reset_index()
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=summary, x="Percent", y="Category", palette="coolwarm")
            plt.title("Audit Results" if LANG == "English" else "Resultados de la Auditoría")
            plt.xlabel("Percentage" if LANG == "English" else "Porcentaje")
            plt.ylabel("Category" if LANG == "English" else "Categoría")
            plt.tight_layout()
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error generating bar plot: {str(e)}")

    # PDF Report
    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(0, 91, 150)
            self.cell(0, 10, "Ethical Lean Audit Report" if LANG == "English" else "Informe de Auditoría Lean Ética", 0, 1, "C")
            self.ln(5)
        
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    try:
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.set_text_color(51)
        pdf.cell(0, 10, "Audit Results" if LANG == "English" else "Resultados de la Auditoría", ln=True)
        pdf.ln(5)
        
        for cat, row in df.iterrows():
            pdf.cell(0, 10, f"{cat}: {row['Percent']:.1f}%", ln=True)
        
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        b64_pdf = base64.b64encode(pdf_output.getvalue()).decode()
        href_pdf = f'<a href="data:application/pdf;base64,{b64_pdf}" download="ethical_lean_audit_report.pdf" class="download-link">Download PDF Report</a>' if LANG == "English" else f'<a href="data:application/pdf;base64,{b64_pdf}" download="informe_auditoria_lean_etica.pdf" class="download-link">Descargar Informe PDF</a>'
        st.markdown(href_pdf, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error generating PDF report: {str(e)}")

    # Excel export
    try:
        excel_output = io.BytesIO()
        with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Audit Results' if LANG == "English" else 'Resultados de la Auditoría', float_format="%.1f")
        excel_output.seek(0)
        b64_excel = base64.b64encode(excel_output.getvalue()).decode()
        href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="ethical_lean_audit_results.xlsx" class="download-link">Download Excel Report</a>' if LANG == "English" else f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="resultados_auditoria_lean_etica.xlsx" class="download-link">Descargar Informe Excel</a>'
        st.markdown(href_excel, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error generating Excel report: {str(e)}")

    # Completion Certificate
    if len(st.session_state.completed_categories) == len(categories):
        st.markdown(f'<div class="success">Congratulations! You have completed the Ethical Lean Audit!</div>' if LANG == "English" else f'<div class="success">¡Felicidades! Has completado la Auditoría Lean Ética!</div>', unsafe_allow_html=True)
        st.markdown('<script>triggerConfetti();</script>', unsafe_allow_html=True)
        
        try:
            cert_pdf = PDF()
            cert_pdf.add_page()
            cert_pdf.set_font("Helvetica", "B", 16)
            cert_pdf.set_text_color(0, 91, 150)
            cert_pdf.cell(0, 20, "Certificate of Completion" if LANG == "English" else "Certificado de Finalización", 0, 1, "C")
            cert_pdf.set_font("Helvetica", size=12)
            cert_pdf.cell(0, 10, "Ethical Lean Audit" if LANG == "English" else "Auditoría Lean Ética", 0, 1, "C")
            cert_pdf.ln(10)
            cert_pdf.cell(0, 10, "Awarded to: [Your Name]" if LANG == "English" else "Otorgado a: [Tu Nombre]", 0, 1, "C")
            cert_pdf.cell(0, 10, f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}", 0, 1, "C")
            cert_pdf.ln(10)
            cert_pdf.cell(0, 10, "Thank you for your commitment to ethical Lean practices!" if LANG == "English" else "¡Gracias por tu compromiso con las prácticas Lean éticas!", 0, 1, "C")
            
            cert_output = io.BytesIO()
            cert_pdf.output(cert_output)
            cert_output.seek(0)
            b64_cert = base64.b64encode(cert_output.getvalue()).decode()
            href_cert = f'<a href="data:application/pdf;base64,{b64_cert}" download="ethical_lean_audit_certificate.pdf" class="download-link">Download Completion Certificate</a>' if LANG == "English" else f'<a href="data:application/pdf;base64,{b64_cert}" download="certificado_auditoria_lean_etica.pdf" class="download-link">Descargar Certificado de Finalización</a>'
            st.markdown(href_cert, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error generating certificate: {str(e)}")
