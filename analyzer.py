import ast
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MAX_ARCHIVE_SIZE = 40 * 1024 * 1024
MAX_FILES = 500
MAX_FILE_SIZE = 300 * 1024

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules",
    "__pycache__", "dist", "build", ".next",
    "coverage", ".idea", ".vscode"
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".cpp", ".c", ".h", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb",
    ".html", ".css", ".sql", ".sh",
    ".yaml", ".yml", ".json", ".md", ".txt",
    ".toml", ".xml"
}

DEPENDENCY_FILES = {
    "requirements.txt", "pyproject.toml",
    "pipfile", "package.json", "pom.xml",
    "build.gradle", "cargo.toml",
    "go.mod", "composer.json"
}


def parse_github_url(url):
    """Accept only public GitHub repository URLs."""

    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Please enter an HTTPS GitHub URL.")

    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValueError("Only public GitHub repository URLs are supported.")

    parts = [p for p in parsed.path.strip("/").split("/") if p]

    if len(parts) < 2:
        raise ValueError("URL must look like github.com/owner/repository.")

    owner = parts[0]
    repo = parts[1].removesuffix(".git")

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner):
        raise ValueError("Invalid GitHub owner.")

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository name.")

    return owner, repo


def download_repository(url):
    """Download a public repository as a ZIP archive."""

    owner, repo = parse_github_url(url)

    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RepoSage-AI-Academic-Project"
    }

    response = requests.get(
        api_url,
        headers=headers,
        timeout=25
    )

    if response.status_code == 404:
        raise ValueError(
            "Repository not found. Check whether the repository is public."
        )

    response.raise_for_status()

    metadata = response.json()

    if metadata.get("private"):
        raise ValueError("Private repositories are not supported.")

    branch = metadata.get("default_branch", "main")

    archive_url = (
        f"https://codeload.github.com/{owner}/{repo}"
        f"/zip/refs/heads/{branch}"
    )

    archive_response = requests.get(
        archive_url,
        headers=headers,
        timeout=45
    )

    archive_response.raise_for_status()

    if len(archive_response.content) > MAX_ARCHIVE_SIZE:
        raise ValueError(
            "Repository archive is too large for this academic prototype."
        )

    return metadata, archive_response.content


def is_allowed_file(path):
    parts = PurePosixPath(path).parts

    if any(part.lower() in SKIP_DIRS for part in parts):
        return False

    if not parts:
        return False

    filename = parts[-1].lower()
    extension = PurePosixPath(filename).suffix.lower()

    return (
        extension in SOURCE_EXTENSIONS
        or filename in DEPENDENCY_FILES
    )


def extract_repository(archive_bytes):
    """Read source files safely from the downloaded ZIP."""

    files = {}

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile:
        raise ValueError("GitHub returned an invalid repository archive.")

    with archive:
        for item in archive.infolist():

            if item.is_dir():
                continue

            if len(files) >= MAX_FILES:
                break

            if item.file_size > MAX_FILE_SIZE:
                continue

            parts = PurePosixPath(item.filename).parts

            if len(parts) < 2:
                continue

            relative_path = "/".join(parts[1:])

            if not is_allowed_file(relative_path):
                continue

            try:
                raw = archive.read(item)
                content = raw.decode("utf-8")
            except (UnicodeDecodeError, RuntimeError, OSError):
                continue

            files[relative_path] = content

    if not files:
        raise ValueError("No supported source or documentation files found.")

    return files


def parse_python_file(path, content):
    functions = []
    classes = []
    imports = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return functions, classes, imports

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "file": path,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "type": "Function"
            })

        elif isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "file": path,
                "line": node.lineno,
                "type": "Class"
            })

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])

    return functions, classes, imports


def detect_dependencies(files):
    dependencies = set()

    for path, content in files.items():
        filename = PurePosixPath(path).name.lower()

        if filename == "requirements.txt":
            for line in content.splitlines():
                line = line.strip()

                if line and not line.startswith("#"):
                    dependencies.add(line.split("==")[0].split(">=")[0])

        elif filename == "package.json":
            try:
                data = json.loads(content)

                for section in (
                    "dependencies",
                    "devDependencies"
                ):
                    dependencies.update(
                        data.get(section, {}).keys()
                    )
            except json.JSONDecodeError:
                pass

        elif filename == "pyproject.toml":
            for line in content.splitlines():
                match = re.match(
                    r"\s*[\"']?([A-Za-z0-9_.-]+)[\"']?\s*(?:[<>=!~]|$)",
                    line
                )
                if match:
                    dependencies.add(match.group(1))

        elif filename == "pom.xml":
            matches = re.findall(
                r"<artifactId>(.*?)</artifactId>",
                content
            )
            dependencies.update(matches)

    return sorted(dependencies)


