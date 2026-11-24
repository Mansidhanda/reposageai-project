"""Project-specific academic report generation for RepoSage AI.

The analysed GitHub repository is the subject of each generated document.
RepoSage AI is only the document-generation platform.
"""
from datetime import date
from io import BytesIO
import html
import re
import unicodedata

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether
)


NAVY = "#17365D"
BLUE = "#244A73"
LIGHT_BLUE = "#EAF0F6"


def _text(value, fallback="Not provided"):
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def _project_info(data, student):
    metadata = data.get("metadata", {}) or {}
    student = student or {}

    name = _text(
        student.get("project_name") or metadata.get("name"),
        "GitHub Project"
    )

    full_name = _text(
        student.get("repository") or metadata.get("full_name"), name
    )

    description = _text(
        student.get("project_description") or metadata.get("description"),
        "No repository description was supplied by GitHub."
    )

    language = _text(
        student.get("primary_language") or metadata.get("language"),
        "Not specified"
    )

    url = _text(
        student.get("repository_url") or metadata.get("html_url"),
        "Not provided"
    )

    return {
        "name": name,
        "full_name": full_name,
        "description": description,
        "language": language,
        "url": url,
        "branch": _text(metadata.get("default_branch"), "Not specified"),
        "stars": metadata.get("stargazers_count", 0),
        "forks": metadata.get("forks_count", 0),
    }


def _student_info(student):
    student = student or {}

    return {
        "name": _text(student.get("name"), "Student Name"),
        "roll": _text(student.get("roll"), "Roll Number"),
        "department": _text(student.get("department"), "Department"),
        "institution": _text(student.get("institution"), "Institution"),
        "year": _text(student.get("year"), str(date.today().year)),
        "guide": _text(
            student.get("guide") or student.get("mentor"),
            "To be completed"
        ),
        "team": _text(student.get("team"), "To be completed"),
    }


def _as_list(value):
    if not value:
        return []

    if isinstance(value, dict):
        return list(value.keys())

    return list(value)


