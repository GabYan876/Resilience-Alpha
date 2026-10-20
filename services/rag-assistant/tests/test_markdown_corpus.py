import sys

import pytest

from app.adapters.markdown_corpus import MarkdownCorpus


def test_reads_markdown_only_with_relative_sorted_sources(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "b.md").write_text("beta", encoding="utf-8")
    (tmp_path / "a.md").write_text("alpha", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignoré", encoding="utf-8")
    (tmp_path / "vide.md").write_text("  \n", encoding="utf-8")

    documents = MarkdownCorpus(tmp_path).read_all()

    assert [(d.source, d.text) for d in documents] == [("a.md", "alpha"), ("docs/b.md", "beta")]


@pytest.mark.skipif(sys.platform == "win32", reason="lien symbolique interdit sous Windows")
def test_symlink_leaving_the_corpus_is_ignored(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("hors corpus", encoding="utf-8")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "ok.md").write_text("dedans", encoding="utf-8")
    (corpus / "lien.md").symlink_to(outside / "secret.md")

    assert [d.source for d in MarkdownCorpus(corpus).read_all()] == ["ok.md"]


def test_oversized_file_is_skipped(tmp_path):
    (tmp_path / "gros.md").write_text("x" * 20, encoding="utf-8")
    (tmp_path / "petit.md").write_text("x", encoding="utf-8")

    assert [d.source for d in MarkdownCorpus(tmp_path, max_bytes=10).read_all()] == ["petit.md"]


def test_missing_root_gives_empty_corpus(tmp_path):
    assert MarkdownCorpus(tmp_path / "absent").read_all() == []
