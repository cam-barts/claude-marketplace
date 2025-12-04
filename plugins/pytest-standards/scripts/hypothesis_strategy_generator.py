#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""
Generate Hypothesis strategies from Python type annotations.

Features:
- Parse function type hints
- Generate appropriate strategies for each type
- Handle custom types with composite strategies
- Generate example-based tests as starting point
- Support dataclasses and Pydantic models

Usage:
    uv run hypothesis_strategy_generator.py [OPTIONS] SOURCE

Examples
--------
    uv run hypothesis_strategy_generator.py src/module.py
    uv run hypothesis_strategy_generator.py src/module.py --function my_func
    uv run hypothesis_strategy_generator.py src/ --output strategies.py
    uv run hypothesis_strategy_generator.py src/ --include-examples
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

# Mapping of Python types to Hypothesis strategies
TYPE_STRATEGIES: dict[str, str] = {
    # Built-in types
    "int": "st.integers()",
    "float": "st.floats(allow_nan=False)",
    "str": "st.text()",
    "bytes": "st.binary()",
    "bool": "st.booleans()",
    "None": "st.none()",
    "NoneType": "st.none()",
    # Collections
    "list": "st.lists({element})",
    "List": "st.lists({element})",
    "set": "st.sets({element})",
    "Set": "st.sets({element})",
    "frozenset": "st.frozensets({element})",
    "FrozenSet": "st.frozensets({element})",
    "dict": "st.dictionaries({key}, {value})",
    "Dict": "st.dictionaries({key}, {value})",
    "tuple": "st.tuples({elements})",
    "Tuple": "st.tuples({elements})",
    # Optional/Union
    "Optional": "st.none() | {inner}",
    # Common stdlib types
    "datetime": "st.datetimes()",
    "date": "st.dates()",
    "time": "st.times()",
    "timedelta": "st.timedeltas()",
    "Decimal": "st.decimals(allow_nan=False)",
    "UUID": "st.uuids()",
    "Path": "st.text().map(Path)",
    # Any type
    "Any": "st.from_type(object)",
}


@dataclass
class FunctionSignature:
    """A function signature with type hints."""

    name: str
    file_path: Path
    line_number: int
    params: dict[str, str] = field(default_factory=dict)  # param_name -> type_hint
    return_type: str | None = None
    is_async: bool = False
    docstring: str | None = None


@dataclass
class GeneratedStrategy:
    """A generated Hypothesis strategy."""

    function_name: str
    param_name: str
    type_hint: str
    strategy: str


@dataclass
class GeneratedTest:
    """A generated test function."""

    function_name: str
    test_code: str
    strategies: list[GeneratedStrategy]


