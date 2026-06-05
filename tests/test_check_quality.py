import json
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


def create_chapter_fixture(tmp_path, include_output=True):
    soln_dir = tmp_path / "soln"
    source_dir = tmp_path / "pretext" / "source"
    soln_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": ["hello\n"],
                    }
                ],
                "source": ["print('hello')\n"],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (soln_dir / "chap01.ipynb").write_text(json.dumps(notebook))

    ptx_lines = [
        "<chapter>",
        "  <program language=\"python\">",
        "    <input>print('hello')</input>",
        "  </program>",
    ]
    if include_output:
        # PTX renders the notebook output as plain text immediately after the code.
        ptx_lines.append("  hello")
    ptx_lines.append("</chapter>")
    (source_dir / "ch01-probability.ptx").write_text("\n".join(ptx_lines) + "\n")

    return tmp_path


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
    assert "Missing frontmatter reference categories" in issues[0]


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
              and the source is hosted on
              <url href="https://github.com/AllenDowney/ThinkBayes2" visual="github.com/AllenDowney/ThinkBayes2">GitHub</url>.
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


def test_frontmatter_reference_boilerplate_reports_missing_shared_refs(tmp_path):
    source_dir = tmp_path / "pretext" / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "meta_frontmatter.ptx").write_text(
        """
        <frontmatter>
          <colophon>
            <website>
              <name>Think Bayes 2</name>
              <address>https://allendowney.github.io/ThinkBayes2</address>
            </website>
            <copyright>
              <shortlicense>
                <url href="https://creativecommons.org/licenses/by-nc-sa/4.0/" visual="creativecommons.org/licenses/by-nc-sa/4.0"> CreativeCommons.org</url>
              </shortlicense>
            </copyright>
          </colophon>
          <preface>
            <p>
              This PreTeXt edition is maintained at
              <url href="https://github.com/PreTeXtBooks/ThinkBayes2" visual="github.com/PreTeXtBooks/ThinkBayes2">github.com/PreTeXtBooks/ThinkBayes2</url>.
              If you find errors or issues specific to this PreTeXt version, please open an issue there.
            </p>
          </preface>
        </frontmatter>
        """
    )

    issues = check_quality.check_frontmatter_reference_boilerplate(tmp_path)

    assert issues
    assert "shared frontmatter references" in issues[0]
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


def test_chapter_footnotes_pass_on_repo():
    repo_root = Path(__file__).resolve().parents[1]
    assert check_quality.check_chapter_footnotes(repo_root) == []


def test_chapter_footnotes_reports_missing_footnotes(tmp_path):
    source_dir = tmp_path / "pretext" / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "ch02-bayes-theorem.ptx").write_text("<chapter><p>Missing footnote</p></chapter>")
    (source_dir / "ch20-abc.ptx").write_text("<chapter><p>Missing footnote</p></chapter>")

    issues = check_quality.check_chapter_footnotes(tmp_path)

    assert issues
    assert "Missing footnotes" in issues[0]


def test_chapter_footnotes_reports_missing_files(tmp_path):
    source_dir = tmp_path / "pretext" / "source"
    source_dir.mkdir(parents=True)

    issues = check_quality.check_chapter_footnotes(tmp_path)

    assert issues
    assert "Chapter file not found" in issues[0]


def test_chapter_output_blocks_matches_simple_output(tmp_path):
    create_chapter_fixture(tmp_path)
    assert check_quality.check_chapter_output_blocks(tmp_path, "chap01", "ch01-probability") == []


def test_chapter_output_blocks_reports_missing_output(tmp_path):
    create_chapter_fixture(tmp_path, include_output=False)
    issues = check_quality.check_chapter_output_blocks(tmp_path, "chap01", "ch01-probability")

    assert issues
    assert "Missing output" in issues[0]


def test_chapter_image_assets_pass_on_repo():
    repo_root = Path(__file__).resolve().parents[1]
    assert check_quality.check_chapter_image_assets(repo_root) == []


def test_chapter_image_assets_reports_unreferenced_supported_formats(tmp_path):
    asset_dir = tmp_path / "pretext" / "assets" / "images"
    asset_dir.mkdir(parents=True)
    for filename in [
        "ch01_probability_a1b2c3d4.png",
        "ch01_probability_e5f6a7b8.jpeg",
        "ch01_probability_1a2b3c4d.svg",
    ]:
        (asset_dir / filename).write_text("dummy")

    issues = check_quality.check_chapter_image_assets(tmp_path)

    assert len(issues) == 3
    assert "ch01_probability_a1b2c3d4.png" in issues[0]
    assert any("ch01_probability_e5f6a7b8.jpeg" in issue for issue in issues)
    assert any("ch01_probability_1a2b3c4d.svg" in issue for issue in issues)


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
