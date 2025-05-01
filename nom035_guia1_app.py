import streamlit as st
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.utils.dataframe import dataframe_to_rows
import matplotlib.pyplot as plt
import seaborn as sns
import os
import tempfile
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
from enum import Enum
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nom035_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ====================
# CONSTANTS & CONFIGURATION
# ====================

class AppConfig:
    """Centralized configuration for the application"""
    # Application metadata
    PAGE_TITLE = "🧠 Evaluación Psicosocial - NOM-035"
    PAGE_ICON = "🧠"
    LAYOUT = "centered"
    
    # Security
    ACCESS_KEY = "NOM035_ACCESS_2025"
    RESET_PASSWORD = "RESET_NOM035_2025"
    
    # Data files
    LOG_FILE = "responses_log.csv"
    BACKUP_FOLDER = "backups/"
    
    # UI Assets
    LOGO_PATH = "assets/FOBO2.png"
    LOGO_WIDTH = 120
    THEME_COLOR = "#1f77b4"
    
    # Visualization
    CHART_WIDTH = 10
    CHART_HEIGHT = 6
    COLOR_PALETTE = "Blues"
    
    # Navigation
    NAV_OPTIONS = {
        "📋 Evaluación": "assessment",
        "📊 Resultados": "results",
        "📥 Reportes": "reports",
        "⚙️ Administración": "admin"
    }

class RiskLevel(Enum):
    """Enum for risk level classifications"""
    VERY_HIGH = "Muy Alto"
    HIGH = "Alto"
    MEDIUM = "Medio"
    LOW = "Bajo"
    INSIGNIFICANT = "Insignificante"

# ====================
# DATA MODELS
# ====================

@dataclass
class Question:
    """Data model for a single assessment question"""
    text: str
    field_name: str
    question_type: str
    options: Optional[List[str]] = None
    required: bool = True
    help_text: Optional[str] = None
    risk_domain: Optional[str] = None
    reverse_score: bool = False

    def render(self, key: str) -> Any:
        """Render the question in Streamlit UI"""
        container = st.container()
        
        # Question text with optional help tooltip
        if self.help_text:
            container.markdown(f"**{self.text}** ❓", help=self.help_text)
        else:
            container.markdown(f"**{self.text}**")
        
        # Render appropriate input based on type
        if self.question_type == "text":
            return container.text_input(
                label="",
                key=key,
                value="",
                help=self.help_text
            )
        elif self.question_type == "number":
            return container.number_input(
                label="",
                key=key,
                min_value=0,
                step=1,
                value=0,
                help=self.help_text
            )
        elif self.question_type == "radio" and self.options:
            return container.radio(
                label="",
                options=self.options,
                horizontal=True,
                key=key,
                help=self.help_text
            )
        elif self.question_type == "select" and self.options:
            return container.selectbox(
                label="",
                options=self.options,
                key=key,
                help=self.help_text
            )
        return None

@dataclass
class Section:
    """Data model for a group of related questions"""
    title: str
    description: Optional[str] = None
    questions: List[Question] = None
    
    def add_question(self, question: Question):
        """Add a question to the section"""
        self.questions = self.questions or []
        self.questions.append(question)
    
    def render(self, prefix: str) -> Dict[str, Any]:
        """Render the entire section with all questions"""
        responses = {}
        
        with st.expander(self.title, expanded=True):
            if self.description:
                st.markdown(self.description)
            
            for idx, question in enumerate(self.questions or []):
                key = f"{prefix}_q{idx}_{question.field_name}"
                responses[question.field_name] = question.render(key)
        
        return responses

# ====================
# ASSESSMENT CONTENT
# ====================

class AssessmentContent:
    """Contains all assessment questions and structure"""
    
    @staticmethod
    def create_guia_i_assessment() -> List[Section]:
        """Create Guia I assessment structure"""
        return [
            Section(
                title="Información Personal",
                description="Datos demográficos y laborales básicos",
                questions=[
                    Question(
                        text="Nombre completo",
                        field_name="nombre",
                        question_type="text",
                        help_text="Ingrese su nombre completo"
                    ),
                    Question(
                        text="Edad",
                        field_name="edad",
                        question_type="number",
                        help_text="Ingrese su edad en años"
                    ),
                    Question(
                        text="Género",
                        field_name="genero",
                        question_type="radio",
                        options=["Femenino", "Masculino", "LGBTQ+", "Otro", "Prefiero no decir"],
                        help_text="Seleccione su identidad de género"
                    ),
                    # Additional personal questions...
                ]
            ),
            Section(
                title="Eventos Traumáticos Severos",
                description="Experiencias que pueden afectar la salud psicológica",
                questions=[
                    Question(
                        text="¿Ha presenciado o sufrido un accidente grave?",
                        field_name="accidente_grave",
                        question_type="radio",
                        options=["Sí", "No"],
                        risk_domain="Trauma"
                    ),
                    # Additional trauma questions...
                ]
            ),
            # Additional sections...
        ]
    
    @staticmethod
    def create_guia_ii_assessment() -> List[Section]:
        """Create Guia II assessment structure"""
        response_scale = ["Siempre", "Casi siempre", "A veces", "Casi nunca", "Nunca"]
        
        return [
            Section(
                title="Condiciones en el Ambiente de Trabajo",
                description="Factores físicos del entorno laboral",
                questions=[
                    Question(
                        text="¿El espacio donde trabaja le permite realizar sus actividades de manera segura y cómoda?",
                        field_name="espacio_seguro",
                        question_type="radio",
                        options=response_scale,
                        risk_domain="Ambiente"
                    ),
                    # Additional environment questions...
                ]
            ),
            # Additional sections...
        ]

