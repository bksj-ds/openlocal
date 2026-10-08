from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from openlocal.cli import main


class CliTests(unittest.TestCase):
    def test_doctor_json(self):
        snapshot = {"schema_version": "1.0", "status": {"ready": False}}
        output = io.StringIO()
        with patch("openlocal.cli.collect_snapshot", return_value=snapshot), contextlib.redirect_stdout(output):
            result = main(["doctor", "--json"])
        self.assertEqual(result, 0)
        self.assertIn('"schema_version": "1.0"', output.getvalue())

    def test_planned_command_fails_explicitly(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = main(["recommend"])
        self.assertEqual(result, 2)
        self.assertIn("not implemented yet", error.getvalue())


if __name__ == "__main__":
    unittest.main()