def get_sections(kind, data, student):
    """Return report sections based on the selected repository analysis."""

    info = _project_info(data, student)
    quality = data.get("quality", {}) or {}
    files = data.get("files", {}) or {}
    functions = data.get("functions", []) or []
    classes = data.get("classes", []) or []
    dependencies = _as_list(data.get("dependencies", []))
    imports = _as_list(data.get("imports", []))
    extensions = data.get("extensions", {}) or {}

    technologies = [f"Primary language: {info['language']}"]
    technologies.extend(dependencies[:35])

    if not dependencies:
        technologies.append(
            "No supported dependency manifest was detected."
        )

    analysis_summary = [
        f"Repository: {info['full_name']}",
        f"Repository URL: {info['url']}",
        f"Default branch: {info['branch']}",
        f"Primary language: {info['language']}",
        f"Files inspected: {len(files)}",
        f"Python functions detected: {len(functions)}",
        f"Python classes detected: {len(classes)}",
        f"Dependencies identified: {len(dependencies)}",
        f"Test-related files detected: {len(quality.get('test_files', []))}",
        f"TODO/FIXME markers detected: {len(quality.get('todo_items', []))}",
    ]

    if kind == "Synopsis":
        return [
            ("Abstract", [
                f"{info['name']} is the software project represented by the public GitHub repository {info['full_name']}. {info['description']} This synopsis is prepared from the repository metadata and the source files inspected by the analysis system. The available analysis identifies {len(files)} files, {len(functions)} Python functions and {len(classes)} Python classes."
            ]),

            ("Chapter 1 – Introduction", [
                f"The project {info['name']} is hosted at {info['url']}. Its GitHub description is: {info['description']}",
                f"The repository identifies {info['language']} as its primary programming language. The default branch is {info['branch']}. The analysis provides an initial view of the available files, code structures and declared dependencies."
            ]),

            ("Problem Statement", [
                f"The purpose and problem addressed by {info['name']} should be described using the project's actual requirements and implementation. The repository metadata currently available is: {info['description']} The detailed user problem and intended beneficiaries should be confirmed from the project's README and requirements before academic submission."
            ]),

            ("Objectives", [
                "Understand the purpose and scope of the analysed repository.",
                "Identify the principal programming language and available project files.",
                "Inspect supported source files for functions, classes and imports.",
                "Identify dependencies declared in supported project manifests.",
                "Prepare a structured synopsis based on the available repository evidence."
            ]),

            ("Chapter 2 – Proposed Methodology", [
                "The repository is obtained from its public GitHub URL. The analysis process retrieves repository metadata, downloads and extracts supported files, and inspects source code and dependency manifests. Python files are parsed using AST to identify functions, classes and imports. Repository code chunks are indexed for lexical retrieval using TF-IDF and cosine similarity. Optional local language-model assistance is available only when configured and enabled."
            ]),

            ("Technologies Identified", technologies),

            ("Chapter 3 – Applications and Scope", [
                f"The applications of {info['name']} must be determined from its documented features and intended users. The repository analysis can support an initial technical overview, but the project's actual deployment context and user scenarios should be verified against its documentation."
            ]),

            ("Expected Outcome", [
                f"The expected outcome is a clear academic description of {info['name']} supported by the repository's metadata and inspected source files. The final synopsis should be reviewed against the actual project requirements and institutional format."
            ])
        ]

    if kind == "Progress Report":
        return [
            ("Project Overview", [
                f"Project title: {info['name']}",
                f"Repository: {info['full_name']}",
                f"Description: {info['description']}",
                f"Repository URL: {info['url']}"
            ]),

            ("Work Completed / Repository Analysis", analysis_summary),

            ("Technologies and Dependencies", technologies),

            ("Repository Structure", [
                f"File extension distribution: {', '.join(f'{key}: {value}' for key, value in extensions.items()) or 'Not available'}",
                f"Detected imports: {', '.join(map(str, imports[:40])) if imports else 'No imports were extracted.'}"
            ]),

            ("Current Limitations", [
                "The report reflects only the files and metadata returned by the current repository analysis.",
                "Python AST analysis is more detailed than analysis for other languages.",
                "TF-IDF retrieval is lexical and may not identify all semantically related code.",
                "The quality indicators are preliminary static indicators, not a complete quality or security audit.",
                "Repository code is inspected but is not executed by the analysis process."
            ]),

            ("Work Remaining / Future Work", [
                "Verify the generated project description and objectives against the repository README and project requirements.",
                "Review all detected dependencies and module relationships.",
                "Add manually verified implementation screenshots and test evidence where required.",
                "Complete the institution-specific sections, supervisor remarks and signatures."
            ])
        ]

    return [
        ("Abstract", [
            f"This report presents the analysed software project {info['name']}, hosted in the GitHub repository {info['full_name']}. {info['description']} The repository analysis retrieved project metadata and inspected {len(files)} files. It detected {len(functions)} Python functions, {len(classes)} Python classes and {len(dependencies)} dependencies. The findings in this report are limited to information available from the analysed repository."
        ]),

        ("Chapter 1 – Introduction", [
            f"Project title: {info['name']}",
            f"Project description: {info['description']}",
            f"Repository URL: {info['url']}",
            f"Primary language: {info['language']}. Default branch: {info['branch']}."
        ]),

        ("Problem Statement and Objectives", [
            f"The GitHub metadata describes {info['name']} as follows: {info['description']} The specific problem statement, user requirements and measurable objectives should be validated using the project's own specification or README; they cannot be conclusively inferred from repository metadata alone.",
            "The analysis objectives are to inspect repository structure, identify supported source-code elements, detect declared dependencies and provide an evidence-based technical overview."
        ]),

        ("Chapter 2 – System and Technology Information", technologies + [
            "The analysis platform uses Python and Streamlit for the interface, GitHub REST API access for repository metadata, Python AST for Python source inspection, TF-IDF and cosine similarity for lexical code retrieval, Plotly for visualisation, python-docx for Word output and ReportLab for PDF output."
        ]),

        ("Chapter 3 – Repository Analysis and Architecture", [
            "The repository workflow consists of URL validation, metadata retrieval, archive download, supported-file extraction, source inspection, dependency detection, code chunking and report generation.",
            f"The current repository contains {len(files)} inspected files. Detected Python functions: {len(functions)}. Detected Python classes: {len(classes)}. Extracted imports: {len(imports)}."
        ]),

        ("Chapter 4 – Methodology", [
            "1. Accept the public GitHub repository URL.",
            "2. Validate the repository address and retrieve metadata.",
            "3. Download and extract the repository archive.",
            "4. Inspect supported source files and project manifests.",
            "5. Parse Python files using AST to identify functions, classes and imports.",
            "6. Create searchable code chunks and retrieve relevant sections using TF-IDF and cosine similarity.",
            "7. Generate repository statistics, visualisations and academic documents."
        ]),

        ("Chapter 5 – Analysis Results", analysis_summary),

        ("Chapter 6 – Dependencies and File Distribution", [
            f"Dependencies: {', '.join(map(str, dependencies[:60])) if dependencies else 'No supported dependency manifest was detected.'}",
            f"File distribution: {', '.join(f'{key}: {value}' for key, value in extensions.items()) if extensions else 'Not available.'}"
        ]),

        ("Chapter 7 – Limitations", [
            "The findings depend on the files and metadata available from the public repository at the time of analysis.",
            "Detailed AST-based structural analysis currently focuses on Python.",
            "TF-IDF retrieval is based on lexical similarity rather than semantic code embeddings.",
            "Architecture visualisation estimates Python module import relationships and is not a complete runtime call graph.",
            "Quality indicators are preliminary and should not be interpreted as a full software quality or security audit."
        ]),

        ("Chapter 8 – Future Scope", [
            "Expand source-code analysis to additional programming languages.",
            "Improve retrieval with semantic code embeddings.",
            "Enhance architecture and dependency visualisation.",
            "Add more repository-specific documentation and testing evidence.",
            "Introduce institution-specific report templates and stronger content verification."
        ]),

        ("Chapter 9 – Conclusion", [
            f"The analysis provides a structured technical overview of {info['name']} using the repository metadata and supported source files available at the time of analysis. The report should be checked against the project's actual requirements, README, implementation and institutional guidelines before submission."
        ]),

        ("References", [
            f"GitHub repository: {info['url']}",
            "Python documentation: https://docs.python.org/3/",
            "Streamlit documentation: https://docs.streamlit.io/",
            "Scikit-learn documentation: https://scikit-learn.org/stable/"
        ])
    ]


