from pathlib import Path

from app.adapters.file_blocklist import BlocklistFile, IpBlocklist, SubjectBlocklist


def make(tmp_path: Path) -> tuple[Path, IpBlocklist, SubjectBlocklist]:
    path = tmp_path / "blocked.txt"
    file = BlocklistFile(str(path))
    return path, IpBlocklist(file), SubjectBlocklist(file)


def test_block_writes_prefixed_entries(tmp_path):
    path, ips, subjects = make(tmp_path)
    ips.block("192.168.137.50")
    subjects.block("abc-123")
    assert path.read_text().splitlines() == ["ip:192.168.137.50", "sub:abc-123"]


def test_block_is_idempotent(tmp_path):
    path, ips, _ = make(tmp_path)
    ips.block("10.0.0.1")
    ips.block("10.0.0.1")
    assert path.read_text().splitlines() == ["ip:10.0.0.1"]


def test_unblock_removes_only_that_entry(tmp_path):
    path, ips, subjects = make(tmp_path)
    ips.block("10.0.0.1")
    subjects.block("abc")
    ips.unblock("10.0.0.1")
    assert path.read_text().splitlines() == ["sub:abc"]


def test_unblock_without_file_is_harmless(tmp_path):
    _, ips, _ = make(tmp_path)
    ips.unblock("10.0.0.1")


def test_no_temporary_file_left_behind(tmp_path):
    path, ips, _ = make(tmp_path)
    ips.block("10.0.0.1")
    assert [p.name for p in tmp_path.iterdir()] == [path.name]
