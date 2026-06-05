"""Quality control check: verify that Python code and simple text outputs in
PreTeXt files match the corresponding Jupyter notebooks (solution versions)
for all chapters.

Usage:
    python pretext/check_quality.py

Exits with code 0 if all checks pass, non-zero if differences are found.
"""

import html
import json
import re
import sys
import textwrap
from pathlib import Path

# Code cell prefixes that are notebook-specific setup boilerplate and are
# intentionally omitted from the PreTeXt version.
NOTEBOOK_BOILERPLATE_PREFIXES = (
    "# install empiricaldist if necessary",
    "# Get utils.py",
    "from utils import set_pyplot_params",
)

IGNORED_OUTPUT_PREFIXES = (
    "<Figure size",
    "Output()",
    "Sampling ",
    "<IPython.core.display.HTML object>",
)

# Code that appears in exercise statement blocks as a student placeholder.
# These are not content to be compared.
EXERCISE_PLACEHOLDER = "# Solution goes here"

# Mapping from solution notebook basename to PreTeXt chapter file
CHAPTER_MAP = {
    "chap01": "ch01-probability",
    "chap02": "ch02-bayes-theorem",
    "chap03": "ch03-distributions",
    "chap04": "ch04-estimating-proportions",
    "chap05": "ch05-estimating-counts",
    "chap06": "ch06-odds-addends",
    "chap07": "ch07-min-max-mixture",
    "chap08": "ch08-poisson-processes",
    "chap09": "ch09-decision-analysis",
    "chap10": "ch10-testing",
    "chap11": "ch11-comparison",
    "chap12": "ch12-classification",
    "chap13": "ch13-inference",
    "chap14": "ch14-survival-analysis",
    "chap15": "ch15-mark-recapture",
    "chap16": "ch16-logistic-regression",
    "chap17": "ch17-regression",
    "chap18": "ch18-conjugate-priors",
    "chap19": "ch19-mcmc",
    "chap20": "ch20-abc",
}

CHAPTER_REFERENCE_BOILERPLATE_MARKERS = {
    "copyright/license boilerplate": (
        "Think Bayes, Second Edition",
        "Copyright 2020 Allen B. Downey",
        "creativecommons.org/licenses/by-nc-sa/4.0",
    ),
    "shared frontmatter references": (
        'This is a <url href="https://pretextbook.org" visual="pretextbook.org">PreTeXt</url> adaptation of',
        "The original book and its Jupyter notebooks are freely available at",
        '<url href="https://allendowney.github.io/ThinkBayes2" visual="allendowney.github.io/ThinkBayes2">',
        '<url href="https://github.com/AllenDowney" visual="github.com/AllenDowney">Allen B. Downey</url>.',
        "All credit for the content of this book belongs to Allen B. Downey.",
        "This PreTeXt edition is maintained at",
        '<url href="https://github.com/PreTeXtBooks/ThinkBayes2" visual="github.com/PreTeXtBooks/ThinkBayes2">',
        "If you find errors or issues specific to this PreTeXt version, please open an issue there.",
    ),
}

# ThinkBayes2-specific frontmatter references that should remain in the book.
FRONTMATTER_REFERENCE_MARKERS = (
    'This is a <url href="https://pretextbook.org" visual="pretextbook.org">PreTeXt</url> adaptation of',
    "The original book and its Jupyter notebooks are freely available at",
    '<url href="https://allendowney.github.io/ThinkBayes2" visual="allendowney.github.io/ThinkBayes2">',
    '<url href="https://github.com/AllenDowney" visual="github.com/AllenDowney">Allen B. Downey</url>.',
    "All credit for the content of this book belongs to Allen B. Downey.",
    "This PreTeXt edition is maintained at",
    '<url href="https://github.com/PreTeXtBooks/ThinkBayes2" visual="github.com/PreTeXtBooks/ThinkBayes2">',
    "If you find errors or issues specific to this PreTeXt version, please open an issue there.",
)


def normalize_qc_text(text):
    """Collapse whitespace so XML-formatted prose can be matched robustly."""
    return re.sub(r"\s+", " ", text).strip()


