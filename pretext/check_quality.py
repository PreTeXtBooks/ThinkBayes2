"""Quality control check: verify that Python code in PreTeXt files matches
the corresponding Jupyter notebooks (solution versions) for all chapters.

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

    if all_passed:
        print("\nAll chapters passed quality control check.")
        return 0
    else:
        print("\nQuality control check FAILED. See differences above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
