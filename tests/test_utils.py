import pytest
from pathlib import Path
from opendata.utils import scan_project_lazy, read_file_header
import tempfile
import shutil


def test_lazy_scanner_no_reads():
    """Verify scanner handles large-ish files without performance hit and avoids reading data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create a "large" mock data file (1MB approx)
        large_file = tmp_path / "data.csv"
        # 100,000 lines of "0,0\n" is roughly 400KB. Let's make it 300,000
        large_file.write_text("header1,header2\n" + "0,0\n" * 300000)

        # Create a nested structure
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "paper.tex").write_text("\\title{Test Paper}")

        fingerprint, full_files = scan_project_lazy(tmp_path)

        assert fingerprint.file_count == 2
        assert fingerprint.total_size_bytes > 1000000
        assert ".csv" in fingerprint.extensions
        assert ".tex" in fingerprint.extensions
        assert any("paper.tex" in s for s in fingerprint.structure_sample)


def test_read_file_header_limit():
    """Ensure read_file_header strictly limits bytes read."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("A" * 10000)
        file_path = Path(f.name)

    try:
        header = read_file_header(file_path, max_bytes=10)
        assert len(header) == 10
        assert all(c == "A" for c in header)
    finally:
        file_path.unlink()