def get_notebook_code_cells(path):
    """Extract Python code cells from a Jupyter notebook."""
    with open(path) as f:
        nb = json.load(f)
    return ["".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"] == "code"]


def get_ptx_code_blocks(path):
    """Extract Python code blocks from a PreTeXt file (content of <input> tags
    inside <program language="python"> blocks)."""
    with open(path) as f:
        content = f.read()
    # Match <input>...</input> inside <program language="python">
    blocks = []
    for m in re.finditer(
        r'<program[^>]*language=["\']python["\'][^>]*>.*?<input>(.*?)</input>.*?</program>',
        content,
        re.DOTALL,
    ):
        blocks.append(m.group(1))
    return blocks


def normalize_ptx_code(code):
    """Normalize a PTX code block for comparison:
    - dedent (PTX files use consistent indentation)
    - unescape HTML entities (applied twice to handle double-encoded entities
      such as &amp;quot; -> &quot; -> ")
    - strip trailing whitespace from each line
    """
    code = textwrap.dedent(code).strip()
    code = html.unescape(html.unescape(code))
    lines = [line.rstrip() for line in code.split("\n")]
    return "\n".join(lines)


def normalize_nb_code(code):
    """Normalize a notebook code cell for comparison:
    - strip trailing whitespace from each line
    - strip the '# Solution' marker that precedes solution code
    """
    lines = [line.rstrip() for line in code.split("\n")]
    result = "\n".join(lines).strip()
    # Solution cells in soln/ notebooks start with '# Solution' on the first line
    # (followed by either a blank line or more comments/code)
    if result.startswith("# Solution\n"):
        result = result[len("# Solution\n"):].lstrip("\n")
    return result


def normalize_output(text):
    """Normalize notebook or PTX output text for comparison."""
    text = textwrap.dedent(text).strip()
    text = html.unescape(text)
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def strip_leading_comments(code):
    """Return the code with any leading comment block removed.

    Some notebook cells start with a comment that describes what the code does,
    followed by the actual code.  The PreTeXt version often omits this comment
    because the explanation appears in the surrounding prose.  This helper
    produces a comment-stripped variant used as a fallback in comparisons.
    """
    lines = code.split("\n")
    first_code = next(
        (i for i, l in enumerate(lines) if l.strip() and not l.startswith("#")),
        None,
    )
    if first_code and first_code > 0 and lines[0].startswith("#"):
        return "\n".join(lines[first_code:]).strip()
    return code


def get_notebook_cells(path):
    """Extract normalized notebook code cells and comparable simple outputs."""
    with open(path) as f:
        nb = json.load(f)

    cells = []
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue

        code = normalize_nb_code("".join(cell["source"]))
        if any(code.startswith(prefix) for prefix in NOTEBOOK_BOILERPLATE_PREFIXES):
            continue

        outputs = []
        for output in cell.get("outputs", []):
            if output.get("output_type") == "stream":
                text = "".join(output.get("text", []))
            elif output.get("output_type") in ("execute_result", "display_data"):
                text = "".join(output.get("data", {}).get("text/plain", []))
            else:
                continue

            text = normalize_output(text)
            if (
                text
                and "\n" not in text
                and not any(text.startswith(prefix) for prefix in IGNORED_OUTPUT_PREFIXES)
            ):
                outputs.append(text)

        cells.append(
            {
                "code": code,
                "code_stripped": strip_leading_comments(code),
                "outputs": outputs,
            }
        )

    return cells


def get_ptx_programs(path):
    """Extract normalized PTX programs with source spans."""
    with open(path) as f:
        content = f.read()

    programs = []
    for m in re.finditer(
        r'<program[^>]*language=["\']python["\'][^>]*>.*?<input>(.*?)</input>.*?</program>',
        content,
        re.DOTALL,
    ):
        code = normalize_ptx_code(m.group(1))
        if (
            not code
            or code == EXERCISE_PLACEHOLDER
            or any(code.startswith(prefix) for prefix in NOTEBOOK_BOILERPLATE_PREFIXES)
        ):
            continue

        programs.append(
            {
                "code": code,
                "code_stripped": strip_leading_comments(code),
                "start": m.start(),
                "end": m.end(),
            }
        )

    return content, programs


def codes_match(nb_cell, ptx_program):
    """Whether a notebook cell and PTX program contain the same code."""
    return (
        nb_cell["code"] == ptx_program["code"]
        or nb_cell["code_stripped"] == ptx_program["code"]
        or nb_cell["code"] == ptx_program["code_stripped"]
        or nb_cell["code_stripped"] == ptx_program["code_stripped"]
    )


def check_chapter(repo_root, nb_name, ptx_name):
    """Compare Python code between a notebook and its PreTeXt counterpart.

    Returns a list of issue strings (empty list means no issues).
    """
    nb_path = repo_root / "soln" / f"{nb_name}.ipynb"
    ptx_path = repo_root / "pretext" / "source" / f"{ptx_name}.ptx"

    issues = []

    if not nb_path.exists():
        issues.append(f"  Notebook not found: {nb_path}")
        return issues
    if not ptx_path.exists():
        issues.append(f"  PreTeXt file not found: {ptx_path}")
        return issues

    nb_cells = get_notebook_code_cells(nb_path)
    ptx_blocks = get_ptx_code_blocks(ptx_path)

    # Exclude notebook-specific boilerplate setup cells from comparison on both sides.
    # Also exclude empty PTX blocks (unfilled solution placeholders) and student
    # exercise placeholders.
    nb_cells = [
        c for c in nb_cells
        if not any(c.strip().startswith(prefix) for prefix in NOTEBOOK_BOILERPLATE_PREFIXES)
    ]
    ptx_blocks = [
        b for b in ptx_blocks
        if normalize_ptx_code(b)  # exclude empty blocks
        and normalize_ptx_code(b) != EXERCISE_PLACEHOLDER  # exclude student placeholders
        and not any(normalize_ptx_code(b).startswith(prefix) for prefix in NOTEBOOK_BOILERPLATE_PREFIXES)
    ]

    nb_normalized = [normalize_nb_code(c) for c in nb_cells]
    ptx_normalized = [normalize_ptx_code(b) for b in ptx_blocks]

    nb_set = set(nb_normalized)
    ptx_set = set(ptx_normalized)

    # Build a set of comment-stripped PTX blocks for lenient comparison
    ptx_stripped_set = {strip_leading_comments(b) for b in ptx_set} | ptx_set

    # A notebook block is considered present in PTX if:
    # 1. exact match, or
    # 2. the comment-stripped notebook block matches a PTX block (exact or stripped)
    def in_ptx(nb_block):
        if nb_block in ptx_set:
            return True
        stripped_nb = strip_leading_comments(nb_block)
        return stripped_nb in ptx_stripped_set

    missing_from_ptx = {b for b in nb_set if not in_ptx(b)}

    # Extra PTX blocks: blocks in PTX whose code (comment-stripped) is not
    # covered by any notebook block (exact or comment-stripped)
    nb_stripped_set = {strip_leading_comments(b) for b in nb_set} | nb_set
    extra_in_ptx = {b for b in ptx_set if b not in nb_stripped_set
                    and strip_leading_comments(b) not in nb_stripped_set}

    if missing_from_ptx:
        issues.append(
            f"  {len(missing_from_ptx)} code block(s) from notebook not found in PreTeXt:"
        )
        for block in sorted(missing_from_ptx):
            preview = block.replace("\n", "\\n")[:80]
            issues.append(f"    - {repr(preview)}")

    if extra_in_ptx:
        issues.append(
            f"  {len(extra_in_ptx)} code block(s) in PreTeXt not found in notebook:"
        )
        for block in sorted(extra_in_ptx):
            preview = block.replace("\n", "\\n")[:80]
            issues.append(f"    + {repr(preview)}")

    return issues


def check_chapter_output_blocks(repo_root, nb_name, ptx_name):
    """Verify comparable simple notebook outputs are present near matching PTX code."""
    nb_path = repo_root / "soln" / f"{nb_name}.ipynb"
    ptx_path = repo_root / "pretext" / "source" / f"{ptx_name}.ptx"

    issues = []

    if not nb_path.exists():
        issues.append(f"  Notebook not found: {nb_path}")
        return issues
    if not ptx_path.exists():
        issues.append(f"  PreTeXt file not found: {ptx_path}")
        return issues

    nb_cells = get_notebook_cells(nb_path)
    content, programs = get_ptx_programs(ptx_path)

    program_index = 0
    for cell in nb_cells:
        matched_program = None
        matched_program_index = None

        while program_index < len(programs):
            candidate = programs[program_index]
            program_index += 1
            if codes_match(cell, candidate):
                matched_program = candidate
                matched_program_index = program_index - 1
                break

        if not matched_program or not cell["outputs"]:
            continue

        next_start = (
            programs[matched_program_index + 1]["start"]
            if matched_program_index + 1 < len(programs)
            else len(content)
        )
        local_chunk = normalize_output(content[matched_program["end"]:next_start])

        for output in cell["outputs"]:
            if output not in local_chunk:
                preview = cell["code"].split("\n", 1)[0]
                issues.append(
                    f"  Missing output for {preview!r} in {ptx_path.name}: {output!r}"
                )

    return issues


def check_chapter_reference_boilerplate(repo_root):
    """Verify chapter PTX files do not include duplicated shared boilerplate."""
    source_dir = repo_root / "pretext" / "source"
    issues = []

    for path in sorted(source_dir.glob("ch*.ptx")):
        content = path.read_text()
        matches = [
            description
            for description, markers in CHAPTER_REFERENCE_BOILERPLATE_MARKERS.items()
            if any(marker in content for marker in markers)
        ]
        if matches:
            issues.append(
                f"  Duplicated chapter boilerplate found in {path.name}: "
                f"{', '.join(matches)}"
            )

    return issues


def check_frontmatter_reference_boilerplate(repo_root):
    """Verify the shared frontmatter keeps the canonical book URLs and references."""
    path = repo_root / "pretext" / "source" / "meta_frontmatter.ptx"
    content = normalize_qc_text(path.read_text())
    issues = []

    missing = [
        marker for marker in FRONTMATTER_REFERENCE_MARKERS
        if normalize_qc_text(marker) not in content
    ]
    if missing:
        issues.append(
            f"  Missing frontmatter references in {path.name}: "
            f"{', '.join(repr(m) for m in missing)}"
        )

    return issues


def check_chapter_image_assets(repo_root):
    """Verify chapter image assets and PTX references stay in sync."""
    source_dir = repo_root / "pretext" / "source"
    asset_dir = repo_root / "pretext" / "assets" / "images"

    chapter_asset_names = {
        path.name
        for path in asset_dir.glob("*.png")
        if re.fullmatch(r"ch\d+_[a-z_]+_[0-9a-f]+\.png", path.name)
    }
    referenced_asset_names = set()
    issues = []

    for path in sorted(source_dir.glob("ch*.ptx")):
        content = path.read_text()
        references = re.findall(
            r"""<image[^>]*?source=['"]([^'"]+)['"]""",
            content,
            re.DOTALL,
        )
        for reference in references:
            if not reference.startswith("images/"):
                continue

            asset_name = Path(reference).name
            if not asset_name.startswith("ch"):
                continue

            referenced_asset_names.add(asset_name)
            if not (asset_dir / asset_name).exists():
                issues.append(
                    f"  Missing chapter image asset referenced in {path.name}: {asset_name}"
                )

    unreferenced_assets = sorted(chapter_asset_names - referenced_asset_names)
    for asset_name in unreferenced_assets:
        issues.append(f"  Unreferenced chapter image asset: {asset_name}")

    return issues


def main():
    repo_root = Path(__file__).parent.parent

    all_passed = True
    for nb_name, ptx_name in CHAPTER_MAP.items():
        issues = check_chapter(repo_root, nb_name, ptx_name)
        if issues:
            all_passed = False
            print(f"FAIL: {nb_name} <-> {ptx_name}")
            for issue in issues:
                print(issue)
            print()
        else:
            print(f"PASS: {nb_name} <-> {ptx_name}")

    chapter_issues = check_chapter_reference_boilerplate(repo_root)
    if chapter_issues:
        all_passed = False
        print("FAIL: chapter reference boilerplate")
        for issue in chapter_issues:
            print(issue)
        print()
    else:
        print("PASS: chapter reference boilerplate")

    frontmatter_issues = check_frontmatter_reference_boilerplate(repo_root)
    if frontmatter_issues:
        all_passed = False
        print("FAIL: frontmatter reference boilerplate")
        for issue in frontmatter_issues:
            print(issue)
        print()
    else:
        print("PASS: frontmatter reference boilerplate")

    image_issues = check_chapter_image_assets(repo_root)
    if image_issues:
        all_passed = False
        print("FAIL: chapter image assets")
        for issue in image_issues:
            print(issue)
        print()
    else:
        print("PASS: chapter image assets")

    output_issues = []
    for nb_name, ptx_name in CHAPTER_MAP.items():
        output_issues.extend(check_chapter_output_blocks(repo_root, nb_name, ptx_name))
    if output_issues:
        all_passed = False
        print("FAIL: chapter output blocks")
        for issue in output_issues:
            print(issue)
        print()
    else:
        print("PASS: chapter output blocks")

    if all_passed:
        print("\nAll chapters passed quality control check.")
        return 0
    else:
        print("\nQuality control check FAILED. See differences above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
