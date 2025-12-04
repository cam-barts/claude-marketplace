#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "libcst>=1.0",
# ]
# ///
"""
Generate test scaffolding for Python source files.

Creates test files with:
- Test function stubs for all public functions
- Appropriate imports
- Hypothesis strategy decorators for typed functions
- Parametrized test cases for edge cases
- Follows Arrange-Act-Assert pattern

Usage:
    uv run generate_test_scaffold.py [OPTIONS] PATH

Examples
--------
    uv run generate_test_scaffold.py src/mymodule.py
    uv run generate_test_scaffold.py src/ --output tests/
    uv run generate_test_scaffold.py src/mymodule.py --hypothesis
    uv run generate_test_scaffold.py src/mymodule.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import libcst as cst
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

console = Console()


@dataclass
class FunctionInfo:
    """Information about a function to generate tests for."""

    name: str
    params: list[tuple[str, str | None]]  # (name, type_annotation)
    return_type: str | None
    is_method: bool = False
    is_async: bool = False
    docstring: str | None = None
    raises: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    methods: list[FunctionInfo] = field(default_factory=list)
    docstring: str | None = None


@dataclass
class ModuleInfo:
    """Information about a module."""

    name: str
    path: Path
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


class FunctionVisitor(cst.CSTVisitor):
    """Extract function and class information from a module."""

    def __init__(self) -> None:
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self._current_class: ClassInfo | None = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:
        """Visit function definitions."""
        name = node.name.value

        # Skip private functions
        if name.startswith("_") and not name.startswith("__"):
            return False

        # Skip dunder methods except __init__
        if name.startswith("__") and name != "__init__":
            return False

        # Extract parameters
        params: list[tuple[str, str | None]] = []
        for param in node.params.params:
            param_name = param.name.value
            if param_name == "self":
                continue

            type_ann = None
            if param.annotation:
                type_ann = self._annotation_to_string(param.annotation.annotation)
            params.append((param_name, type_ann))

        # Extract return type
        return_type = None
        if node.returns:
            return_type = self._annotation_to_string(node.returns.annotation)

        # Extract docstring
        docstring = None
        if node.body.body:
            first_stmt = node.body.body[0]
            is_simple = isinstance(first_stmt, cst.SimpleStatementLine)
            has_expr = (
                is_simple
                and first_stmt.body
                and isinstance(first_stmt.body[0], cst.Expr)
            )
            if has_expr:
                expr = first_stmt.body[0].value
                if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString)):
                    docstring = self._extract_string(expr)

        # Detect raised exceptions from docstring
        raises: list[str] = []
        if docstring:
            raises = self._extract_raises_from_docstring(docstring)

        func_info = FunctionInfo(
            name=name,
            params=params,
            return_type=return_type,
            is_method=self._current_class is not None,
            is_async=isinstance(node.asynchronous, cst.Asynchronous),
            docstring=docstring,
            raises=raises,
        )

        if self._current_class:
            self._current_class.methods.append(func_info)
        else:
            self.functions.append(func_info)

        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        """Visit class definitions."""
        name = node.name.value

        # Skip private classes
        if name.startswith("_"):
            return False

        # Extract docstring
        docstring = None
        if node.body.body:
            first_stmt = node.body.body[0]
            is_simple = isinstance(first_stmt, cst.SimpleStatementLine)
            has_expr = (
                is_simple
                and first_stmt.body
                and isinstance(first_stmt.body[0], cst.Expr)
            )
            if has_expr:
                expr = first_stmt.body[0].value
                if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString)):
                    docstring = self._extract_string(expr)

        self._current_class = ClassInfo(name=name, docstring=docstring)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: ARG002
        """Leave class definition."""
        if self._current_class:
            self.classes.append(self._current_class)
            self._current_class = None

    def _annotation_to_string(self, node: cst.BaseExpression) -> str:
        """Convert an annotation node to string."""
        if isinstance(node, cst.Name):
            return node.value
        if isinstance(node, cst.Attribute):
            return f"{self._annotation_to_string(node.value)}.{node.attr.value}"
        if isinstance(node, cst.Subscript):
            base = self._annotation_to_string(node.value)
            slices = []
            for s in node.slice:
                if isinstance(s, cst.SubscriptElement):
                    slices.append(self._annotation_to_string(s.slice.value))
            return f"{base}[{', '.join(slices)}]"
        return "Any"

    def _extract_string(self, node: cst.BaseExpression) -> str:
        """Extract string value from a string node."""
        if isinstance(node, cst.SimpleString):
            return node.evaluated_value or ""
        if isinstance(node, cst.ConcatenatedString):
            parts = []
            for part in node.left, node.right:
                parts.append(self._extract_string(part))
            return "".join(parts)
        return ""

    def _extract_raises_from_docstring(self, docstring: str) -> list[str]:
        """Extract exception types from docstring Raises section."""
        raises = []
        in_raises = False
        for line in docstring.split("\n"):
            line = line.strip()
            if line.lower().startswith("raises:"):
                in_raises = True
                continue
            if in_raises:
                if line and not line[0].isspace() and ":" in line:
                    # New section
                    break
                if ":" in line:
                    exc_type = line.split(":")[0].strip()
                    if exc_type:
                        raises.append(exc_type)
        return raises


def parse_module(path: Path) -> ModuleInfo:
    """Parse a Python module and extract function/class info."""
    content = path.read_text(encoding="utf-8")
    tree = cst.parse_module(content)

    visitor = FunctionVisitor()
    tree.walk(visitor)

    module_name = path.stem

    return ModuleInfo(
        name=module_name,
        path=path,
        functions=visitor.functions,
        classes=visitor.classes,
    )


def type_to_hypothesis_strategy(type_str: str | None) -> str | None:
    """Convert a type annotation to a Hypothesis strategy."""
    if not type_str:
        return None

    mapping = {
        "int": "st.integers()",
        "float": "st.floats(allow_nan=False, allow_infinity=False)",
        "str": "st.text(max_size=100)",
        "bool": "st.booleans()",
        "bytes": "st.binary(max_size=100)",
        "None": "st.none()",
        "Any": "st.from_type(type)",
    }

    if type_str in mapping:
        return mapping[type_str]

    # Handle generic types
    if type_str.startswith("list["):
        inner = type_str[5:-1]
        inner_strategy = type_to_hypothesis_strategy(inner)
        if inner_strategy:
            return f"st.lists({inner_strategy}, max_size=10)"
        return "st.lists(st.integers(), max_size=10)"

    if type_str.startswith("dict["):
        # dict[K, V]
        inner = type_str[5:-1]
        parts = inner.split(", ")
        if len(parts) == 2:
            k_strategy = type_to_hypothesis_strategy(parts[0]) or "st.text(max_size=10)"
            v_strategy = type_to_hypothesis_strategy(parts[1]) or "st.integers()"
            return f"st.dictionaries({k_strategy}, {v_strategy}, max_size=5)"

    if type_str.startswith("Optional[") or type_str.endswith(" | None"):
        if type_str.startswith("Optional["):
            inner = type_str[9:-1]
        else:
            inner = type_str.replace(" | None", "")
        inner_strategy = type_to_hypothesis_strategy(inner)
        if inner_strategy:
            return f"st.none() | {inner_strategy}"

    if type_str.startswith("tuple["):
        inner = type_str[6:-1]
        parts = inner.split(", ")
        strategies = [type_to_hypothesis_strategy(p) or "st.integers()" for p in parts]
        return f"st.tuples({', '.join(strategies)})"

    if type_str.startswith("set["):
        inner = type_str[4:-1]
        inner_strategy = type_to_hypothesis_strategy(inner)
        if inner_strategy:
            return f"st.frozensets({inner_strategy}, max_size=10)"

    # For unknown types, return None (user needs to define)
    return None


def generate_test_function(
    func: FunctionInfo,
    module_name: str,  # noqa: ARG001
    include_hypothesis: bool = True,
    style: str = "function",
) -> str:
    """Generate test code for a function."""
    lines = []
    indent = "    " if style == "class" else ""

    # Basic test
    test_name = f"test_{func.name}" if not func.is_method else f"test_{func.name}"
    if func.name == "__init__":
        test_name = "test_init"

    lines.append(
        f"{indent}def {test_name}(self):" if style == "class" else f"def {test_name}():"
    )
    lines.append(f'{indent}    """Test {func.name} basic functionality."""')
    lines.append(f"{indent}    # Arrange")

    # Generate sample values for parameters
    for param_name, param_type in func.params:
        sample_value = _get_sample_value(param_type)
        lines.append(f"{indent}    {param_name} = {sample_value}")

    lines.append(f"{indent}    # Act")
    call_args = ", ".join(p[0] for p in func.params)
    if func.is_async:
        lines.append(f"{indent}    result = await {func.name}({call_args})")
    else:
        lines.append(f"{indent}    result = {func.name}({call_args})")

    lines.append(f"{indent}    # Assert")
    lines.append(
        f"{indent}    assert result is not None  # TODO: Add specific assertions"
    )
    lines.append("")

    # Generate hypothesis test if we have type annotations
    if include_hypothesis and func.params:
        strategies = []
        all_have_strategies = True
        for param_name, param_type in func.params:
            strategy = type_to_hypothesis_strategy(param_type)
            if strategy:
                strategies.append(f"{param_name}={strategy}")
            else:
                all_have_strategies = False

        if all_have_strategies and strategies:
            lines.append(f"{indent}@given({', '.join(strategies)})")
            hyp_params = ", ".join(f"{p[0]}: {p[1] or 'Any'}" for p in func.params)
            if style == "class":
                lines.append(
                    f"{indent}def test_{func.name}_property(self, {hyp_params}):"
                )
            else:
                lines.append(f"def test_{func.name}_property({hyp_params}):")
            lines.append(f'{indent}    """Property-based test for {func.name}."""')
            if func.is_async:
                lines.append(f"{indent}    result = await {func.name}({call_args})")
            else:
                lines.append(f"{indent}    result = {func.name}({call_args})")
            lines.append(f"{indent}    # TODO: Add property assertions")
            lines.append(f"{indent}    assert True  # Replace with actual property")
            lines.append("")

    # Generate exception tests
    for exc_type in func.raises:
        exc_test_name = f"test_{func.name}_raises_{exc_type.lower()}"
        if style == "class":
            lines.append(f"{indent}def {exc_test_name}(self):")
        else:
            lines.append(f"def {exc_test_name}():")
        lines.append(f'{indent}    """Test that {func.name} raises {exc_type}."""')
        lines.append(f"{indent}    with pytest.raises({exc_type}):")
        lines.append(
            f"{indent}        {func.name}(...)  # TODO: Add args to trigger exception"
        )
        lines.append("")

    return "\n".join(lines)


def _get_sample_value(type_str: str | None) -> str:
    """Get a sample value for a type."""
    if not type_str:
        return "None  # TODO: Provide value"

    mapping = {
        "int": "1",
        "float": "1.0",
        "str": '"test"',
        "bool": "True",
        "bytes": 'b"test"',
        "None": "None",
    }

    if type_str in mapping:
        return mapping[type_str]

    if type_str.startswith("list["):
        return "[]"
    if type_str.startswith("dict["):
        return "{}"
    if type_str.startswith("set["):
        return "set()"
    if type_str.startswith("tuple["):
        return "()"
    if type_str.startswith("Optional[") or type_str.endswith(" | None"):
        return "None"

    return "None  # TODO: Provide value"


def generate_test_file(
    module: ModuleInfo,
    include_hypothesis: bool = True,
    style: str = "class",
) -> str:
    """Generate a complete test file for a module."""
    lines = []

    # Module docstring
    lines.append(f'"""Tests for {module.name} module."""')
    lines.append("")

    # Imports
    lines.append("import pytest")
    if include_hypothesis:
        lines.append("from hypothesis import given, strategies as st")
    lines.append("")

    # Import from source module
    imports = []
    for func in module.functions:
        imports.append(func.name)
    for cls in module.classes:
        imports.append(cls.name)

    if imports:
        # Calculate module import path
        module_path = (
            str(module.path.with_suffix("")).replace("/", ".").replace("\\", ".")
        )
        # Remove leading dots
        while module_path.startswith("."):
            module_path = module_path[1:]
        lines.append(f"from {module_path} import {', '.join(imports)}")
        lines.append("")
    lines.append("")

    # Generate tests for standalone functions
    if module.functions:
        if style == "class":
            for func in module.functions:
                class_name = "".join(word.title() for word in func.name.split("_"))
                lines.append(f"class Test{class_name}:")
                lines.append(f'    """Tests for {func.name} function."""')
                lines.append("")
                test_code = generate_test_function(
                    func, module.name, include_hypothesis, style="class"
                )
                lines.append(test_code)
                lines.append("")
        else:
            for func in module.functions:
                test_code = generate_test_function(
                    func, module.name, include_hypothesis, style="function"
                )
                lines.append(test_code)

    # Generate tests for classes
    for cls in module.classes:
        lines.append(f"class Test{cls.name}:")
        if cls.docstring:
            lines.append(f'    """Tests for {cls.name} class."""')
        else:
            lines.append(f'    """Tests for {cls.name}."""')
        lines.append("")

        if cls.methods:
            for method in cls.methods:
                test_code = generate_test_function(
                    method, module.name, include_hypothesis, style="class"
                )
                lines.append(test_code)
        else:
            lines.append("    def test_instantiation(self):")
            lines.append(f'        """Test {cls.name} can be instantiated."""')
            lines.append(f"        obj = {cls.name}()  # TODO: Add required arguments")
            lines.append(f"        assert isinstance(obj, {cls.name})")
            lines.append("")

    return "\n".join(lines)


def process_path(
    source_path: Path,
    output_path: Path | None,
    include_hypothesis: bool,
    style: str,
    dry_run: bool,
    verbose: bool,
) -> dict[str, Any]:
    """Process a source file or directory."""
    results: dict[str, Any] = {
        "success": True,
        "files_processed": 0,
        "files_generated": 0,
        "errors": [],
    }

    if source_path.is_file():
        files = [source_path]
    else:
        files = list(source_path.rglob("*.py"))
        # Exclude test files and __pycache__
        files = [
            f
            for f in files
            if not f.name.startswith("test_")
            and "__pycache__" not in str(f)
            and not f.name.startswith("_")
        ]

    for source_file in files:
        results["files_processed"] += 1

        try:
            module = parse_module(source_file)

            # Skip if no functions or classes
            if not module.functions and not module.classes:
                if verbose:
                    console.print(
                        f"[dim]Skipping {source_file}: no public funcs/classes[/dim]"
                    )
                continue

            # Generate test content
            test_content = generate_test_file(module, include_hypothesis, style)

            # Determine output path
            if output_path:
                if output_path.is_dir():
                    test_file = output_path / f"test_{source_file.name}"
                else:
                    test_file = output_path
            else:
                # Put test file next to source
                test_file = source_file.parent / f"test_{source_file.name}"

            if dry_run:
                console.print(f"\n[bold blue]Would create:[/bold blue] {test_file}")
                console.print(
                    Syntax(test_content, "python", theme="monokai", line_numbers=True)
                )
            else:
                test_file.parent.mkdir(parents=True, exist_ok=True)
                test_file.write_text(test_content, encoding="utf-8")
                console.print(f"[green]Created:[/green] {test_file}")

            results["files_generated"] += 1

        except Exception as e:
            results["errors"].append({"file": str(source_file), "error": str(e)})
            results["success"] = False
            console.print(
                f"[red]Error processing {source_file}:[/red] {e}", file=sys.stderr
            )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "path", type=Path, help="Source file or directory to generate tests for"
    )
    parser.add_argument(
        "--output", "-o", type=Path, help="Output directory for test files"
    )
    parser.add_argument(
        "--style",
        choices=["function", "class"],
        default="class",
        help="Test style: function-based or class-based (default: class)",
    )
    parser.add_argument(
        "--hypothesis",
        action="store_true",
        default=True,
        help="Include Hypothesis property-based tests (default: True)",
    )
    parser.add_argument(
        "--no-hypothesis",
        action="store_false",
        dest="hypothesis",
        help="Exclude Hypothesis tests",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without creating files"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format for results",
    )

    args = parser.parse_args()

    if not args.path.exists():
        console.print(
            f"[red]Error:[/red] Path '{args.path}' does not exist", file=sys.stderr
        )
        return 1

    results = process_path(
        source_path=args.path,
        output_path=args.output,
        include_hypothesis=args.hypothesis,
        style=args.style,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if args.output_format == "json":
        print(json.dumps(results, indent=2))
    else:
        # Summary table
        table = Table(title="Test Generation Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Files Processed", str(results["files_processed"]))
        table.add_row("Tests Generated", str(results["files_generated"]))
        table.add_row("Errors", str(len(results["errors"])))
        console.print(table)

    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
