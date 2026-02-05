import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import import_jobs as ij


class ImportJobsTests(unittest.TestCase):
    def test_build_job_payload_includes_optional_fields(self):
        payload = ij.build_job_payload(
            input_dir="/mnt/photos",
            root_path="/2024/Trip",
            dry_run=True,
            requested_by="tester",
            worker_id="worker-1",
        )
        self.assertEqual(
            {
                "inputDir": "/mnt/photos",
                "rootPath": "/2024/Trip",
                "dryRun": True,
                "requestedBy": "tester",
                "workerId": "worker-1",
            },
            payload,
        )

    def test_build_job_payload_rejects_local_path_root(self):
        with self.assertRaises(ValueError):
            ij.build_job_payload(
                input_dir="/mnt/photos",
                root_path="C:/Users/me",
                dry_run=False,
            )

    def test_enqueue_job_parses_job_id(self):
        class FakeResponse:
            status = 200

            def readable(self):
                return True

            def read(self):
                return json.dumps({"jobId": "job-123"}).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()):
            result = ij.enqueue_job("https://example.com", {"inputDir": "x"})
        self.assertEqual("job-123", result["job_id"])


if __name__ == "__main__":
    unittest.main()