def _docx_set_run(run, size=12, bold=False, color=None):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold

    if color:
        run.font.color.rgb = RGBColor(*color)


def _docx_page_number(section, project_name):
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = footer.add_run(f"{project_name} | Page ")
    _docx_set_run(run, size=9, color=(90, 100, 115))

    # Word field for a live page number.
    field = footer.add_run()
    _docx_set_run(field, size=9, color=(90, 100, 115))

    field._r.append(__import__("docx").oxml.OxmlElement("w:fldChar"))
    field._r[-1].set(
        __import__("docx").oxml.ns.qn("w:fldCharType"), "begin"
    )

    instr = __import__("docx").oxml.OxmlElement("w:instrText")
    instr.set(
        __import__("docx").oxml.ns.qn("xml:space"), "preserve"
    )
    instr.text = " PAGE "
    field._r.append(instr)

    end = __import__("docx").oxml.OxmlElement("w:fldChar")
    end.set(
        __import__("docx").oxml.ns.qn("w:fldCharType"), "end"
    )
    field._r.append(end)


def build_docx_report(kind, data, student):
    info = _project_info(data, student)
    student_info = _student_info(student)
    sections = get_sections(kind, data, student)

    doc = Document()
    sec = doc.sections[0]

    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin, sec.bottom_margin = Inches(0.85), Inches(0.8)
    sec.left_margin, sec.right_margin = Inches(1), Inches(0.85)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(7)

    for style_name in ("Heading 1", "Heading 2"):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(14)
        style.font.bold = True
        style.font.color.rgb = RGBColor(23, 54, 93)
        style.paragraph_format.space_before = Pt(14)
        style.paragraph_format.space_after = Pt(7)
        style.paragraph_format.keep_with_next = True

    _docx_page_number(sec, info["name"])

    # Professional cover page centred on the analysed repository.
    p = doc.add_paragraph("\n\n\n")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _docx_set_run(
        p.add_run(info["name"].upper()), 24, True, (23, 54, 93)
    )

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _docx_set_run(
        p.add_run(kind.upper()), 16, True, (36, 74, 115)
    )

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _docx_set_run(
        p.add_run(info["description"]), 11, False, (75, 85, 99)
    )

    doc.add_paragraph("\n")

    cover_rows = [
        ("Submitted by", student_info["name"]),
        ("Roll number", student_info["roll"]),
        ("Department", student_info["department"]),
        ("Institution", student_info["institution"]),
        ("Academic year", student_info["year"]),
        ("Project repository", info["full_name"]),
        ("Repository URL", info["url"]),
        ("Project guide", student_info["guide"]),
    ]

    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"

    for label, value in cover_rows:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = label, value

        for run in cells[0].paragraphs[0].runs:
            _docx_set_run(run, 10, True, (23, 54, 93))

        for run in cells[1].paragraphs[0].runs:
            _docx_set_run(run, 10)

    doc.add_page_break()

    doc.add_heading("TABLE OF CONTENTS", level=1)

    for index, (heading, _) in enumerate(sections, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.15)
        p.add_run(f"{index}. {heading}")

    doc.add_page_break()

    doc.add_heading(f"{info['name']} – {kind}", level=1)

    for heading, paragraphs in sections:
        doc.add_heading(heading, level=1)

        for item in paragraphs:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.5
            p.add_run(str(item))

    output = BytesIO()
    doc.save(output)

    return output.getvalue()


