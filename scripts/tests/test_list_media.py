import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import list_media as lm


class ListMediaTests(unittest.TestCase):
    def test_iter_media_files_top_level_only_and_hidden_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.jpg").write_bytes(b"data")
            (base / ".hidden.jpg").write_bytes(b"data")
            sub = base / "subdir"
            sub.mkdir()
            (sub / "b.jpg").write_bytes(b"data")

            visible = list(lm.iter_media_files(base, include_hidden=False))
            self.assertEqual([base / "a.jpg"], visible)

            all_files = list(lm.iter_media_files(base, include_hidden=True))
            self.assertIn(base / "a.jpg", all_files)
            self.assertIn(base / ".hidden.jpg", all_files)
            self.assertNotIn(sub / "b.jpg", all_files)


if __name__ == "__main__":
    unittest.main()
