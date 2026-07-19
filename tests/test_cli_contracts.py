import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "harness.py"
SPEC = importlib.util.spec_from_file_location("harness_cli", CLI)
assert SPEC and SPEC.loader
HARNESS_CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS_CLI)


class HarnessCliContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = os.environ.copy()
        self.env["MY_HARNESS_DB"] = str(Path(self.temp_dir.name) / "harness-test.db")
        self.run_json("--json", "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_raw(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )
        if result.returncode != expect:
            self.fail(
                "command failed\n"
                f"args: {args}\n"
                f"expected: {expect}\n"
                f"actual: {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def run_json(self, *args: str, expect: int = 0):
        result = self.run_raw(*args, expect=expect)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"stdout was not JSON: {exc}\n{result.stdout}")

    def seed_tools(self):
        return self.run_json("--json", "tool", "seed")

    def test_route_blocks_ui_when_required_visual_proof_is_missing(self) -> None:
        self.seed_tools()
        route = self.run_json(
            "route",
            "--json",
            "--summary",
            "Update dashboard component",
            "--work-type",
            "feature",
            "--scope",
            "module",
            "--risk",
            "medium",
            "--tag",
            "ui",
        )

        self.assertEqual(route["lane"], "normal")
        self.assertEqual(route["proof_policy"], "block")
        self.assertIn("design-quality-review", route["skills"])
        self.assertIn("browser-check", route["missing_required_capabilities"])
        self.assertIn("accessibility-check", route["missing_required_capabilities"])
        self.assertIn("visual-review", route["missing_required_capabilities"])

    def test_approval_scope_contract(self) -> None:
        approval = self.run_json(
            "--json",
            "approval",
            "request",
            "--summary",
            "Deploy production migration",
            "--risk",
            "critical",
            "--scope",
            "deploy-prod",
            "--ttl-minutes",
            "60",
        )
        resolved = self.run_json(
            "--json",
            "approval",
            "resolve",
            "--id",
            str(approval["id"]),
            "--status",
            "approved",
        )
        self.assertEqual(resolved["status"], "approved")

        valid = self.run_json("--json", "approval", "check", "--id", str(approval["id"]), "--scope", "deploy-prod")
        self.assertTrue(valid["valid"])

        wrong_scope = self.run_json(
            "--json",
            "approval",
            "check",
            "--id",
            str(approval["id"]),
            "--scope",
            "other-scope",
        )
        self.assertFalse(wrong_scope["valid"])
        self.assertEqual(wrong_scope["status"], "scope_mismatch")
        self.assertIn("deploy-prod", wrong_scope["reason"])

    def test_completion_requires_fresh_evidence(self) -> None:
        self.seed_tools()
        route = self.run_json(
            "route",
            "--json",
            "--summary",
            "Fix parser bug",
            "--work-type",
            "bugfix",
            "--scope",
            "module",
            "--risk",
            "medium",
            "--persist",
        )
        story_id = "TST-COMPLETE"
        self.run_json("--json", "story", "add", "--id", story_id, "--title", "Contract test story", "--lane", "normal")

        blocked = self.run_json(
            "report",
            "final",
            "--json",
            "--story",
            story_id,
            "--route-id",
            str(route["route_id"]),
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("missing_evidence", blocked["blockers"])

        evidence = self.run_json(
            "--json",
            "evidence",
            "add",
            "--kind",
            "test",
            "--target",
            story_id,
            "--result",
            "pass",
            "--command",
            "python -m unittest",
            "--story",
            story_id,
        )
        self.assertEqual(evidence["result"], "pass")

        report = self.run_json(
            "report",
            "final",
            "--json",
            "--story",
            story_id,
            "--route-id",
            str(route["route_id"]),
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["evidence_ids"], [evidence["id"]])

        completed = self.run_json(
            "complete",
            "--json",
            "--story",
            story_id,
            "--route-id",
            str(route["route_id"]),
        )
        self.assertTrue(completed["completed"])

    def test_benchmark_contract_scores_are_reported(self) -> None:
        self.seed_tools()
        result = self.run_json("bench", "run", "--json", "--fail-on-regression")

        self.assertEqual(result["fail_count"], 0)
        self.assertGreaterEqual(result["pass_count"], 1)
        for key in ["quality", "cost", "adaptiveness", "durability", "total"]:
            self.assertIn(key, result["scores"])

    def test_json_schema_subset_validator_reports_contract_errors(self) -> None:
        schema = {
            "type": "object",
            "required": ["id", "items"],
            "additionalProperties": False,
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "integer", "minimum": 1},
                },
            },
        }

        self.assertEqual(HARNESS_CLI.validate_json_schema_subset({"id": "ok", "items": [1]}, schema), [])
        errors = HARNESS_CLI.validate_json_schema_subset({"id": "", "extra": True, "items": [0]}, schema)
        self.assertTrue(any("unexpected property extra" in error for error in errors))
        self.assertTrue(any("shorter than minLength" in error for error in errors))
        self.assertTrue(any("below minimum" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
