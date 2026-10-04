import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("apple-archive-admission.py")
SPEC = importlib.util.spec_from_file_location("apple_archive_admission", MODULE_PATH)
assert SPEC and SPEC.loader
admission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admission)


class ArchiveAdmissionTests(unittest.TestCase):
    def make_archive(self, parent: str) -> Path:
        archive = Path(parent) / "Example.xcarchive"
        archive.mkdir()
        (archive / "Info.plist").write_text("plist")
        (archive / "Products").mkdir()
        (archive / "Products" / "app").write_bytes(b"app")
        return archive

    def test_valid_archive_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(admission.admit_archive(self.make_archive(temp)))

    def test_absent_archive_and_info_plist_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(admission.admit_archive(root / "missing.xcarchive"))
            archive = self.make_archive(temp)
            (archive / "Info.plist").unlink()
            self.assertFalse(admission.admit_archive(archive))

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            target = Path(temp) / "outside"
            target.write_text("outside")
            (archive / "linked-file").symlink_to(target)
            self.assertFalse(admission.admit_archive(archive))

    def test_oversized_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            self.assertFalse(admission.admit_archive(archive, max_bytes=4))

    def test_traversal_error_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            original_scandir = os.scandir

            def failing_scandir(path):
                if Path(path).name == "Products":
                    raise PermissionError("simulated traversal error")
                return original_scandir(path)

            with mock.patch.object(admission.os, "scandir", side_effect=failing_scandir):
                self.assertFalse(admission.admit_archive(archive))

    def test_special_entry_is_rejected(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO creation is unavailable")
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(temp)
            os.mkfifo(archive / "special")
            self.assertFalse(admission.admit_archive(archive))


if __name__ == "__main__":
    unittest.main()
