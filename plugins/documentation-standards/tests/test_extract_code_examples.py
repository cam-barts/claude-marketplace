"""Tests for extract_code_examples.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestCodeBlockExtraction:
    """Tests for extracting code blocks from markdown."""

    def test_extract_python_blocks(self, tmp_path: Path) -> None:
        """Test extracting Python code blocks."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
# Example

Here is some Python code:

```python
def hello():
    print("Hello, world!")

hello()
```

And another block:

```python
x = 1 + 2
print(x)
```
""")

        from extract_code_examples import extract_code_blocks

        blocks = extract_code_blocks(md_file)
        python_blocks = [b for b in blocks if b.language == "python"]

        assert len(python_blocks) == 2
        assert "def hello" in python_blocks[0].code
        assert "x = 1 + 2" in python_blocks[1].code

    def test_extract_multiple_languages(self, tmp_path: Path) -> None:
        """Test extracting blocks from multiple languages."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
# Multi-language Example

Python:
```python
print("Python")
```

JavaScript:
```javascript
console.log("JavaScript");
```

Bash:
```bash
echo "Bash"
```
""")

        from extract_code_examples import extract_code_blocks

        blocks = extract_code_blocks(md_file)
        languages = {b.language for b in blocks}

        assert "python" in languages
        assert "javascript" in languages
        assert "bash" in languages


class TestCodeValidation:
    """Tests for validating extracted code."""

    def test_validate_python_syntax(self, tmp_path: Path) -> None:
        """Test validating Python syntax."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
Valid code:
```python
def valid():
    return True
```

Invalid code:
```python
def invalid(
    # missing closing paren
```
""")

        from extract_code_examples import validate_code_blocks

        report = validate_code_blocks(md_file)
        assert len(report.valid_blocks) >= 1
        assert len(report.invalid_blocks) >= 1

    def test_skip_output_blocks(self, tmp_path: Path) -> None:
        """Test skipping output/console blocks."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
Code:
```python
print("hello")
```

Output:
```
hello
```
""")

        from extract_code_examples import extract_code_blocks

        blocks = extract_code_blocks(md_file, skip_output=True)
        # Should only have the python block, not the output
        assert len(blocks) == 1


class TestCodeExecution:
    """Tests for executing code examples."""

    def test_run_python_example(self, tmp_path: Path) -> None:
        """Test running a Python code example."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
```python
result = 1 + 1
print(result)
```
""")

        from extract_code_examples import extract_code_blocks, run_code_block

        blocks = extract_code_blocks(md_file)
        result = run_code_block(blocks[0])

        assert result.success
        assert "2" in result.output

    def test_detect_failing_example(self, tmp_path: Path) -> None:
        """Test detecting a failing code example."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
```python
raise ValueError("This should fail")
```
""")

        from extract_code_examples import extract_code_blocks, run_code_block

        blocks = extract_code_blocks(md_file)
        result = run_code_block(blocks[0])

        assert not result.success
        assert "ValueError" in result.error


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from extract_code_examples import main

        old_argv = sys.argv
        try:
            sys.argv = ["extract_code_examples.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
