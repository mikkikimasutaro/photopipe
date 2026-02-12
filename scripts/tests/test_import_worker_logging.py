import io
import os
import sys
import types
import unittest
from contextlib import redirect_stderr


def _install_stub_modules():
    stubs = {}
    for name in [
        "firebase_admin",
        "firebase_admin.credentials",
        "firebase_admin.firestore",
        "google",
        "google.cloud",
        "google.cloud.pubsub_v1",
    ]:
        if name not in sys.modules:
            mod = types.ModuleType(name)
            sys.modules[name] = mod
            stubs[name] = mod
    return stubs


def _remove_stub_modules(stubs):
    for name in stubs:
        sys.modules.pop(name, None)


class ImportWorkerLoggingTests(unittest.TestCase):
    def test_log_suppressed_when_quiet(self):
        stubs = _install_stub_modules()
        original = os.environ.get("IMPORT_WORKER_LOG_LEVEL")
        try:
            os.environ["IMPORT_WORKER_LOG_LEVEL"] = "quiet"
            import import_worker

            buf = io.StringIO()
            with redirect_stderr(buf):
                import_worker._log("hello")
            self.assertEqual("", buf.getvalue())
        finally:
            _remove_stub_modules(stubs)
            if original is None:
                os.environ.pop("IMPORT_WORKER_LOG_LEVEL", None)
            else:
                os.environ["IMPORT_WORKER_LOG_LEVEL"] = original


if __name__ == "__main__":
    unittest.main()
