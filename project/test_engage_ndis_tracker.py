"""Offline checks; all token-shaped values below are synthetic."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import engage_ndis_tracker as tracker


def fake_token():
    return b"sk" + b"." + b"synthetic_payload" + b"." + b"not_a_real_signature"


class RedactionTests(unittest.TestCase):
    def test_removes_every_occurrence_without_changing_other_bytes(self):
        token = fake_token()
        public = b"pk" + b".public.value"
        temporary = b"tk" + b".temporary.value"
        data = b"\xff<script>key='" + token + b"'; public='" + public + b"'</script>" + token
        result, count = tracker.redact_credentials(data)
        self.assertEqual(count, 3)
        self.assertEqual(result, data.replace(token, tracker.REDACTION_MARKER).replace(public, tracker.REDACTION_MARKER))
        self.assertNotIn(public, result)
        self.assertEqual(tracker.redact_credentials(temporary), (tracker.REDACTION_MARKER, 1))
        self.assertEqual(tracker.redact_credentials(result), (result, 0))

    def test_does_not_redact_ordinary_text(self):
        data = b"<p>No credentials here; task.example and sk.incomplete</p>"
        self.assertEqual(tracker.redact_credentials(data), (data, 0))

    def test_archive_and_manifest_contain_no_secret(self):
        token = fake_token()
        source = b"<script>key='" + token + b"'</script><a href='/projects'>Projects</a>"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "archive/gov/engage-ndis"
            with patch.object(tracker, "ROOT", root), patch.object(tracker, "ARCHIVE", archive), \
                 patch.object(tracker, "fetch", return_value=(source, "text/html")), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                tracker.main()
                tracker.main()
            self.assertNotIn(token.decode(), output.getvalue())
            for path in archive.rglob("*"):
                if path.is_file():
                    self.assertNotIn(token, path.read_bytes())
            manifest = json.loads((archive / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(len(manifest["items"]), 2)
            for entry in manifest["items"].values():
                saved = (root / entry["path"]).read_bytes()
                self.assertEqual(entry["sha256"], hashlib.sha256(saved).hexdigest())
                self.assertEqual(entry["source_sha256"], hashlib.sha256(source).hexdigest())
                self.assertEqual(entry["redactions"], {"mapbox_access_token": 1})
                self.assertNotEqual(entry["sha256"], entry["source_sha256"])

    def test_failed_fetch_keeps_previously_redacted_capture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "archive/gov/engage-ndis"
            with patch.object(tracker, "ROOT", root), patch.object(tracker, "ARCHIVE", archive), \
                 contextlib.redirect_stdout(io.StringIO()):
                with patch.object(tracker, "fetch", return_value=(fake_token(), "text/html")):
                    tracker.main()
                before = (archive / "pages/home/index.html").read_bytes()
                with patch.object(tracker, "fetch", side_effect=RuntimeError("Fetch unavailable")):
                    tracker.main()
            manifest = json.loads((archive / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "partial")
            self.assertEqual((archive / "pages/home/index.html").read_bytes(), before)
            self.assertEqual(manifest["items"][tracker.clean(tracker.SEEDS[0])]["redactions"],
                             {"mapbox_access_token": 1})


if __name__ == "__main__":
    unittest.main()
