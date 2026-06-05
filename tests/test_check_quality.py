from pathlib import Path

import pytest

from importlib.util import module_from_spec, spec_from_file_location


# pretext/ is a script directory rather than an importable package, so load the
# module directly from its file path for test coverage.
def load_check_quality():
    path = Path(__file__).resolve().parents[1] / "pretext" / "check_quality.py"
    spec = spec_from_file_location("check_quality", path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


check_quality = load_check_quality()


@pytest.mark.parametrize(
    "text, expected",
    [
        ("  hello\n\tworld  ", "hello world"),
        ("", ""),
        ("   \n\t  ", ""),
        ("already-clean", "already-clean"),
    ],
)
def test_normalize_whitespace_collapses_whitespace(text, expected):
    assert check_quality.normalize_whitespace(text) == expected


def test_frontmatter_reference_boilerplate_passes_on_repo():
    repo_root = Path(__file__).resolve().parents[1]
    assert check_quality.check_frontmatter_reference_boilerplate(repo_root) == []


def test_frontmatter_reference_boilerplate_reports_missing_markers(tmp_path):
    source_dir = tmp_path / "pretext" / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "meta_frontmatter.ptx").write_text("<frontmatter>missing links</frontmatter>")

    issues = check_quality.check_frontmatter_reference_boilerplate(tmp_path)

    assert issues
    assert "Missing frontmatter references" in issues[0]


def test_frontmatter_reference_boilerplate_reports_missing_external_refs(tmp_path):
    source_dir = tmp_path / "pretext" / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "meta_frontmatter.ptx").write_text(
        """
        <frontmatter>
          <preface>
            <p>
              This is a <url href="https://pretextbook.org" visual="pretextbook.org">PreTeXt</url> adaptation of
              <em>Think Bayes 2</em> by
              <url href="https://github.com/AllenDowney" visual="github.com/AllenDowney">Allen B. Downey</url>.
              The original book and its Jupyter notebooks are freely available at
              <url href="https://allendowney.github.io/ThinkBayes2" visual="allendowney.github.io/ThinkBayes2">allendowney.github.io/ThinkBayes2</url>,
              All credit for the content of this book belongs to Allen B. Downey.
            </p>
            <p>
              <website>
                <name>Think Bayes 2</name>
                <address>https://allendowney.github.io/ThinkBayes2</address>
              </website>
            </p>
          </preface>
        </frontmatter>
        """
    )

    issues = check_quality.check_frontmatter_reference_boilerplate(tmp_path)

    assert issues
    assert "frontmatter license reference" in issues[0]
    assert "frontmatter source reference" in issues[0]
    assert "frontmatter website reference" not in issues[0]


def test_chapter_cross_references_pass_on_repo():
    repo_root = Path(__file__).resolve().parents[1]
    assert check_quality.check_chapter_cross_references(repo_root) == []


def test_chapter_cross_references_reports_missing_refs(tmp_path):
    source_dir = tmp_path / "pretext" / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "ch03-distributions.ptx").write_text(
        '<chapter><p>See <xref ref="ch-conjugate-priors"/></p></chapter>'
    )

    issues = check_quality.check_chapter_cross_references(tmp_path)

    assert issues
    assert "Missing chapter cross-references" in issues[0]


def test_chapter_cross_references_reports_missing_files(tmp_path):
    source_dir = tmp_path / "pretext" / "source"
    source_dir.mkdir(parents=True)

    issues = check_quality.check_chapter_cross_references(tmp_path)

    assert issues
    assert "Chapter file not found" in issues[0]


def test_contains_xref_reference_handles_whitespace():
    content = 'before <xref\n  ref="ch-bayes-theorem"\n/> after'
    assert check_quality.contains_xref_reference(content, "ch-bayes-theorem") is True


@pytest.mark.parametrize(
    "content, phrase, expected",
    [
        ("alpha beta", "alpha beta", True),
        ("alpha beta gamma", "beta", True),
        ("alphabet soup", "alpha", False),
    ],
)
def test_contains_normalized_phrase(content, phrase, expected):
    assert check_quality.contains_normalized_phrase(content, phrase) is expected