# ====================
# DATA PROCESSING
# ====================

class DataValidator:
    """Handles data validation and cleaning"""
    
    @staticmethod
    def validate_response(response: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, str]:
        """Validate that all required fields are completed"""
        missing_fields = [field for field in required_fields if not response.get(field)]
        
        if missing_fields:
            return False, f"Faltan campos obligatorios: {', '.join(missing_fields)}"
        return True, ""

class DataAnalyzer:
    """Handles data analysis and scoring"""
    
    @staticmethod
    def calculate_guia_i_risk(responses: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk level for Guia I responses"""
        # Implementation details...
        pass
    
    @staticmethod
    def calculate_guia_ii_scores(responses: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate scores and risk levels for Guia II"""
        # Implementation details...
        pass
    
    @staticmethod
    def generate_statistical_report(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive statistical analysis"""
        # Implementation details...
        pass

class DataVisualizer:
    """Handles data visualization"""
    
    @staticmethod
    def initialize_style():
        """Initialize visualization style settings"""
        sns.set_style("whitegrid")
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        plt.rcParams['savefig.facecolor'] = 'white'
    
    @staticmethod
    def create_demographic_charts(data: pd.DataFrame, temp_dir: str) -> List[Tuple[str, str]]:
        """Create demographic visualization charts"""
        charts = []
        
        # Age distribution
        plt.figure(figsize=(AppConfig.CHART_WIDTH, AppConfig.CHART_HEIGHT))
        sns.histplot(data['edad'], kde=True, color=AppConfig.THEME_COLOR)
        plt.title('Distribución de Edad de los Empleados')
        plt.xlabel('Edad')
        plt.ylabel('Número de Empleados')
        age_path = os.path.join(temp_dir, 'age_distribution.png')
        plt.savefig(age_path, bbox_inches='tight')
        plt.close()
        charts.append(("Distribución de Edad", age_path))
        
        # Gender distribution
        plt.figure(figsize=(AppConfig.CHART_WIDTH, AppConfig.CHART_HEIGHT))
        gender_counts = data['genero'].value_counts()
        plt.pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%')
        plt.title('Distribución por Género')
        gender_path = os.path.join(temp_dir, 'gender_distribution.png')
        plt.savefig(gender_path, bbox_inches='tight')
        plt.close()
        charts.append(("Distribución por Género", gender_path))
        
        return charts
    
    @staticmethod
    def create_risk_charts(analysis: Dict[str, Any], temp_dir: str) -> List[Tuple[str, str]]:
        """Create risk assessment visualization charts"""
        charts = []
        
        # Guia I positive responses
        if 'guia_i_positive_percentage' in analysis:
            plt.figure(figsize=(AppConfig.CHART_WIDTH, AppConfig.CHART_HEIGHT))
            plt.bar(['Positivas', 'Negativas'], 
                   [analysis['guia_i_positive_percentage'], 
                    100 - analysis['guia_i_positive_percentage']],
                   color=AppConfig.THEME_COLOR)
            plt.title('Porcentaje de Respuestas Positivas (Guía I)')
            plt.ylabel('Porcentaje (%)')
            plt.ylim(0, 100)
            guia_i_path = os.path.join(temp_dir, 'guia_i_positive.png')
            plt.savefig(guia_i_path, bbox_inches='tight')
            plt.close()
            charts.append(("Respuestas Positivas Guía I", guia_i_path))
        
        # Guia II risk distribution
        if 'guia_ii_risk_distribution' in analysis:
            plt.figure(figsize=(AppConfig.CHART_WIDTH, AppConfig.CHART_HEIGHT))
            risk_data = analysis['guia_ii_risk_distribution']
            risk_levels = [level.value for level in RiskLevel]
            counts = [risk_data.get(level, 0) for level in risk_levels]
            
            sns.barplot(x=risk_levels, y=counts, palette=AppConfig.COLOR_PALETTE)
            plt.title('Distribución de Riesgo Psicosocial (Guía II)')
            plt.xlabel('Nivel de Riesgo')
            plt.ylabel('Número de Empleados')
            plt.xticks(rotation=45)
            guia_ii_path = os.path.join(temp_dir, 'guia_ii_risk.png')
            plt.savefig(guia_ii_path, bbox_inches='tight')
            plt.close()
            charts.append(("Distribución de Riesgo Guía II", guia_ii_path))
        
        return charts

# ====================
# REPORT GENERATION
# ====================

class ReportGenerator:
    """Handles report generation in multiple formats"""
    
    @staticmethod
    def generate_excel_report(data: pd.DataFrame, 
                            analysis: Dict[str, Any],
                            charts: List[Tuple[str, str]]) -> io.BytesIO:
        """Generate comprehensive Excel report"""
        wb = Workbook()
        
        # Summary sheet
        ws_summary = wb.active
        ws_summary.title = "Resumen Ejecutivo"
        ws_summary.append(["Reporte de Evaluación Psicosocial NOM-035"])
        ws_summary.append([f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
        ws_summary.append([f"Total de evaluaciones: {len(data)}"])
        ws_summary.append([])
        
        # Add key findings
        ws_summary.append(["Hallazgos Clave:"])
        if 'guia_i_positive_percentage' in analysis:
            ws_summary.append([
                f"- {analysis['guia_i_positive_percentage']:.1f}% de empleados mostraron "
                "respuestas positivas en Guía I (eventos traumáticos)"
            ])
        
        if 'guia_ii_risk_distribution' in analysis:
            high_risk = analysis['guia_ii_risk_distribution'].get(RiskLevel.HIGH.value, 0)
            very_high = analysis['guia_ii_risk_distribution'].get(RiskLevel.VERY_HIGH.value, 0)
            ws_summary.append([
                f"- {high_risk + very_high} empleados ({((high_risk + very_high)/len(data)*100:.1f}%) "
                "en riesgo Alto o Muy Alto en Guía II"
            ])
        
        # Raw data sheet
        ws_data = wb.create_sheet("Datos Crudos")
        for row in dataframe_to_rows(data, index=False, header=True):
            ws_data.append(row)
        
        # Analysis sheet
        ws_analysis = wb.create_sheet("Análisis")
        ReportGenerator._add_analysis_to_sheet(ws_analysis, analysis)
        
        # Charts sheet
        if charts:
            ws_charts = wb.create_sheet("Gráficos")
            ReportGenerator._add_charts_to_sheet(ws_charts, charts)
        
        # Save to BytesIO
        excel_io = io.BytesIO()
        wb.save(excel_io)
        excel_io.seek(0)
        return excel_io
    
    @staticmethod
    def _add_analysis_to_sheet(ws, analysis: Dict[str, Any]):
        """Add analysis data to worksheet"""
        # Implementation details...
        pass
    
    @staticmethod
    def _add_charts_to_sheet(ws, charts: List[Tuple[str, str]]):
        """Add charts to worksheet"""
        row = 1
        for title, path in charts:
            ws.cell(row=row, column=1).value = title
            img = Image(path)
            img.anchor = f'A{row+1}'
            ws.add_image(img)
            row += 30  # Adjust based on image height

# ====================
# SESSION MANAGEMENT
# ====================

class SessionManager:
    """Manages application session state"""
    
    @staticmethod
    def initialize():
        """Initialize all session state variables"""
        defaults = {
            "responses": [],
            "current_assessment": None,
            "assessment_stage": "guia_i",
            "form_progress": {},
            "analysis_results": None,
            "report_generated": False
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def reset_data(password: str):
        """Reset all application data with password protection"""
        if password == AppConfig.RESET_PASSWORD:
            try:
                # Create backup before reset
                backup_file = os.path.join(
                    AppConfig.BACKUP_FOLDER,
                    f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
                
                if os.path.exists(AppConfig.LOG_FILE):
                    os.rename(AppConfig.LOG_FILE, backup_file)
                
                # Reset session state
                SessionManager.initialize()
                st.success("✅ Datos reiniciados exitosamente. Se creó una copia de seguridad.")
                logger.info("Application data reset performed")
            except Exception as e:
                st.error(f"❌ Error al reiniciar los datos: {str(e)}")
                logger.error(f"Data reset failed: {str(e)}")
        else:
            st.error("🔐 Contraseña incorrecta para reiniciar datos.")
            logger.warning("Failed data reset attempt - incorrect password")

# ====================
# USER INTERFACE
# ====================

class AssessmentUI:
    """Handles all user interface components"""
    
    @staticmethod
    def render_sidebar():
        """Render the application sidebar"""
        with st.sidebar:
            st.image(AppConfig.LOGO_PATH, width=AppConfig.LOGO_WIDTH)
            st.title("Evaluación NOM-035")
            
            selected = st.radio(
                "Navegación:",
                list(AppConfig.NAV_OPTIONS.keys()),
                key="nav_radio"
            )
            
            st.markdown("---")
            st.markdown("### Acerca de")
            st.markdown("""
                Esta herramienta ayuda a implementar la NOM-035-STPS-2018 
                para identificar y analizar factores de riesgo psicosocial.
            """)
            
        return AppConfig.NAV_OPTIONS[selected]
    
    @staticmethod
    def render_guia_i_assessment():
        """Render the Guia I assessment interface"""
        st.title("📋 Evaluación Psicosocial - Guía I")
        st.markdown("""
            **Instrucciones:** Responda cada pregunta con honestidad. 
            La información proporcionada es confidencial y se utilizará 
            únicamente para fines de evaluación psicosocial.
        """)
        
        sections = AssessmentContent.create_guia_i_assessment()
        
        with st.form("guia_i_form"):
            responses = {}
            required_fields = []
            
            for section in sections:
                section_responses = section.render(f"gi_{section.title[:10]}")
                responses.update(section_responses)
                
                # Track required fields
                for q in section.questions:
                    if q.required:
                        required_fields.append(q.field_name)
            
            submitted = st.form_submit_button("✅ Enviar Evaluación")
            
            if submitted:
                is_valid, message = DataValidator.validate_response(responses, required_fields)
                
                if is_valid:
                    try:
                        # Check if Guia II is needed
                        needs_guia_ii = any(
                            responses.get(q.field_name) == "Sí" 
                            for section in sections[1:]  # Skip personal info section
                            for q in section.questions
                        )
                        
                        # Save responses
                        st.session_state.responses.append(responses)
                        
                        if needs_guia_ii:
                            st.session_state.assessment_stage = "guia_ii"
                            st.session_state.current_assessment = responses
                            st.success("✅ Guía I completada. Por favor complete la Guía II.")
                        else:
                            st.session_state.assessment_stage = "complete"
                            st.success("✅ Evaluación completada. No se requiere Guía II.")
                        
                        # Log response
                        DataLogger.log_response(responses)
                        
                    except Exception as e:
                        st.error(f"❌ Error al procesar la evaluación: {str(e)}")
                        logger.error(f"Assessment processing failed: {str(e)}")
                else:
                    st.warning(f"⚠️ {message}")

    @staticmethod
    def render_guia_ii_assessment():
        """Render the Guia II assessment interface"""
        st.title("📋 Evaluación Psicosocial - Guía II")
        st.markdown("""
            **Instrucciones:** A continuación encontrará preguntas adicionales 
            sobre su experiencia laboral. Por favor responda con sinceridad.
        """)
        
        sections = AssessmentContent.create_guia_ii_assessment()
        
        with st.form("guia_ii_form"):
            responses = st.session_state.current_assessment.copy()
            required_fields = []
            
            for section in sections:
                section_responses = section.render(f"gii_{section.title[:10]}")
                responses.update(section_responses)
                
                # Track required fields
                for q in section.questions:
                    if q.required:
                        required_fields.append(q.field_name)
            
            submitted = st.form_submit_button("✅ Enviar Evaluación")
            
            if submitted:
                is_valid, message = DataValidator.validate_response(responses, required_fields)
                
                if is_valid:
                    try:
                        # Save responses
                        st.session_state.responses.append(responses)
                        st.session_state.assessment_stage = "complete"
                        
                        # Log response
                        DataLogger.log_response(responses)
                        
                        st.success("✅ Evaluación Guía I y II completada exitosamente!")
                    except Exception as e:
                        st.error(f"❌ Error al procesar la evaluación: {str(e)}")
                        logger.error(f"Assessment processing failed: {str(e)}")
                else:
                    st.warning(f"⚠️ {message}")

    @staticmethod
    def render_results_dashboard():
        """Render the interactive results dashboard"""
        st.title("📊 Resultados de la Evaluación")
        
        if not st.session_state.responses:
            st.warning("No hay datos de evaluación para mostrar.")
            return
        
        try:
            # Convert responses to DataFrame
            df = pd.DataFrame(st.session_state.responses)
            
            # Perform analysis
            analysis = DataAnalyzer.generate_statistical_report(df)
            st.session_state.analysis_results = analysis
            
            # Display key metrics
            st.subheader("Resumen General")
            
            cols = st.columns(3)
            cols[0].metric(
                "Total Evaluaciones",
                len(df),
                help="Número total de evaluaciones completadas"
            )
            
            if 'guia_i_positive_percentage' in analysis:
                cols[1].metric(
                    "Positivos Guía I",
                    f"{analysis['guia_i_positive_percentage']:.1f}%",
                    help="Porcentaje con respuestas positivas a eventos traumáticos"
                )
            
            if 'guia_ii_risk_distribution' in analysis:
                high_risk = analysis['guia_ii_risk_distribution'].get(RiskLevel.HIGH.value, 0)
                very_high = analysis['guia_ii_risk_distribution'].get(RiskLevel.VERY_HIGH.value, 0)
                cols[2].metric(
                    "Alto/Muy Alto Riesgo",
                    f"{high_risk + very_high} ({((high_risk + very_high)/len(df)*100):.1f}%)",
                    help="Empleados con riesgo Alto o Muy Alto en Guía II"
                )
            
            # Interactive filters
            st.subheader("Filtros Interactivos")
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                department_filter = st.multiselect(
                    "Filtrar por departamento",
                    options=df['departamento'].unique() if 'departamento' in df.columns else [],
                    default=df['departamento'].unique() if 'departamento' in df.columns else []
                )
            
            with filter_col2:
                gender_filter = st.multiselect(
                    "Filtrar por género",
                    options=df['genero'].unique() if 'genero' in df.columns else [],
                    default=df['genero'].unique() if 'genero' in df.columns else []
                )
            
            # Apply filters
            filtered_df = df.copy()
            if department_filter and 'departamento' in df.columns:
                filtered_df = filtered_df[filtered_df['departamento'].isin(department_filter)]
            if gender_filter and 'genero' in df.columns:
                filtered_df = filtered_df[filtered_df['genero'].isin(gender_filter)]
            
            # Display filtered data
            st.subheader("Datos Filtrados")
            st.dataframe(filtered_df, height=300, use_container_width=True)
            
            # Visualization tabs
            tab1, tab2 = st.tabs(["📈 Gráficos", "🔍 Detalles"])
            
            with tab1:
                with tempfile.TemporaryDirectory() as temp_dir:
                    charts = DataVisualizer.create_demographic_charts(filtered_df, temp_dir)
                    charts += DataVisualizer.create_risk_charts(analysis, temp_dir)
                    
                    for title, path in charts:
                        st.subheader(title)
                        st.image(path, use_column_width=True)
            
            with tab2:
                st.subheader("Análisis Detallado")
                if 'guia_i_analysis' in analysis:
                    with st.expander("Resultados Guía I"):
                        st.write(analysis['guia_i_analysis'])
                
                if 'guia_ii_analysis' in analysis:
                    with st.expander("Resultados Guía II"):
                        st.write(analysis['guia_ii_analysis'])
            
            st.session_state.report_generated = True
            
        except Exception as e:
            st.error(f"❌ Error al generar el dashboard: {str(e)}")
            logger.error(f"Dashboard generation failed: {str(e)}")

    @staticmethod
    def render_report_generator():
        """Render the report generation interface"""
        st.title("📥 Generar Reportes")
        
        if not st.session_state.responses:
            st.warning("No hay datos de evaluación para generar reportes.")
            return
        
        if not st.session_state.report_generated:
            st.warning("Genere los resultados primero en la pestaña 'Resultados'.")
            return
        
        st.markdown("""
            Seleccione el formato del reporte y haga clic en el botón correspondiente 
            para descargar los resultados de la evaluación.
        """)
        
        access_key = st.text_input(
            "🔑 Clave de acceso para reportes:",
            type="password",
            help="Ingrese la clave autorizada para generar reportes"
        )
        
        if access_key != AppConfig.ACCESS_KEY:
            st.warning("Ingrese la clave de acceso válida para generar reportes.")
            return
        
        try:
            df = pd.DataFrame(st.session_state.responses)
            analysis = st.session_state.analysis_results
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Generate visualizations
                charts = DataVisualizer.create_demographic_charts(df, temp_dir)
                charts += DataVisualizer.create_risk_charts(analysis, temp_dir)
                
                # Generate reports
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    excel_report = ReportGenerator.generate_excel_report(df, analysis, charts)
                    st.download_button(
                        "💾 Descargar Excel",
                        data=excel_report,
                        file_name="reporte_nom035.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Descargue un reporte completo en formato Excel"
                    )
                
                with col2:
                    csv_report = ReportGenerator.generate_csv_report(df)
                    st.download_button(
                        "📊 Descargar CSV",
                        data=csv_report.getvalue(),
                        file_name="datos_nom035.csv",
                        mime="text/csv",
                        help="Descargue los datos crudos en formato CSV"
                    )
                
                with col3:
                    pdf_report = ReportGenerator.generate_pdf_report(df, analysis, charts)
                    st.download_button(
                        "📄 Descargar PDF",
                        data=pdf_report,
                        file_name="resumen_nom035.pdf",
                        mime="application/pdf",
                        help="Descargue un resumen ejecutivo en PDF"
                    )
        
        except Exception as e:
            st.error(f"❌ Error al generar reportes: {str(e)}")
            logger.error(f"Report generation failed: {str(e)}")

    @staticmethod
    def render_admin_panel():
        """Render the administration panel"""
        st.title("⚙️ Administración del Sistema")
        
        tab1, tab2 = st.tabs(["🔐 Seguridad", "🛠 Mantenimiento"])
        
        with tab1:
            st.subheader("Configuración de Seguridad")
            st.warning("Estas opciones son solo para administradores autorizados.")
            
            with st.expander("Cambiar Clave de Acceso", expanded=False):
                current_pass = st.text_input("Clave actual:", type="password")
                new_pass = st.text_input("Nueva clave:", type="password")
                confirm_pass = st.text_input("Confirmar nueva clave:", type="password")
                
                if st.button("Actualizar Clave"):
                    if current_pass != AppConfig.ACCESS_KEY:
                        st.error("Clave actual incorrecta")
                    elif new_pass != confirm_pass:
                        st.error("Las claves nuevas no coinciden")
                    else:
                        # In a real app, you would securely update the password
                        st.success("Clave actualizada exitosamente (simulado)")
            
        with tab2:
            st.subheader("Mantenimiento de Datos")
            
            with st.expander("Respaldar Datos", expanded=False):
                if st.button("🔄 Crear Copia de Seguridad"):
                    try:
                        backup_file = os.path.join(
                            AppConfig.BACKUP_FOLDER,
                            f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        )
                        
                        if os.path.exists(AppConfig.LOG_FILE):
                            import shutil
                            shutil.copy2(AppConfig.LOG_FILE, backup_file)
                            st.success(f"✅ Copia de seguridad creada: {backup_file}")
                        else:
                            st.warning("No hay datos para respaldar")
                    except Exception as e:
                        st.error(f"❌ Error al crear copia: {str(e)}")
            
            with st.expander("Reiniciar Datos", expanded=False):
                st.warning("Esta acción eliminará todos los datos de evaluación y no se puede deshacer.")
                reset_pass = st.text_input("Contraseña de administrador:", type="password")
                
                if st.button("🛑 Reiniciar Todos los Datos"):
                    SessionManager.reset_data(reset_pass)

# ====================
# MAIN APPLICATION
# ====================

def main():
    """Main application entry point"""
    # Initialize application
    st.set_page_config(
        page_title=AppConfig.PAGE_TITLE,
        page_icon=AppConfig.PAGE_ICON,
        layout=AppConfig.LAYOUT
    )
    
    # Initialize session state
    SessionManager.initialize()
    
    # Initialize visualization style
    DataVisualizer.initialize_style()
    
    # Render sidebar and get current view
    current_view = AssessmentUI.render_sidebar()
    
    # Render appropriate view based on navigation
    if current_view == "assessment":
        if st.session_state.assessment_stage == "guia_i":
            AssessmentUI.render_guia_i_assessment()
        elif st.session_state.assessment_stage == "guia_ii":
            AssessmentUI.render_guia_ii_assessment()
        else:
            AssessmentUI.render_guia_i_assessment()
    
    elif current_view == "results":
        AssessmentUI.render_results_dashboard()
    
    elif current_view == "reports":
        AssessmentUI.render_report_generator()
    
    elif current_view == "admin":
        AssessmentUI.render_admin_panel()

if __name__ == "__main__":
    main()
# ====================
# DATA LOGGING & PERSISTENCE
# ====================

class DataLogger:
    """Handles data persistence and logging"""
    
    @staticmethod
    def log_response(response: Dict[str, Any]):
        """Log assessment responses to persistent storage"""
        try:
            # Ensure backup directory exists
            os.makedirs(AppConfig.BACKUP_FOLDER, exist_ok=True)
            
            # Add metadata
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'assessment_type': 'guia_i' if 'guia_ii' not in response else 'guia_ii',
                **response
            }
            
            # Convert to DataFrame
            log_df = pd.DataFrame([log_entry])
            
            # Write to log file
            if not os.path.exists(AppConfig.LOG_FILE):
                log_df.to_csv(AppConfig.LOG_FILE, index=False)
            else:
                log_df.to_csv(AppConfig.LOG_FILE, mode='a', header=False, index=False)
            
            logger.info(f"Logged assessment response for {response.get('nombre', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to log response: {str(e)}")
            st.error("❌ Error al guardar los datos. Por favor intente nuevamente.")

    @staticmethod
    def load_responses() -> pd.DataFrame:
        """Load all historical responses from log"""
        try:
            if os.path.exists(AppConfig.LOG_FILE):
                df = pd.read_csv(AppConfig.LOG_FILE)
                
                # Convert timestamp to datetime
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to load responses: {str(e)}")
            return pd.DataFrame()

# ====================
# RISK ANALYSIS ENGINE
# ====================

class RiskAnalyzer:
    """Core engine for calculating risk levels and scores"""
    
    # Scoring weights for different domains
    DOMAIN_WEIGHTS = {
        'ambiente_trabajo': 0.15,
        'carga_trabajo': 0.20,
        'falta_control': 0.15,
        'jornada_trabajo': 0.10,
        'trabajo_familia': 0.10,
        'liderazgo': 0.15,
        'relaciones_trabajo': 0.10,
        'violencia': 0.05
    }
    
    # Thresholds for risk levels
    RISK_THRESHOLDS = {
        RiskLevel.VERY_HIGH: 80,
        RiskLevel.HIGH: 60,
        RiskLevel.MEDIUM: 40,
        RiskLevel.LOW: 20,
        RiskLevel.INSIGNIFICANT: 0
    }
    
    @staticmethod
    def calculate_composite_score(scores: Dict[str, float]) -> float:
        """Calculate weighted composite score from domain scores"""
        return sum(
            score * RiskAnalyzer.DOMAIN_WEIGHTS.get(domain, 0)
            for domain, score in scores.items()
        )
    
    @staticmethod
    def determine_risk_level(score: float) -> RiskLevel:
        """Determine risk level based on score"""
        for level, threshold in sorted(
            RiskAnalyzer.RISK_THRESHOLDS.items(), 
            key=lambda x: x[1], 
            reverse=True
        ):
            if score >= threshold:
                return level
        return RiskLevel.INSIGNIFICANT
    
    @staticmethod
    def analyze_guia_i(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Guia I responses for traumatic events"""
        analysis = {
            'total_responses': len(responses),
            'positive_responses': 0,
            'by_department': {},
            'by_gender': {},
            'by_age_group': {}
        }
        
        if not responses:
            return analysis
        
        df = pd.DataFrame(responses)
        
        # Check for positive responses (Sí answers)
        symptom_questions = [
            'accidente_grave', 'asalto', 'violencia_lesiones',
            'secuestro', 'amenazas', 'otra_situacion_riesgo'
        ]
        
        # Count positive responses
        for question in symptom_questions:
            if question in df.columns:
                analysis['positive_responses'] += (df[question] == 'Sí').sum()
        
        # Analyze by department
        if 'departamento' in df.columns:
            analysis['by_department'] = df.groupby('departamento')[symptom_questions]\
                .apply(lambda x: (x == 'Sí').sum().sum())\
                .to_dict()
        
        # Analyze by gender
        if 'genero' in df.columns:
            analysis['by_gender'] = df.groupby('genero')[symptom_questions]\
                .apply(lambda x: (x == 'Sí').sum().sum())\
                .to_dict()
        
        # Analyze by age groups
        if 'edad' in df.columns:
            df['age_group'] = pd.cut(
                df['edad'],
                bins=[0, 25, 35, 45, 55, 65, 100],
                labels=['<25', '25-34', '35-44', '45-54', '55-64', '65+']
            )
            analysis['by_age_group'] = df.groupby('age_group')[symptom_questions]\
                .apply(lambda x: (x == 'Sí').sum().sum())\
                .to_dict()
        
        return analysis
    
    @staticmethod
    def analyze_guia_ii(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Comprehensive analysis of Guia II psychosocial factors"""
        analysis = {
            'domain_scores': {},
            'composite_scores': [],
            'risk_levels': [],
            'by_department': {},
            'by_gender': {}
        }
        
        if not responses:
            return analysis
        
        df = pd.DataFrame(responses)
        
        # Define question domains and their weights
        domains = {
            'ambiente_trabajo': [
                'espacio_seguro', 'condiciones_adecuadas',
                'equipos_buen_estado', 'lugar_limpio_ordenado'
            ],
            # Other domains would be defined here...
        }
        
        # Calculate domain scores for each response
        domain_scores = []
        
        for _, row in df.iterrows():
            scores = {}
            for domain, questions in domains.items():
                domain_score = 0
                for q in questions:
                    if q in row:
                        # Convert response to numerical score
                        score = RiskAnalyzer._response_to_score(row[q])
                        # Apply reverse scoring if needed
                        if q in ['horas_extras_frecuencia', 'demandas_interfieren']:
                            score = 4 - score
                        domain_score += score
                # Normalize by number of questions
                scores[domain] = domain_score / len(questions)
            domain_scores.append(scores)
        
        # Add scores to analysis
        analysis['domain_scores'] = pd.DataFrame(domain_scores).mean().to_dict()
        
        # Calculate composite scores and risk levels
        composite_scores = [
            RiskAnalyzer.calculate_composite_score(scores) * 100  # Convert to percentage
            for scores in domain_scores
        ]
        
        risk_levels = [
            RiskAnalyzer.determine_risk_level(score)
            for score in composite_scores
        ]
        
        analysis['composite_scores'] = composite_scores
        analysis['risk_levels'] = risk_levels
        
        # Add risk distribution
        risk_counts = {level.value: 0 for level in RiskLevel}
        for level in risk_levels:
            risk_counts[level.value] += 1
        analysis['risk_distribution'] = risk_counts
        
        # Analyze by department
        if 'departamento' in df.columns:
            df['composite_score'] = composite_scores
            df['risk_level'] = [level.value for level in risk_levels]
            
            # Average scores by department
            analysis['by_department']['scores'] = df.groupby('departamento')['composite_score']\
                .mean().round(2).to_dict()
            
            # Risk level counts by department
            analysis['by_department']['risk_levels'] = df.groupby(
                ['departamento', 'risk_level']
            ).size().unstack(fill_value=0).to_dict()
        
        # Analyze by gender
        if 'genero' in df.columns:
            analysis['by_gender']['scores'] = df.groupby('genero')['composite_score']\
                .mean().round(2).to_dict()
            
            analysis['by_gender']['risk_levels'] = df.groupby(
                ['genero', 'risk_level']
            ).size().unstack(fill_value=0).to_dict()
        
        return analysis
    
    @staticmethod
    def _response_to_score(response: str) -> int:
        """Convert Likert scale response to numerical score"""
        scale = {
            "Siempre": 4,
            "Casi siempre": 3,
            "A veces": 2,
            "Casi nunca": 1,
            "Nunca": 0
        }
        return scale.get(response, 0)

# ====================
# REPORT GENERATION (CONTINUED)
# ====================

class ReportGenerator:
    """Extended reporting functionality"""
    
    @staticmethod
    def generate_pdf_report(df: pd.DataFrame, 
                          analysis: Dict[str, Any],
                          charts: List[Tuple[str, str]]) -> io.BytesIO:
        """Generate PDF executive summary report"""
        try:
            from fpdf import FPDF
            from PIL import Image as PILImage
            
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Add cover page
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Reporte de Evaluación Psicosocial NOM-035', 0, 1, 'C')
            pdf.ln(10)
            
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
            pdf.cell(0, 10, f"Total de evaluaciones: {len(df)}", 0, 1)
            pdf.ln(15)
            
            # Add key findings
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Hallazgos Clave:', 0, 1)
            pdf.set_font('Arial', '', 12)
            
            if 'guia_i_analysis' in analysis:
                positives = analysis['guia_i_analysis']['positive_responses']
                total = analysis['guia_i_analysis']['total_responses']
                pdf.multi_cell(0, 10, 
                    f"- {positives} de {total} empleados ({positives/total*100:.1f}%) "
                    "reportaron eventos traumáticos o síntomas relevantes.")
            
            if 'guia_ii_analysis' in analysis:
                high_risk = analysis['guia_ii_analysis']['risk_distribution'].get('Alto', 0)
                very_high = analysis['guia_ii_analysis']['risk_distribution'].get('Muy Alto', 0)
                pdf.multi_cell(0, 10,
                    f"- {high_risk + very_high} empleados en riesgo Alto o Muy Alto "
                    f"({(high_risk + very_high)/len(df)*100:.1f}%)")
            
            # Add charts
            for title, path in charts:
                pdf.add_page()
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, title, 0, 1)
                
                # Resize image to fit PDF
                img = PILImage.open(path)
                width, height = img.size
                aspect = width / height
                new_width = 180  # ~6 inches
                new_height = new_width / aspect
                
                pdf.image(path, x=15, y=30, w=new_width, h=new_height)
            
            # Save to bytes buffer
            pdf_bytes = io.BytesIO()
            pdf.output(pdf_bytes)
            pdf_bytes.seek(0)
            return pdf_bytes
        
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            st.error("Error al generar reporte PDF")
            return io.BytesIO()

    @staticmethod
    def generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Guia I recommendations
        if 'guia_i_analysis' in analysis:
            positives = analysis['guia_i_analysis']['positive_responses']
            total = analysis['guia_i_analysis']['total_responses']
            
            if positives > 0:
                pct = positives / total * 100
                rec = (
                    f"Implementar programas de apoyo psicológico para los {positives} "
                    f"empleados ({pct:.1f}%) que reportaron eventos traumáticos. "
                    "Considerar evaluaciones individuales con especialistas."
                )
                recommendations.append(rec)
                
                # Department-specific recommendations
                if 'by_department' in analysis['guia_i_analysis']:
                    top_dept = max(
                        analysis['guia_i_analysis']['by_department'].items(),
                        key=lambda x: x[1]
                    )
                    if top_dept[1] > 0:
                        rec = (
                            f"Priorizar intervenciones en el departamento de {top_dept[0]}, "
                            f"que muestra la mayor cantidad de reportes ({top_dept[1]})."
                        )
                        recommendations.append(rec)
        
        # Guia II recommendations
        if 'guia_ii_analysis' in analysis:
            high_risk = analysis['guia_ii_analysis']['risk_distribution'].get('Alto', 0)
            very_high = analysis['guia_ii_analysis']['risk_distribution'].get('Muy Alto', 0)
            
            if high_risk + very_high > 0:
                rec = (
                    f"Realizar intervenciones organizacionales para abordar los factores "
                    f"de riesgo psicosocial identificados en {high_risk + very_high} "
                    "empleados. Considerar:"
                )
                recommendations.append(rec)
                
                # Domain-specific recommendations
                domains = analysis['guia_ii_analysis']['domain_scores']
                top_risk_domain = max(domains.items(), key=lambda x: x[1])
                
                if top_risk_domain[1] > 60:  # Above high risk threshold
                    rec = (
                        f"- Enfocarse en mejorar el área de {top_risk_domain[0].replace('_', ' ')}, "
                        f"que muestra el mayor nivel de riesgo ({top_risk_domain[1]:.1f}%)."
                    )
                    recommendations.append(rec)
                
                # Add general recommendations
                recommendations.extend([
                    "- Capacitar a supervisores en detección temprana de factores de riesgo",
                    "- Revisar políticas de carga de trabajo y equilibrio vida laboral-personal",
                    "- Implementar programas de promoción de salud mental en el trabajo"
                ])
        
        if not recommendations:
            recommendations.append(
                "No se identificaron riesgos significativos. "
                "Mantener los programas de prevención y monitoreo regular."
            )
        
        return recommendations

# ====================
# ADMINISTRATION TOOLS
# ====================

class AdminTools:
    """Administrative and maintenance functions"""
    
    @staticmethod
    def backup_data():
        """Create a timestamped backup of assessment data"""
        try:
            os.makedirs(AppConfig.BACKUP_FOLDER, exist_ok=True)
            
            if os.path.exists(AppConfig.LOG_FILE):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(
                    AppConfig.BACKUP_FOLDER,
                    f"nom035_backup_{timestamp}.csv"
                )
                
                import shutil
                shutil.copy2(AppConfig.LOG_FILE, backup_path)
                
                logger.info(f"Created backup at {backup_path}")
                return True, backup_path
            return False, "No data to backup"
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def restore_backup(backup_file: str):
        """Restore data from a backup file"""
        try:
            if os.path.exists(backup_file):
                # Create pre-restore backup
                AdminTools.backup_data()
                
                # Restore from selected backup
                shutil.copy2(backup_file, AppConfig.LOG_FILE)
                
                # Reload session data
                SessionManager.initialize()
                
                logger.info(f"Restored data from {backup_file}")
                return True, "Datos restaurados exitosamente"
            return False, "Archivo de backup no encontrado"
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def get_backup_files() -> List[Dict[str, str]]:
        """List available backup files with metadata"""
        backups = []
        
        if os.path.exists(AppConfig.BACKUP_FOLDER):
            for filename in os.listdir(AppConfig.BACKUP_FOLDER):
                if filename.startswith("nom035_backup_") and filename.endswith(".csv"):
                    filepath = os.path.join(AppConfig.BACKUP_FOLDER, filename)
                    stat = os.stat(filepath)
                    
                    backups.append({
                        'filename': filename,
                        'path': filepath,
                        'size': f"{stat.st_size / 1024:.1f} KB",
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    })
        
        # Sort by modified time (newest first)
        return sorted(backups, key=lambda x: x['modified'], reverse=True)

# ====================
# MAIN APPLICATION FLOW
# ====================

if __name__ == "__main__":
    # Initialize the application
    st.set_page_config(
        page_title=AppConfig.PAGE_TITLE,
        page_icon=AppConfig.PAGE_ICON,
        layout=AppConfig.LAYOUT
    )
    
    # Initialize session state and components
    SessionManager.initialize()
    DataVisualizer.initialize_style()
    
    # Render the application
    try:
        current_view = AssessmentUI.render_sidebar()
        
        if current_view == "assessment":
            if st.session_state.assessment_stage == "guia_i":
                AssessmentUI.render_guia_i_assessment()
            elif st.session_state.assessment_stage == "guia_ii":
                AssessmentUI.render_guia_ii_assessment()
            else:
                AssessmentUI.render_guia_i_assessment()
        
        elif current_view == "results":
            AssessmentUI.render_results_dashboard()
        
        elif current_view == "reports":
            AssessmentUI.render_report_generator()
        
        elif current_view == "admin":
            AssessmentUI.render_admin_panel()
    
    except Exception as e:
        logger.critical(f"Application error: {str(e)}")
        st.error("Ocurrió un error crítico en la aplicación. Por favor recargue la página.")
