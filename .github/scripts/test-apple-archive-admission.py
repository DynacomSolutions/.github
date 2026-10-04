import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW_PATH = Path(__file__).parents[1] / "workflows" / "apple-build.yml"
WORKFLOW = WORKFLOW_PATH.read_text()
MARKER = 'if python3 - "$archive" <<\'PY\'\n'
start = WORKFLOW.index(MARKER) + len(MARKER)
end = WORKFLOW.index("\n          PY\n", start)
ADMISSION_CODE = textwrap.dedent(WORKFLOW[start:end])


class ArchiveAdmissionTests(unittest.TestCase):
    def run_admission(self, archive: Path, code: str = ADMISSION_CODE) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-c", code, str(archive)],
            capture_output=True,
            text=True,
            check=False,
        )

    def make_archive(self, parent: str) -> Path:
        archive = Path(parent) / "Example.xcarchive"
        archive.mkdir()
        (archive / "Info.plist").write_text("plist")
        (archive / "Products").mkdir()
        (archive / "Products" / "app").write_bytes(b"app")
        return archive

    def test_valid_archive_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_admission(self.make_archive(temp))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_absent_archive_and_info_plist_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = self.run_admission(root / "missing.xcarchive")
            self.assertNotEqual(missing.returncode, 0)
            archive = self.make_archive(temp)
            (archive / "Info.plist").unlink()
            absent_info = self.run_admission(archive)
            self.assertNotEqual(absent_info.returncode, 0)

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            target = Path(temp) / "outside"
            target.write_text("outside")
            (archive / "linked-file").symlink_to(target)
            result = self.run_admission(archive)
            self.assertNotEqual(result.returncode, 0)

    def test_oversized_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            large_file = archive / "Products" / "large"
            with large_file.open("wb") as stream:
                stream.truncate(268435457)
            result = self.run_admission(archive)
            self.assertNotEqual(result.returncode, 0)

    def test_traversal_error_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            injected_error = textwrap.dedent(
                """\
                import os
                from pathlib import Path
                original_scandir = os.scandir
                def failing_scandir(path):
                    if Path(path).name == "Products":
                        raise PermissionError("simulated traversal error")
                    return original_scandir(path)
                os.scandir = failing_scandir
                """
            )
            result = self.run_admission(archive, injected_error + ADMISSION_CODE)
            self.assertNotEqual(result.returncode, 0)

    def test_special_entry_is_rejected(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO creation is unavailable")
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            os.mkfifo(archive / "special")
            result = self.run_admission(archive)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
