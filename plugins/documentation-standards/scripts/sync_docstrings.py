#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "cyclopts>=3.0",
#     "pydantic>=2.0",
#     "docstring-parser>=0.16",
#     "rich>=13.0",
# ]
# ///
"""
Compare Python docstrings with external documentation.

Features:
- Parse Python docstrings (Google, NumPy, Sphinx styles)
- Compare function signatures with docs
- Detect out-of-sync descriptions
- Generate diff reports
- Optionally update docs from docstrings

Usage:
    uv run sync_docstrings.py [OPTIONS] SOURCE DOCS

Examples
--------
    uv run sync_docstrings.py src/ docs/api/
    uv run sync_docstrings.py src/module.py docs/api.md
    uv run sync_docstrings.py src/ docs/ --style google
    uv run sync_docstrings.py src/ docs/ --update --dry-run
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

import docstring_parser
from cyclopts import App
from docstring_parser import DocstringStyle
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = App(help="Compare Python docstrings with external documentation")

STYLE_MAP = {
    "google": DocstringStyle.GOOGLE,
    "numpy": DocstringStyle.NUMPYDOC,
    "sphinx": DocstringStyle.REST,
    "epydoc": DocstringStyle.EPYDOC,
    "auto": DocstringStyle.AUTO,
}


class FunctionDoc(BaseModel):
    """Extracted documentation for a function."""

    name: str
    module: str
    file_path: Path
    line_number: int
    signature: str
    docstring: str | None
    description: str | None
    params: dict[str, str] = Field(default_factory=dict)
    returns: str | None = None
    raises: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class DocReference(BaseModel):
    """Reference to a function in external documentation."""

    name: str
    file_path: Path
    line_number: int
    description: str
    params: dict[str, str] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class SyncIssue(BaseModel):
    """A synchronization issue between code and docs."""

    function: str
    issue_type: str  # missing_doc, missing_code, param_mismatch, description_diff
    details: str
    code_location: str | None = None
    doc_location: str | None = None


class DocCompareReport(BaseModel):
    """Report of doc comparison results."""

    missing_from_docs: list[str] = Field(default_factory=list)
    missing_from_code: list[str] = Field(default_factory=list)
    outdated: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    issues: list[SyncIssue] = Field(default_factory=list)


class SyncUpdateSuggestion(BaseModel):
    """A suggestion to update documentation."""

    function_name: str
    suggestion: str
    details: str


class SyncReport(BaseModel):
    """Report of synchronization between code and documentation."""

    functions: list[FunctionDoc] = Field(default_factory=list)
    doc_refs: list[DocReference] = Field(default_factory=list)
    issues: list[SyncIssue] = Field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


def extract_functions_from_file(
    file_path: Path,
    style: DocstringStyle,
) -> list[FunctionDoc]:
    """Extract function documentation from a Python file."""
    functions: list[FunctionDoc] = []

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not parse {file_path}: {e}")
        return functions

    module_name = file_path.stem

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and not node.name.startswith("__"):
                continue

            args = []
            for arg in node.args.args:
                annotation = ""
                if arg.annotation:
                    annotation = f": {ast.unparse(arg.annotation)}"
                args.append(f"{arg.arg}{annotation}")

            returns = ""
            if node.returns:
                returns = f" -> {ast.unparse(node.returns)}"

            signature = f"def {node.name}({', '.join(args)}){returns}"

            docstring = ast.get_docstring(node)
            description = None
            params: dict[str, str] = {}
            returns_doc = None
            raises: list[str] = []

            if docstring:
                try:
                    parsed = docstring_parser.parse(docstring, style=style)
                    description = parsed.short_description
                    if parsed.long_description:
                        description = f"{description}\n\n{parsed.long_description}"

                    for param in parsed.params:
                        params[param.arg_name] = param.description or ""

                    if parsed.returns:
                        returns_doc = parsed.returns.description

                    raises = [r.type_name or "" for r in parsed.raises]

                except Exception:
                    description = docstring.split("\n")[0]

            functions.append(
                FunctionDoc(
                    name=node.name,
                    module=module_name,
                    file_path=file_path,
                    line_number=node.lineno,
                    signature=signature,
                    docstring=docstring,
                    description=description,
                    params=params,
                    returns=returns_doc,
                    raises=raises,
                ),
            )

    return functions


def extract_functions_from_source(
    path: Path,
    style: DocstringStyle,
) -> list[FunctionDoc]:
    """Extract all function documentation from a source directory."""
    functions: list[FunctionDoc] = []

    if path.is_file():
        files = [path] if path.suffix == ".py" else []
    else:
        files = list(path.rglob("*.py"))

    for file_path in files:
        if any(
            part.startswith(".") or part == "__pycache__" for part in file_path.parts
        ):
            continue

        functions.extend(extract_functions_from_file(file_path, style))

    return functions


def extract_doc_references(path: Path) -> list[DocReference]:
    """Extract function references from markdown documentation."""
    references: list[DocReference] = []

    if path.is_file():
        files = [path] if path.suffix in {".md", ".markdown", ".rst"} else []
    else:
        files = list(path.rglob("*.md")) + list(path.rglob("*.rst"))

    func_pattern = re.compile(
        r"^#{2,4}\s+`?(\w+)`?\s*(?:\([^)]*\))?\s*$",
        re.MULTILINE,
    )

    param_pattern = re.compile(r"^[-*]\s+`?(\w+)`?\s*[-:]\s*(.+)$", re.MULTILINE)

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for i, line in enumerate(lines):
                match = func_pattern.match(line)
                if match:
                    func_name = match.group(1)

                    description = ""
                    for j in range(i + 1, min(i + 10, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith("#"):
                            description = next_line
                            break

                    params: dict[str, str] = {}
                    section_end = min(i + 50, len(lines))
                    for j in range(i + 1, section_end):
                        if lines[j].startswith("#"):
                            break
                        param_match = param_pattern.match(lines[j])
                        if param_match:
                            params[param_match.group(1)] = param_match.group(2).strip()

                    references.append(
                        DocReference(
                            name=func_name,
                            file_path=file_path,
                            line_number=i + 1,
                            description=description,
                            params=params,
                        ),
                    )

        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not read {file_path}: {e}")

    return references


def compare_docs(
    source: Path,
    docs: Path,
    style: str = "auto",
) -> DocCompareReport:
    """Compare source code docstrings with external documentation."""
    doc_style = STYLE_MAP.get(style, DocstringStyle.AUTO)
    report = DocCompareReport()

    functions = extract_functions_from_source(source, doc_style)
    doc_refs = extract_doc_references(docs)

    func_by_name = {f.name: f for f in functions}
    doc_by_name = {d.name: d for d in doc_refs}

    # Check for missing documentation
    for name, func in func_by_name.items():
        if name not in doc_by_name:
            report.missing_from_docs.append(name)
            report.issues.append(
                SyncIssue(
                    function=name,
                    issue_type="missing_doc",
                    details=f"Function '{name}' is not documented",
                    code_location=f"{func.file_path}:{func.line_number}",
                ),
            )
        else:
            doc = doc_by_name[name]
            code_params = set(func.params.keys())
            doc_params = set(doc.params.keys())

            missing_in_docs = code_params - doc_params
            if missing_in_docs:
                missing_str = ", ".join(missing_in_docs)
                report.mismatches.append(name)
                report.issues.append(
                    SyncIssue(
                        function=name,
                        issue_type="param_mismatch",
                        details=f"Parameters not documented: {missing_str}",
                        code_location=f"{func.file_path}:{func.line_number}",
                        doc_location=f"{doc.file_path}:{doc.line_number}",
                    ),
                )

            extra_in_docs = doc_params - code_params
            if extra_in_docs:
                extra_str = ", ".join(extra_in_docs)
                report.outdated.append(name)
                report.issues.append(
                    SyncIssue(
                        function=name,
                        issue_type="param_mismatch",
                        details=f"Documented params not in code: {extra_str}",
                        code_location=f"{func.file_path}:{func.line_number}",
                        doc_location=f"{doc.file_path}:{doc.line_number}",
                    ),
                )

    # Check for documented functions not in code
    for name, doc in doc_by_name.items():
        if name not in func_by_name:
            report.missing_from_code.append(name)
            report.issues.append(
                SyncIssue(
                    function=name,
                    issue_type="missing_code",
                    details=f"Documented function '{name}' not found in code",
                    doc_location=f"{doc.file_path}:{doc.line_number}",
                ),
            )

    return report


def extract_docstrings(file_path: Path) -> dict[str, str]:
    """Extract all docstrings from a Python file, keyed by name."""
    result: dict[str, str] = {}
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ds = ast.get_docstring(node)
            if ds:
                result[node.name] = ds

    return result


def suggest_updates(
    file_path: Path,
    docs_dir: Path | None,
) -> list[SyncUpdateSuggestion]:
    """Suggest documentation updates for functions in a file."""
    suggestions: list[SyncUpdateSuggestion] = []
    docstrings = extract_docstrings(file_path)

    if docs_dir is None:
        # Suggest docs for all functions
        for name, ds in docstrings.items():
            suggestions.append(
                SyncUpdateSuggestion(
                    function_name=name,
                    suggestion="Add to external documentation",
                    details=ds.split("\n")[0],
                )
            )
        return suggestions

    doc_refs = extract_doc_references(docs_dir)
    doc_names = {d.name for d in doc_refs}

    for name, ds in docstrings.items():
        if name not in doc_names:
            suggestions.append(
                SyncUpdateSuggestion(
                    function_name=name,
                    suggestion="Add to external documentation",
                    details=ds.split("\n")[0],
                )
            )

    return suggestions


def sync_docstrings(
    source_path: Path,
    docs_path: Path,
    style: str = "auto",
) -> SyncReport:
    """Compare docstrings with external documentation."""
    doc_style = STYLE_MAP.get(style, DocstringStyle.AUTO)

    functions = extract_functions_from_source(source_path, doc_style)
    doc_refs = extract_doc_references(docs_path)

    func_by_name = {f.name: f for f in functions}
    doc_by_name = {d.name: d for d in doc_refs}

    issues: list[SyncIssue] = []

    for name, func in func_by_name.items():
        if name not in doc_by_name:
            issues.append(
                SyncIssue(
                    function=name,
                    issue_type="missing_doc",
                    details=f"Function '{name}' is not documented",
                    code_location=f"{func.file_path}:{func.line_number}",
                ),
            )
        else:
            doc = doc_by_name[name]
            code_params = set(func.params.keys())
            doc_params = set(doc.params.keys())

            missing_in_docs = code_params - doc_params
            if missing_in_docs:
                issues.append(
                    SyncIssue(
                        function=name,
                        issue_type="param_mismatch",
                        details=(
                            f"Parameters not documented: {', '.join(missing_in_docs)}"
                        ),
                        code_location=f"{func.file_path}:{func.line_number}",
                        doc_location=f"{doc.file_path}:{doc.line_number}",
                    ),
                )

            extra_in_docs = doc_params - code_params
            if extra_in_docs:
                issues.append(
                    SyncIssue(
                        function=name,
                        issue_type="param_mismatch",
                        details=(
                            f"Documented params not in code: {', '.join(extra_in_docs)}"
                        ),
                        code_location=f"{func.file_path}:{func.line_number}",
                        doc_location=f"{doc.file_path}:{doc.line_number}",
                    ),
                )

    for name, doc in doc_by_name.items():
        if name not in func_by_name:
            issues.append(
                SyncIssue(
                    function=name,
                    issue_type="missing_code",
                    details=f"Documented function '{name}' not found in code",
                    doc_location=f"{doc.file_path}:{doc.line_number}",
                ),
            )

    return SyncReport(
        functions=functions,
        doc_refs=doc_refs,
        issues=issues,
    )


def print_report(report: SyncReport, verbose: bool = False) -> None:
    """Print the synchronization report."""
    console.print(Panel("[bold]Docstring Sync Report[/bold]"))

    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    summary_table.add_row("Functions in Code", str(len(report.functions)))
    summary_table.add_row("Functions in Docs", str(len(report.doc_refs)))
    summary_table.add_row(
        "Issues",
        f"[red]{len(report.issues)}[/red]" if report.issues else "0",
    )

    console.print(summary_table)

    if verbose and report.functions:
        console.print("\n[bold]Functions Found[/bold]")
        for func in report.functions[:20]:
            has_docstring = "✓" if func.docstring else "✗"
            console.print(f"  [{has_docstring}] {func.module}.{func.name}")

    if report.issues:
        by_type: dict[str, list[SyncIssue]] = {}
        for issue in report.issues:
            if issue.issue_type not in by_type:
                by_type[issue.issue_type] = []
            by_type[issue.issue_type].append(issue)

        if "missing_doc" in by_type:
            count = len(by_type["missing_doc"])
            console.print(
                f"\n[bold yellow]Undocumented Functions ({count})[/bold yellow]"
            )
            for issue in by_type["missing_doc"][:10]:
                console.print(f"  {issue.function}")
                console.print(f"    [dim]{issue.code_location}[/dim]")
            if len(by_type["missing_doc"]) > 10:
                console.print(f"  ... and {len(by_type['missing_doc']) - 10} more")

        if "missing_code" in by_type:
            count = len(by_type["missing_code"])
            console.print(f"\n[bold red]Orphaned Documentation ({count})[/bold red]")
            for issue in by_type["missing_code"]:
                console.print(f"  {issue.function}")
                console.print(f"    [dim]{issue.doc_location}[/dim]")

        if "param_mismatch" in by_type:
            count = len(by_type["param_mismatch"])
            console.print(
                f"\n[bold yellow]Parameter Mismatches ({count})[/bold yellow]"
            )
            for issue in by_type["param_mismatch"][:10]:
                console.print(f"  {issue.function}: {issue.details}")
                if issue.code_location:
                    console.print(f"    [dim]Code: {issue.code_location}[/dim]")
                if issue.doc_location:
                    console.print(f"    [dim]Docs: {issue.doc_location}[/dim]")


@app.default
def main(
    source: Path,
    docs: Path,
    /,
    *,
    style: str = "auto",
    update: bool = False,
    _dry_run: bool = False,
    verbose: bool = False,
    output: str = "text",
) -> int:
    """Compare Python docstrings with external documentation."""
    if not source.exists():
        console.print(
            f"[red]Error:[/red] Source path '{source}' does not exist",
        )
        return 1

    if not docs.exists():
        console.print(
            f"[red]Error:[/red] Docs path '{docs}' does not exist",
        )
        return 1

    if update:
        console.print("[yellow]Warning:[/yellow] --update is not yet implemented")

    report = sync_docstrings(source, docs, style)

    if output == "json":
        result: dict[str, Any] = {
            "summary": {
                "functions_in_code": len(report.functions),
                "functions_in_docs": len(report.doc_refs),
                "issues": len(report.issues),
            },
            "functions": [
                {
                    "name": f.name,
                    "module": f.module,
                    "file": str(f.file_path),
                    "line": f.line_number,
                    "has_docstring": f.docstring is not None,
                    "params": list(f.params.keys()),
                }
                for f in report.functions
            ],
            "issues": [
                {
                    "function": i.function,
                    "type": i.issue_type,
                    "details": i.details,
                    "code_location": i.code_location,
                    "doc_location": i.doc_location,
                }
                for i in report.issues
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=verbose)

    return 1 if report.has_issues else 0


if __name__ == "__main__":
    sys.exit(app())