def _pdf_footer(project_name):
    def draw(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D7DEE8"))
        canvas.line(
            0.8 * inch, 0.62 * inch,
            A4[0] - 0.8 * inch, 0.62 * inch
        )
        canvas.setFont("Times-Roman", 9)
        canvas.setFillColor(colors.HexColor("#5B6573"))
        canvas.drawCentredString(
            A4[0] / 2,
            0.42 * inch,
            f"{project_name} | Page {document.page}"
        )
        canvas.restoreState()

    return draw


def build_pdf_report(kind, data, student):
    info = _project_info(data, student)
    student_info = _student_info(student)
    sections = get_sections(kind, data, student)

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=0.85 * inch,
        leftMargin=0.85 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.85 * inch,
        title=f"{info['name']} – {kind}",
        author=student_info["name"],
        subject=f"Academic documentation for {info['name']}"
    )

    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ProjectTitle",
        parent=base["Title"],
        fontName="Times-Bold",
        fontSize=23,
        leading=29,
        alignment=TA_CENTER,
        textColor=colors.HexColor(NAVY),
        spaceAfter=16
    )

    subtitle_style = ParagraphStyle(
        "ProjectSubtitle",
        parent=base["Heading2"],
        fontName="Times-Bold",
        fontSize=15,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor(BLUE),
        spaceAfter=14
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=base["Heading2"],
        fontName="Times-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor(NAVY),
        spaceBefore=13,
        spaceAfter=7,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "AcademicBody",
        parent=base["BodyText"],
        fontName="Times-Roman",
        fontSize=12,
        leading=18,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )

    center_style = ParagraphStyle(
        "CoverInfo",
        parent=body_style,
        alignment=TA_CENTER,
        leading=16
    )

    small_style = ParagraphStyle(
        "SmallInfo",
        parent=body_style,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#536273")
    )

    story = [
        Spacer(1, 1.15 * inch),
        Paragraph(html.escape(info["name"].upper()), title_style),
        Paragraph(html.escape(kind.upper()), subtitle_style),
        Paragraph(html.escape(info["description"]), center_style),
        Spacer(1, 0.35 * inch)
    ]

    cover_data = [
        ["Submitted by", student_info["name"]],
        ["Roll number", student_info["roll"]],
        ["Department", student_info["department"]],
        ["Institution", student_info["institution"]],
        ["Academic year", student_info["year"]],
        ["Project repository", info["full_name"]],
        ["Repository URL", info["url"]],
        ["Project guide", student_info["guide"]],
    ]

    safe_cover = [
        [
            Paragraph(html.escape(str(a)), small_style),
            Paragraph(html.escape(str(b)), small_style)
        ]
        for a, b in cover_data
    ]

    cover_table = Table(
        safe_cover,
        colWidths=[1.55 * inch, 4.85 * inch],
        hAlign="CENTER"
    )

    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LIGHT_BLUE)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D3DF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    story += [
        cover_table,
        PageBreak(),
        Paragraph("TABLE OF CONTENTS", title_style)
    ]

    for index, (heading, _) in enumerate(sections, 1):
        story.append(
            Paragraph(f"{index}. {html.escape(heading)}", body_style)
        )

    story += [
        PageBreak(),
        Paragraph(html.escape(f"{info['name']} – {kind}"), title_style)
    ]

    for heading, paragraphs in sections:
        block = [
            Paragraph(html.escape(heading), heading_style)
        ]

        for item in paragraphs:
            block.append(
                Paragraph(
                    html.escape(str(item)).replace("\n", "<br/>"),
                    body_style
                )
            )

        story.append(
            KeepTogether(block) if len(block) <= 3 else block[0]
        )

        if len(block) > 3:
            story.extend(block[1:])

    doc.build(
        story,
        onFirstPage=_pdf_footer(info["name"]),
        onLaterPages=_pdf_footer(info["name"])
    )

    return output.getvalue()