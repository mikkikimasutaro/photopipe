import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import find_directory as fd


class FindDirectoryTests(unittest.TestCase):
    def test_find_keyword_dirs_skips_hidden_and_skip_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            visible = root / "Pictures" / "Trip"
            hidden = root / ".hidden" / "Trip"
            skipped = root / "node_modules" / "Trip"

            for p in (visible, hidden, skipped):
                p.mkdir(parents=True, exist_ok=True)

            results = fd.find_keyword_dirs(
                roots=[root],
                keyword="trip",
                include_hidden=False,
                skip_dirnames={"node_modules"},
            )

            self.assertEqual([visible], results)

    def test_count_media_by_directory_counts_only_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.jpg").write_bytes(b"data")
            (base / "b.txt").write_bytes(b"data")
            (base / ".hidden.png").write_bytes(b"data")

            counts = fd.count_media_by_directory(
                dirs=[base],
                include_hidden=False,
                skip_dirnames=set(),
            )

            self.assertEqual(1, counts.get(base, 0))


if __name__ == "__main__":
    unittest.main()