def parse_type_annotation(annotation: ast.expr) -> str:
    """Parse an AST type annotation to a string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Constant):
        if annotation.value is None:
            return "None"
        return str(annotation.value)
    if isinstance(annotation, ast.Subscript):
        # Handle generics like List[int], Dict[str, int]
        base = parse_type_annotation(annotation.value)
        if isinstance(annotation.slice, ast.Tuple):
            args = ", ".join(
                parse_type_annotation(elt) for elt in annotation.slice.elts
            )
            return f"{base}[{args}]"
        arg = parse_type_annotation(annotation.slice)
        return f"{base}[{arg}]"
    if isinstance(annotation, ast.Attribute):
        # Handle module.Type
        return f"{parse_type_annotation(annotation.value)}.{annotation.attr}"
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        # Handle Union types with | operator (Python 3.10+)
        left = parse_type_annotation(annotation.left)
        right = parse_type_annotation(annotation.right)
        return f"Union[{left}, {right}]"
    return ast.unparse(annotation)


def type_to_strategy(type_hint: str, depth: int = 0) -> str:
    """Convert a type hint to a Hypothesis strategy."""
    if depth > 5:
        return "st.nothing()"  # Prevent infinite recursion

    # Clean up the type hint
    type_hint = type_hint.strip()

    # Handle None
    if type_hint in ("None", "NoneType"):
        return "st.none()"

    # Handle basic types
    if type_hint in TYPE_STRATEGIES:
        return TYPE_STRATEGIES[type_hint]

    # Handle Optional[X] -> None | X
    if type_hint.startswith("Optional["):
        inner = type_hint[9:-1]
        inner_strategy = type_to_strategy(inner, depth + 1)
        return f"st.none() | {inner_strategy}"

    # Handle Union[X, Y, ...]
    if type_hint.startswith("Union["):
        inner = type_hint[6:-1]
        types = split_type_args(inner)
        strategies = [type_to_strategy(t, depth + 1) for t in types]
        return " | ".join(strategies)

    # Handle List[X]
    if type_hint.startswith("List[") or type_hint.startswith("list["):
        inner = type_hint[5:-1]
        element_strategy = type_to_strategy(inner, depth + 1)
        return f"st.lists({element_strategy})"

    # Handle Set[X]
    if type_hint.startswith("Set[") or type_hint.startswith("set["):
        inner = type_hint[4:-1]
        element_strategy = type_to_strategy(inner, depth + 1)
        return f"st.sets({element_strategy})"

    # Handle Dict[K, V]
    if type_hint.startswith("Dict[") or type_hint.startswith("dict["):
        inner = type_hint[5:-1]
        types = split_type_args(inner)
        if len(types) == 2:
            key_strategy = type_to_strategy(types[0], depth + 1)
            value_strategy = type_to_strategy(types[1], depth + 1)
            return f"st.dictionaries({key_strategy}, {value_strategy})"

    # Handle Tuple[X, Y, ...]
    if type_hint.startswith("Tuple[") or type_hint.startswith("tuple["):
        inner = type_hint[6:-1]
        types = split_type_args(inner)
        strategies = [type_to_strategy(t, depth + 1) for t in types]
        return f"st.tuples({', '.join(strategies)})"

    # Handle Callable
    if type_hint.startswith("Callable"):
        return "st.functions()"

    # Handle Literal
    if type_hint.startswith("Literal["):
        inner = type_hint[8:-1]
        values = [v.strip() for v in inner.split(",")]
        return f"st.sampled_from([{', '.join(values)}])"

    # Default: try from_type
    return f"st.from_type({type_hint})"


def split_type_args(args_str: str) -> list[str]:
    """Split type arguments respecting nested brackets."""
    result = []
    current = ""
    depth = 0

    for char in args_str:
        if char == "[":
            depth += 1
            current += char
        elif char == "]":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            result.append(current.strip())
            current = ""
        else:
            current += char

    if current.strip():
        result.append(current.strip())

    return result


def extract_functions(
    path: Path, function_filter: str | None = None
) -> list[FunctionSignature]:
    """Extract function signatures from Python files."""
    functions: list[FunctionSignature] = []

    if path.is_file():
        files = [path] if path.suffix == ".py" else []
    else:
        files = list(path.rglob("*.py"))

    for file_path in files:
        # Skip test files, hidden dirs, cache
        if any(
            part.startswith(".") or part == "__pycache__" or part.startswith("test_")
            for part in file_path.parts
        ):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private functions
                    if node.name.startswith("_"):
                        continue

                    # Apply filter if specified
                    if function_filter and node.name != function_filter:
                        continue

                    params: dict[str, str] = {}
                    for arg in node.args.args:
                        if arg.arg in ("self", "cls"):
                            continue
                        if arg.annotation:
                            params[arg.arg] = parse_type_annotation(arg.annotation)
                        else:
                            params[arg.arg] = "Any"

                    return_type = None
                    if node.returns:
                        return_type = parse_type_annotation(node.returns)

                    functions.append(
                        FunctionSignature(
                            name=node.name,
                            file_path=file_path,
                            line_number=node.lineno,
                            params=params,
                            return_type=return_type,
                            is_async=isinstance(node, ast.AsyncFunctionDef),
                            docstring=ast.get_docstring(node),
                        ),
                    )

        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Could not parse {file_path}: {e}",
            )

    return functions


def generate_test(
    func: FunctionSignature, include_examples: bool = False
) -> GeneratedTest:
    """Generate a test function with Hypothesis strategies."""
    strategies: list[GeneratedStrategy] = []

    # Generate strategies for each parameter
    for param_name, type_hint in func.params.items():
        strategy = type_to_strategy(type_hint)
        strategies.append(
            GeneratedStrategy(
                function_name=func.name,
                param_name=param_name,
                type_hint=type_hint,
                strategy=strategy,
            ),
        )

    # Build test function
    lines = []

    # Add given decorator
    if strategies:
        given_args = ", ".join(f"{s.param_name}={s.strategy}" for s in strategies)
        lines.append(f"@given({given_args})")

    # Add example decorator if requested
    if include_examples and strategies:
        example_args = ", ".join(f"{s.param_name}=..." for s in strategies)
        lines.append(f"@example({example_args})  # TODO: Add concrete example")

    # Function definition
    async_prefix = "async " if func.is_async else ""
    param_list = ", ".join(func.params.keys())
    lines.append(f"{async_prefix}def test_{func.name}({param_list}):")

    # Docstring
    lines.append(f'    """Test {func.name} with generated inputs."""')

    # Body
    if func.is_async:
        lines.append(f"    result = await {func.name}({param_list})")
    else:
        lines.append(f"    result = {func.name}({param_list})")

    # Add assertion based on return type
    if func.return_type:
        if func.return_type == "bool":
            lines.append("    assert isinstance(result, bool)")
        elif func.return_type in ("int", "float", "str", "bytes"):
            lines.append(f"    assert isinstance(result, {func.return_type})")
        elif func.return_type.startswith("List") or func.return_type.startswith("list"):
            lines.append("    assert isinstance(result, list)")
        elif func.return_type.startswith("Dict") or func.return_type.startswith("dict"):
            lines.append("    assert isinstance(result, dict)")
        elif func.return_type == "None":
            lines.append("    assert result is None")
        else:
            lines.append("    # TODO: Add appropriate assertions")
            lines.append("    assert result is not None")
    else:
        lines.append("    # TODO: Add appropriate assertions")

    test_code = "\n".join(lines)
    return GeneratedTest(
        function_name=func.name,
        test_code=test_code,
        strategies=strategies,
    )


def generate_strategies_file(
    functions: list[FunctionSignature],
    include_examples: bool = False,
) -> str:
    """Generate a complete test file with strategies."""
    lines = [
        '"""Generated Hypothesis tests."""',
        "",
        "from hypothesis import given, example, strategies as st",
        "",
        "# Import your functions here:",
        "# from your_module import func1, func2",
        "",
        "",
    ]

    for func in functions:
        test = generate_test(func, include_examples)
        lines.append(test.test_code)
        lines.append("")
        lines.append("")

    return "\n".join(lines)


def print_report(
    functions: list[FunctionSignature],
    verbose: bool = False,  # noqa: ARG001
) -> None:
    """Print the generation report."""
    console.print(Panel("[bold]Hypothesis Strategy Generator[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    summary_table.add_row("Functions Found", str(len(functions)))
    total_params = sum(len(f.params) for f in functions)
    summary_table.add_row("Total Parameters", str(total_params))

    console.print(summary_table)

    # Functions
    if functions:
        console.print("\n[bold]Generated Strategies[/bold]")
        for func in functions[:10]:
            console.print(
                f"\n[cyan]{func.name}[/cyan] ({func.file_path.name}:{func.line_number})"
            )
            for param_name, type_hint in func.params.items():
                strategy = type_to_strategy(type_hint)
                console.print(f"  {param_name}: {type_hint}")
                console.print(f"    → [green]{strategy}[/green]")

        if len(functions) > 10:
            console.print(f"\n... and {len(functions) - 10} more functions")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="Source file or directory")
    parser.add_argument(
        "--function",
        "-f",
        type=str,
        help="Specific function to generate for",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file for generated tests",
    )
    parser.add_argument(
        "--include-examples",
        action="store_true",
        help="Include @example decorators",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--format",
        choices=["text", "json", "code"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.source.exists():
        console.print(
            f"[red]Error:[/red] Source '{args.source}' does not exist",
            file=sys.stderr,
        )
        return 1

    # Extract functions
    functions = extract_functions(args.source, args.function)

    if not functions:
        console.print("[yellow]No functions with type annotations found[/yellow]")
        return 0

    # Generate output
    if args.output:
        code = generate_strategies_file(functions, args.include_examples)
        args.output.write_text(code, encoding="utf-8")
        console.print(f"[green]Generated tests written to {args.output}[/green]")
        return 0

    if args.format == "json":
        result: dict[str, Any] = {
            "functions": [
                {
                    "name": f.name,
                    "file": str(f.file_path),
                    "line": f.line_number,
                    "params": {
                        name: {
                            "type": hint,
                            "strategy": type_to_strategy(hint),
                        }
                        for name, hint in f.params.items()
                    },
                    "return_type": f.return_type,
                    "is_async": f.is_async,
                }
                for f in functions
            ],
        }
        print(json.dumps(result, indent=2))
    elif args.format == "code":
        code = generate_strategies_file(functions, args.include_examples)
        console.print(Syntax(code, "python", line_numbers=True))
    else:
        print_report(functions, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
