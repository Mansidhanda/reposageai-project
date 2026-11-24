# RepoSage AI

RepoSage AI analyses public GitHub repositories and creates downloadable PDF and DOCX reports.

## Features
- Validates public GitHub repository URLs.
- Clones the repository shallowly.
- Detects programming languages, common frameworks and dependency files.
- Builds a directory tree and identifies conventional entry/documentation files.
- Uses Python AST to extract functions, classes and imports.
- Generates PDF and Word reports.

## Requirements
- Python 3.10 or newer (Python 3.12 recommended)
- Git installed and available in PATH
- Internet connection

## Windows setup

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed in the terminal, usually http://localhost:8501.

## Current limitations
This version performs static analysis only; it does not run untrusted repository code. Framework detection is heuristic. Python AST analysis extracts structural information but does not establish runtime behaviour. The analyser caps file count and file sizes.

## Suggested advanced extensions
1. Add a retrieval-augmented question-answering layer over repository files.
2. Add call-graph and import-dependency visualisation.
3. Add support for JavaScript/TypeScript, Java and other language AST parsers.
4. Add configurable report templates and project-specific report sections.
5. Add test discovery, API endpoint extraction and architecture diagrams.
6. Add secure optional LLM integration with evidence citations.