def inspect_quality(files):
    test_files = []
    todo_items = []
    docstrings = 0
    python_files = 0
    documented_functions = 0
    total_functions = 0

    for path, content in files.items():

        name = PurePosixPath(path).name.lower()

        if (
            "test" in name
            or "/tests/" in "/" + path.lower()
            or "/test/" in "/" + path.lower()
        ):
            test_files.append(path)

        for line_number, line in enumerate(content.splitlines(), 1):

            if re.search(r"\b(TODO|FIXME|XXX)\b", line):
                todo_items.append({
                    "file": path,
                    "line": line_number,
                    "text": line.strip()[:160]
                })

        if path.lower().endswith(".py"):
            python_files += 1

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_functions += 1

                    if ast.get_docstring(node):
                        documented_functions += 1

                if isinstance(node, ast.ClassDef):
                    if ast.get_docstring(node):
                        docstrings += 1

    return {
        "test_files": sorted(test_files),
        "todo_items": todo_items,
        "python_files": python_files,
        "total_functions": total_functions,
        "documented_functions": documented_functions,
        "class_docstrings": docstrings
    }


def build_chunks(files):
    """Create searchable chunks for repository question answering."""

    chunks = []

    for path, content in files.items():

        lines = content.splitlines()

        if not lines:
            continue

        chunk_size = 70
        overlap = 12

        start = 0

        while start < len(lines):

            end = min(start + chunk_size, len(lines))

            text = "\n".join(lines[start:end])

            if text.strip():
                chunks.append({
                    "file": path,
                    "start_line": start + 1,
                    "end_line": end,
                    "text": text
                })

            if end == len(lines):
                break

            start = end - overlap

    return chunks


def retrieve_chunks(chunks, question, top_k=5):
    if not chunks:
        return []

    documents = [
        chunk["file"] + "\n" + chunk["text"]
        for chunk in chunks
    ]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=12000,
        ngram_range=(1, 2)
    )

    try:
        matrix = vectorizer.fit_transform(
            documents + [question]
        )
    except ValueError:
        return []

    scores = cosine_similarity(
        matrix[-1],
        matrix[:-1]
    ).flatten()

    ranked = scores.argsort()[::-1][:top_k]

    results = []

    for index in ranked:

        if scores[index] <= 0:
            continue

        result = dict(chunks[index])
        result["score"] = float(scores[index])
        results.append(result)

    return results


def call_ollama(prompt, model="llama3.2"):
    """Optional local LLM integration."""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        return response.json().get("response", "")

    except requests.RequestException:
        return None


def explain_code(path, content, language="English", use_ai=True):
    prompt = f"""
You are an experienced software engineering teacher.

Explain the following source code in {language}.

Include:
1. Purpose of the code.
2. Important functions and classes.
3. Input and output.
4. Step-by-step working.
5. Important dependencies.
6. A simple example where useful.

Do not invent functionality that is not present in the code.

File: {path}

Source code:
{content[:12000]}
"""

    if use_ai:
        answer = call_ollama(prompt)

        if answer:
            return answer

    lines = content.splitlines()

    return (
        f"File: {path}\n\n"
        f"This file contains {len(lines)} lines of code.\n"
        f"Detected programming language: "
        f"{PurePosixPath(path).suffix or 'Unknown'}.\n\n"
        "Automatic fallback explanation:\n"
        "Review the function and class listings in Repository "
        "Intelligence to understand the main components. "
        "For a generated natural-language explanation, "
        "start Ollama and install a supported local model."
    )


def answer_repository_question(chunks, question, use_ai=True):
    relevant = retrieve_chunks(chunks, question)

    if not relevant:
        return (
            "I could not find sufficiently relevant source sections. "
            "Try using the name of a function, class or module."
        ), []

    context = "\n\n".join([
        (
            f"FILE: {item['file']}\n"
            f"LINES: {item['start_line']}-{item['end_line']}\n"
            f"{item['text']}"
        )
        for item in relevant
    ])

    prompt = f"""
You are RepoSage AI, a repository analysis assistant.

Answer the question using ONLY the supplied repository context.
If the answer is not available, clearly say that the repository
does not provide enough evidence.

Cite relevant file names and line ranges.

Question:
{question}

Repository context:
{context}

Give a clear answer in simple English.
"""

    answer = call_ollama(prompt) if use_ai else None

    if not answer:
        answer = (
            "Relevant repository evidence was retrieved, but a local "
            "LLM is not available. Review the source sections below "
            "to answer the question.\n\n"
        )

        for item in relevant:
            answer += (
                f"- {item['file']} "
                f"(lines {item['start_line']}-"
                f"{item['end_line']})\n"
            )

    return answer, relevant


def analyse_repository(url):
    metadata, archive = download_repository(url)
    files = extract_repository(archive)

    all_functions = []
    all_classes = []
    all_imports = []

    for path, content in files.items():

        if path.lower().endswith(".py"):

            functions, classes, imports = parse_python_file(
                path,
                content
            )

            all_functions.extend(functions)
            all_classes.extend(classes)
            all_imports.extend(imports)

    extension_counts = Counter(
        PurePosixPath(path).suffix.lower() or "No extension"
        for path in files
    )

    dependencies = detect_dependencies(files)
    quality = inspect_quality(files)
    chunks = build_chunks(files)

    directory_counts = Counter()

    for path in files:
        parts = PurePosixPath(path).parts

        if len(parts) > 1:
            directory_counts[parts[0]] += 1
        else:
            directory_counts["Root"] += 1

    return {
        "metadata": metadata,
        "files": files,
        "functions": all_functions,
        "classes": all_classes,
        "imports": sorted(set(all_imports)),
        "dependencies": dependencies,
        "extensions": dict(extension_counts),
        "directories": dict(directory_counts),
        "quality": quality,
        "chunks": chunks
    }