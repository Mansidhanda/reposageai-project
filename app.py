import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pathlib import PurePosixPath
import re
import unicodedata
import ast
import math

from reposage.analyzer import (
    analyse_repository,
    explain_code,
    answer_repository_question
)

from reposage.reports import (
    build_pdf_report,
    build_docx_report
)


# ============================================================
# HELPER FUNCTION
# ============================================================

def safe_project_filename(project_name, report_type, extension):
    """Create a clean, project-specific download filename."""

    project = unicodedata.normalize(
        "NFKD",
        str(project_name or "GitHub_Project")
    )

    project = project.encode("ascii", "ignore").decode("ascii")

    project = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        project
    ).strip("_") or "GitHub_Project"

    report = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        str(report_type)
    ).strip("_")

    return f"{project}_{report}.{extension.lstrip('.')}"


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="RepoSage AI",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

@import url(
'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap'
);

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 5% 5%, #e0e7ff, transparent 25%),
        radial-gradient(circle at 95% 10%, #cffafe, transparent 22%),
        #f6f8fc;
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

.hero {
    padding: 2.1rem;
    border-radius: 22px;
    color: white;
    background: linear-gradient(
        120deg, #111827, #3730a3 58%, #0e7490
    );
    box-shadow: 0 18px 45px #1e293b22;
    margin-bottom: 20px;
}

.hero h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.6rem;
    margin: 0;
}

.hero p {
    color: #dbeafe;
    font-size: 1.05rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827, #172554);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stCaption {
    color: #f8fafc !important;
}

