"""Run with: python -m unittest discover -s tools -p test_build_support.py."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_support import defer_file_snapshots, snapshot_files, write_preserving_format


class BuildSupportTests(unittest.TestCase):
    def test_deferred_snapshots_are_scoped_and_restore_after_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            a.mkdir()
            b.mkdir()
            (a / "one").write_bytes(b"first")
            (a / "build_manifest.json").write_bytes(b"excluded")
            (b / "two").write_bytes(b"second")
            initial = snapshot_files(a)
            self.assertEqual(set(initial), {"one"})
            with self.assertRaises(RuntimeError):
                with defer_file_snapshots(a):
                    with patch("build_support.sha256_file", side_effect=AssertionError):
                        self.assertEqual(snapshot_files(a / "."), {})
                    self.assertEqual(snapshot_files(a, force=True), initial)
                    self.assertEqual(len(snapshot_files(b)), 1)
                    with defer_file_snapshots(b):
                        self.assertEqual(snapshot_files(b), {})
                        self.assertEqual(snapshot_files(a), initial)
                    self.assertEqual(snapshot_files(a), {})
                    raise RuntimeError("restore scope")
            self.assertEqual(snapshot_files(a), initial)
            (a / "one").write_bytes(b"changed")
            self.assertNotEqual(snapshot_files(a), initial)
            (a / "one").unlink()
            self.assertEqual(snapshot_files(a), {})

    def test_writer_preserves_legacy_bytes_and_skips_identical_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for previous in (b"", b"old\n", b"old\r\n", b"\xef\xbb\xbfold\r\n"):
                for text in ("", "中文\nnext\n", "raw\r\nmixed\n"):
                    with self.subTest(previous=previous, text=text):
                        actual, reference = Path(tmp) / "actual", Path(tmp) / "reference"
                        actual.write_bytes(previous)
                        reference.write_bytes(previous)
                        # Repeated writes must preserve even the legacy mixed-newline behavior.
                        for _ in range(2):
                            old = reference.read_bytes()
                            newline = "\r\n" if b"\r\n" in old else "\n"
                            encoding = "utf-8-sig" if old.startswith(b"\xef\xbb\xbf") else "utf-8"
                            reference.write_text(text, encoding=encoding, newline=newline)
                            expected = reference.read_bytes()
                            if expected == actual.read_bytes():
                                with patch.object(Path, "write_bytes", side_effect=AssertionError):
                                    write_preserving_format(actual, text)
                            else:
                                write_preserving_format(actual, text)
                            self.assertEqual(actual.read_bytes(), expected)
            new = Path(tmp) / "nested" / "empty"
            write_preserving_format(new, "")
            self.assertTrue(new.is_file())
            self.assertEqual(new.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