[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div {
    background: #ffffff !important;
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
}

[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] *,
[data-testid="stSidebar"] [data-baseweb="input"] * {
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
}

[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: #f8fafc !important;
    font-weight: 600 !important;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 15px;
    padding: 1rem;
    box-shadow: 0 5px 18px #0f172a0a;
}

.stButton > button,
.stDownloadButton > button {
    border: 0;
    border-radius: 11px;
    background: linear-gradient(100deg, #4f46e5, #0891b2);
    color: white;
    font-weight: 700;
    min-height: 2.7rem;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: #e9eef8;
    padding: 7px;
    border-radius: 14px;
}

.stTabs [aria-selected="true"] {
    background: white;
    color: #4338ca;
}

div[data-testid="stExpander"] {
    background: white;
    border: 1px solid #e5eaf3;
    border-radius: 13px;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    border-radius: 10px;
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
}

input::placeholder,
textarea::placeholder {
    color: #64748b !important;
    opacity: 1 !important;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "repo_url" not in st.session_state:
    st.session_state.repo_url = ""

if "question_answer" not in st.session_state:
    st.session_state.question_answer = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🔎 RepoSage AI")

    st.caption("Repository Intelligence Platform")

    st.divider()

    st.markdown("### Academic Details")

    student_name = st.text_input(
        "Student name",
        placeholder="Enter your name"
    )

    roll_number = st.text_input(
        "Roll number",
        placeholder="Enter roll number"
    )

    department = st.text_input(
        "Department",
        value="Computer Engineering"
    )

    institution = st.text_input(
        "Institution",
        placeholder="University / College name"
    )

    academic_year = st.text_input(
        "Academic year",
        value="2026-2027"
    )

    st.divider()

    st.markdown("### AI Configuration")

    use_ai = st.toggle(
        "Enable local Ollama AI",
        value=False,
        help="Enable this after installing and starting Ollama."
    )

    language = st.selectbox(
        "Explanation language",
        ["English", "Hindi"]
    )

    st.divider()

    st.caption(
        "Only analyse public repositories that you are "
        "permitted to access."
    )

    st.caption("RepoSage AI | Academic Prototype")


# ============================================================
# HERO SECTION
# ============================================================

st.markdown("""
<div class="hero">

    <h1>🔎 RepoSage AI</h1>

    <p>
        Understand GitHub repositories. Analyse code.
        Explore architecture. Generate academic reports.
    </p>

    <p>
        An intelligent software repository analysis platform.
    </p>

</div>
""", unsafe_allow_html=True)


# ============================================================
# REPOSITORY INPUT
# ============================================================

st.markdown("### Connect a GitHub Repository")

repo_url = st.text_input(
    "Public GitHub repository URL",
    value=st.session_state.repo_url,
    placeholder="https://github.com/owner/repository"
)

analyse_button = st.button(
    "🚀 Analyse Repository",
    use_container_width=True
)


if analyse_button:

    if not repo_url.strip():

        st.error("Please enter a GitHub repository URL.")

    else:

        try:

            with st.spinner(
                "Downloading and analysing repository..."
            ):

                result = analyse_repository(repo_url.strip())

                st.session_state.analysis = result

                st.session_state.repo_url = repo_url.strip()

                st.session_state.question_answer = None

            st.success("Repository analysed successfully!")

        except Exception as error:

            st.error(f"Analysis failed: {error}")


# ============================================================
# MAIN DASHBOARD
# ============================================================

data = st.session_state.analysis


if data is None:

    st.info(
        "Enter a public GitHub repository URL and select "
        "'Analyse Repository' to begin."
    )

    st.markdown("### Platform Capabilities")

    columns = st.columns(3)

    features = [

        (
            "🧠",
            "Repository Intelligence",
            "Inspect files, functions, classes and dependencies."
        ),

        (
            "💬",
            "Repository Q&A",
            "Retrieve relevant code sections to answer questions."
        ),

        (
            "🏗️",
            "Architecture Visualisation",
            "Explore relationships between source modules."
        ),

        (
            "📄",
            "Report Generator",
            "Create synopsis, progress and detailed reports."
        ),

        (
            "✨",
            "Code Explanation",
            "Understand source files in simple English or Hindi."
        ),

        (
            "🛡️",
            "Code Quality",
            "Discover tests, TODOs and documentation indicators."
        )

    ]

    for index, feature in enumerate(features):

        with columns[index % 3]:

            with st.container(border=True):

                st.markdown(
                    f"## {feature[0]} {feature[1]}"
                )

                st.write(feature[2])

    st.stop()


# ============================================================
# REPOSITORY METADATA
# ============================================================

metadata = data["metadata"]

quality = data["quality"]

st.markdown("---")

st.markdown(
    f"## 📊 {metadata.get('full_name', metadata.get('name', 'Repository'))}"
)

if metadata.get("description"):

    st.write(metadata["description"])


st.caption(
    f"Default branch: {metadata.get('default_branch', 'Unknown')} "
    f"| Stars: {metadata.get('stargazers_count', 0)} "
    f"| Forks: {metadata.get('forks_count', 0)}"
)


# ============================================================
# DASHBOARD METRICS
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Files inspected",
    len(data["files"])
)

c2.metric(
    "Python functions",
    len(data["functions"])
)

c3.metric(
    "Python classes",
    len(data["classes"])
)

c4.metric(
    "Dependencies",
    len(data["dependencies"])
)

c5.metric(
    "Test files",
    len(quality["test_files"])
)


# ============================================================
# TABS
# ============================================================

tabs = st.tabs([

    "🏠 Overview",

    "📁 Repository Intelligence",

    "✨ Code Explanation",

    "💬 Ask Repository",

    "🏗️ Architecture",

    "🛡️ Code Quality",

    "📄 Document Studio"

])


# ============================================================
# TAB 1: OVERVIEW
# ============================================================

with tabs[0]:

    st.subheader("Repository Overview")

    left, right = st.columns(2)

    with left:

        st.markdown("#### File Type Distribution")

        extension_data = data["extensions"]

        if extension_data:

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=list(extension_data.keys()),
                        values=list(extension_data.values()),
                        hole=0.55
                    )
                ]
            )

            fig.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=True
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    with right:

        st.markdown("#### Top-Level Folder Distribution")

        folder_data = data["directories"]

        if folder_data:

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=list(folder_data.values()),
                        y=list(folder_data.keys()),
                        orientation="h"
                    )
                ]
            )

            fig.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=20, b=20),
                xaxis_title="Number of files",
                yaxis_title="Folder"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    st.markdown("#### Repository Information")

    info = {

        "Repository": metadata.get("full_name", ""),

        "Description": metadata.get("description", ""),

        "Default branch": metadata.get("default_branch", ""),

        "Language": metadata.get("language", ""),

        "Stars": metadata.get("stargazers_count", 0),

        "Forks": metadata.get("forks_count", 0),

        "Open issues": metadata.get("open_issues_count", 0),

        "URL": metadata.get("html_url", "")

    }

    st.dataframe(
        pd.DataFrame(
            list(info.items()),
            columns=["Property", "Value"]
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# TAB 2: REPOSITORY INTELLIGENCE
# ============================================================

with tabs[1]:

    st.subheader("Repository Intelligence")

    st.markdown("#### File and Folder Structure")

    for path in sorted(data["files"].keys()):

        st.text("📄 " + path)

    st.divider()

    st.markdown("#### Python Functions")

    if data["functions"]:

        function_df = pd.DataFrame(data["functions"])

        st.dataframe(
            function_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No Python functions were detected.")

    st.markdown("#### Python Classes")

    if data["classes"]:

        class_df = pd.DataFrame(data["classes"])

        st.dataframe(
            class_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No Python classes were detected.")

    st.markdown("#### Detected Dependencies")

    if data["dependencies"]:

        st.write(", ".join(data["dependencies"]))

    else:

        st.info("No supported dependency manifest was detected.")

    st.markdown("#### Python Imports")

    if data["imports"]:

        st.write(", ".join(data["imports"]))


# ============================================================
# TAB 3: CODE EXPLANATION
# ============================================================

with tabs[2]:

    st.subheader("AI-Powered Code Explanation")

    file_paths = list(data["files"].keys())

    selected_file = st.selectbox(
        "Select a source file",
        file_paths,
        key="explain_file"
    )

    if selected_file:

        code = data["files"][selected_file]

        st.markdown("#### Source Code")

        st.code(
            code[:20000],
            language="python"
        )

        if st.button(
            "✨ Explain Selected File",
            use_container_width=True
        ):

            with st.spinner("Preparing code explanation..."):

                explanation = explain_code(
                    selected_file,
                    code,
                    language=language,
                    use_ai=use_ai
                )

            st.markdown("#### Explanation")

            st.markdown(explanation)


# ============================================================
# TAB 4: REPOSITORY QUESTION ANSWERING
# ============================================================

with tabs[3]:

    st.subheader("Ask Questions About Your Repository")

    st.write(
        "Ask questions about modules, functions, dependencies "
        "or how a feature is implemented."
    )

    question = st.text_area(
        "Your repository question",
        placeholder=(
            "Example: How does authentication work in this project?"
        ),
        height=100
    )

    if st.button(
        "🔍 Find Answer",
        use_container_width=True
    ):

        if not question.strip():

            st.warning("Please enter a question.")

        else:

            with st.spinner(
                "Searching relevant repository sections..."
            ):

                answer, sources = answer_repository_question(
                    data["chunks"],
                    question,
                    use_ai=use_ai
                )

                st.session_state.question_answer = (
                    answer,
                    sources
                )

    if st.session_state.question_answer:

        answer, sources = st.session_state.question_answer

        st.markdown("#### Answer")

        st.markdown(answer)

        st.markdown("#### Retrieved Evidence")

        for source in sources:

            with st.expander(
                f"{source['file']} "
                f"(Lines {source['start_line']}-"
                f"{source['end_line']})"
            ):

                st.code(source["text"])


# ============================================================
# TAB 5: ARCHITECTURE VISUALISATION
# ============================================================

with tabs[4]:

    st.subheader("Architecture Visualisation")

    st.write(
        "This graph estimates relationships between Python "
        "modules using their import statements. It is not a "
        "complete runtime call graph."
    )

    python_paths = [
        path for path in data["files"]
        if path.endswith(".py")
    ]

    module_names = {}

    for path in python_paths:

        name = PurePosixPath(path).stem

        module_names[name] = path

    edges = []

    for path in python_paths:

        content = data["files"][path]

        try:

            tree = ast.parse(content)

        except SyntaxError:

            continue

        source_name = PurePosixPath(path).stem

        for node in ast.walk(tree):

            imported = None

            if isinstance(node, ast.Import):

                imported = [
                    alias.name.split(".")[0]
                    for alias in node.names
                ]

            elif isinstance(node, ast.ImportFrom):

                if node.module:

                    imported = [
                        node.module.split(".")[0]
                    ]

            if imported:

                for target in imported:

                    if target in module_names:

                        edges.append(
                            (source_name, target)
                        )

    nodes = list(module_names.keys())

    if nodes:

        positions = {}

        for index, node in enumerate(nodes):

            angle = (
                2 * math.pi * index / max(len(nodes), 1)
            )

            positions[node] = (
                math.cos(angle),
                math.sin(angle)
            )

        edge_x = []

        edge_y = []

        for source, target in edges:

            x1, y1 = positions[source]

            x2, y2 = positions[target]

            edge_x.extend([x1, x2, None])

            edge_y.extend([y1, y2, None])

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line=dict(
                    width=1,
                    color="#94a3b8"
                ),
                hoverinfo="none"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[
                    positions[node][0]
                    for node in nodes
                ],
                y=[
                    positions[node][1]
                    for node in nodes
                ],
                mode="markers+text",
                text=nodes,
                textposition="bottom center",
                marker=dict(
                    size=25,
                    color="#4f46e5",
                    line=dict(
                        width=2,
                        color="#ffffff"
                    )
                ),
                hovertext=[
                    module_names[node]
                    for node in nodes
                ],
                hoverinfo="text"
            )
        )

        fig.update_layout(
            height=600,
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20)
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.metric(
            "Detected module relationships",
            len(edges)
        )

    else:

        st.info("No Python modules were found.")


# ============================================================
# TAB 6: CODE QUALITY
# ============================================================

with tabs[5]:

    st.subheader("Code Quality and Testing Insights")

    q1, q2, q3 = st.columns(3)

    q1.metric(
        "Test-related files",
        len(quality["test_files"])
    )

    q2.metric(
        "TODO / FIXME markers",
        len(quality["todo_items"])
    )

    q3.metric(
        "Python files",
        quality["python_files"]
    )

    st.markdown("#### Test Files")

    if quality["test_files"]:

        for item in quality["test_files"]:

            st.write("🧪", item)

    else:

        st.warning("No test-related files were detected.")

    st.markdown("#### TODO / FIXME Markers")

    if quality["todo_items"]:

        st.dataframe(
            pd.DataFrame(quality["todo_items"]),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success("No TODO/FIXME markers were detected.")

    st.markdown("#### Documentation Indicators")

    total = quality["total_functions"]

    documented = quality["documented_functions"]

    if total > 0:

        percentage = (documented / total) * 100

        st.metric(
            "Python functions with docstrings",
            f"{percentage:.1f}%"
        )

        st.progress(percentage / 100)

        st.caption(
            f"{documented} documented functions "
            f"out of {total} detected functions."
        )

    else:

        st.info("No Python functions were detected.")


# ============================================================
# TAB 7: ACADEMIC DOCUMENT STUDIO
# ============================================================

with tabs[6]:

    st.subheader("📄 Academic Document Studio")

    st.write(
        "Generate formatted academic documents using "
        "the repository analysis results."
    )

    student = {

        "name": student_name or "Student Name",

        "roll": roll_number or "Roll Number",

        "department": department,

        "institution": institution or "Institution Name",

        "year": academic_year,

        "project_name": metadata.get("name") or "GitHub Project",

        "repository": (
            metadata.get("full_name")
            or metadata.get("name")
            or ""
        ),

        "repository_url": (
            metadata.get("html_url")
            or st.session_state.repo_url
        ),

        "project_description": (
            metadata.get("description") or ""
        ),

        "primary_language": (
            metadata.get("language") or "Not specified"
        )

    }

    report_types = [

        "Synopsis",

        "Progress Report",

        "Detailed Project Report"

    ]

    for report_type in report_types:

        with st.container(border=True):

            st.markdown(f"### {report_type}")

            if report_type == "Synopsis":

                st.write(
                    "Abstract, introduction, problem statement, "
                    "objectives, methodology and expected outcome."
                )

            elif report_type == "Progress Report":

                st.write(
                    "Completed work, current results, challenges "
                    "and future work."
                )

            else:

                st.write(
                    "Detailed project documentation, requirements, "
                    "methodology, modules, results and conclusion."
                )

            col1, col2 = st.columns(2)

            safe_name = report_type.lower().replace(" ", "_")

            # ---------------- PDF GENERATION ----------------

            with col1:

                if st.button(
                    f"Generate {report_type} PDF",
                    key=f"pdf_{safe_name}",
                    use_container_width=True
                ):

                    try:

                        pdf_bytes = build_pdf_report(
                            report_type,
                            data,
                            student
                        )

                        st.download_button(
                            "⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name=safe_project_filename(
                                student["project_name"],
                                report_type,
                                "pdf"
                            ),
                            mime="application/pdf",
                            key=f"download_pdf_{safe_name}",
                            use_container_width=True
                        )

                    except Exception as error:

                        st.error(
                            f"PDF generation failed: {error}"
                        )

            # ---------------- WORD GENERATION ----------------

            with col2:

                if st.button(
                    f"Generate {report_type} Word",
                    key=f"docx_{safe_name}",
                    use_container_width=True
                ):

                    try:

                        docx_bytes = build_docx_report(
                            report_type,
                            data,
                            student
                        )

                        st.download_button(
                            "⬇️ Download Word",
                            data=docx_bytes,
                            file_name=safe_project_filename(
                                student["project_name"],
                                report_type,
                                "docx"
                            ),
                            mime=(
                                "application/vnd.openxmlformats-"
                                "officedocument.wordprocessingml.document"
                            ),
                            key=f"download_docx_{safe_name}",
                            use_container_width=True
                        )

                    except Exception as error:

                        st.error(
                            f"Word generation failed: {error}"
                        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.markdown(
    "<center><small>"
    "RepoSage AI | Intelligent Repository Analysis "
    "| Academic Project Prototype"
    "</small></center>",
    unsafe_allow_html=True
)