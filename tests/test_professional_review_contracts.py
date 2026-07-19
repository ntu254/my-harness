import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "harness.py"


class HarnessProfessionalReviewContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.env = os.environ.copy()
        self.env["MY_HARNESS_DB"] = str(self.workspace / "harness" / "harness-test.db")
        self.env["MY_HARNESS_WORKSPACE"] = str(self.workspace)
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

    def python_shell_command(self) -> str:
        if os.name == "nt":
            return subprocess.list2cmdline([sys.executable])
        return shlex.quote(sys.executable)

    def test_adapter_argv_mode_renders_prompt_file_and_records_run(self) -> None:
        argv = [
            sys.executable,
            "-c",
            "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text(encoding='utf-8'))",
            "{prompt_file}",
        ]
        registered = self.run_json(
            "--json",
            "adapter",
            "register",
            "--id",
            "argv-template-reader",
            "--provider",
            "mock",
            "--command-template",
            "python prompt-file-reader",
            "--command-mode",
            "argv",
            "--command-argv-json",
            json.dumps(argv),
            "--availability",
            "present",
            "--trust",
            "verified_local",
            "--capabilities",
            "code-generation,code-analysis",
        )
        self.assertEqual(registered["command_mode"], "argv")

        run = self.run_json(
            "--json",
            "adapter",
            "run",
            "--adapter",
            "argv-template-reader",
            "--id",
            "TST-ADAPTER-ARGV",
            "--summary",
            "Adapter argv template test",
            "--prompt-template",
            "templates/prompts/adapter-smoke.md",
            "--var",
            "task=render prompt",
            "--var",
            "context=temp workspace",
            "--var",
            "outcome=completed run",
            "--verify-command",
            f"{sys.executable} --version",
            "--timeout",
            "30",
        )

        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["agent_exit_code"], 0)
        self.assertEqual(run["verify_exit_code"], 0)
        self.assertEqual(len(run["evidence_ids"]), 2)
        self.assertTrue((self.workspace / run["log_dir"] / "agent.log").exists())
        self.assertTrue((self.workspace / "harness" / "prompts" / "TST-ADAPTER-ARGV.prompt.txt").exists())

    def test_adapter_shell_raw_prompt_requires_explicit_override(self) -> None:
        self.run_json(
            "--json",
            "adapter",
            "register",
            "--id",
            "unsafe-shell-prompt",
            "--provider",
            "mock",
            "--command-template",
            "{prompt}",
            "--command-mode",
            "shell",
            "--availability",
            "present",
            "--trust",
            "verified_local",
        )

        result = self.run_raw(
            "--json",
            "adapter",
            "run",
            "--adapter",
            "unsafe-shell-prompt",
            "--id",
            "TST-RAW-PROMPT",
            "--summary",
            "Raw prompt guard",
            "--prompt",
            "echo should-not-run",
            "--verify-command",
            f"{sys.executable} --version",
            expect=1,
        )
        self.assertIn("raw {prompt}", result.stderr)

    def test_adapter_prompt_shell_preserves_percent_literals(self) -> None:
        command = f'{self.python_shell_command()} -c "import sys; print(sys.argv[1])" {{prompt_shell}}'
        self.run_json(
            "--json",
            "adapter",
            "register",
            "--id",
            "prompt-shell-literal",
            "--provider",
            "mock",
            "--command-template",
            command,
            "--command-mode",
            "shell",
            "--availability",
            "present",
            "--trust",
            "verified_local",
        )

        run = self.run_json(
            "--json",
            "adapter",
            "run",
            "--adapter",
            "prompt-shell-literal",
            "--id",
            "TST-PROMPT-SHELL-LITERAL",
            "--summary",
            "Prompt shell literal guard",
            "--prompt",
            "%PATH%",
            "--verify-command",
            f"{self.python_shell_command()} --version",
            "--timeout",
            "30",
        )

        log = (self.workspace / run["log_dir"] / "agent.log").read_text(encoding="utf-8")
        self.assertIn("%PATH%", log)
        self.assertNotIn(os.environ.get("PATH", ""), log)

    def test_adapter_enforces_prompt_length_contract(self) -> None:
        self.run_json(
            "--json",
            "adapter",
            "register",
            "--id",
            "short-prompt-only",
            "--provider",
            "mock",
            "--command-template",
            f"{sys.executable} --version",
            "--availability",
            "present",
            "--trust",
            "verified_local",
            "--max-prompt-length",
            "5",
        )

        result = self.run_raw(
            "--json",
            "adapter",
            "run",
            "--adapter",
            "short-prompt-only",
            "--id",
            "TST-PROMPT-LIMIT",
            "--summary",
            "Prompt length guard",
            "--prompt",
            "too long",
            "--verify-command",
            f"{sys.executable} --version",
            expect=1,
        )
        self.assertIn("exceeds adapter max_prompt_length", result.stderr)

    def test_adapter_enforces_template_support_contract(self) -> None:
        self.run_json(
            "--json",
            "adapter",
            "register",
            "--id",
            "no-template-support",
            "--provider",
            "mock",
            "--command-template",
            f"{sys.executable} --version",
            "--availability",
            "present",
            "--trust",
            "verified_local",
            "--no-supports-templates",
        )

        result = self.run_raw(
            "--json",
            "adapter",
            "run",
            "--adapter",
            "no-template-support",
            "--id",
            "TST-TEMPLATE-SUPPORT",
            "--summary",
            "Template support guard",
            "--prompt-template",
            "templates/prompts/adapter-smoke.md",
            "--verify-command",
            f"{sys.executable} --version",
            expect=1,
        )
        self.assertIn("does not support prompt templates", result.stderr)

    def test_adapter_enforces_argv_support_contract(self) -> None:
        argv = [sys.executable, "--version"]
        self.run_json(
            "--json",
            "adapter",
            "register",
            "--id",
            "no-argv-support",
            "--provider",
            "mock",
            "--command-template",
            "python --version",
            "--command-mode",
            "argv",
            "--command-argv-json",
            json.dumps(argv),
            "--availability",
            "present",
            "--trust",
            "verified_local",
            "--no-supports-argv",
        )

        result = self.run_raw(
            "--json",
            "adapter",
            "run",
            "--adapter",
            "no-argv-support",
            "--id",
            "TST-ARGV-SUPPORT",
            "--summary",
            "Argv support guard",
            "--prompt",
            "hello",
            "--verify-command",
            f"{sys.executable} --version",
            expect=1,
        )
        self.assertIn("does not support argv command mode", result.stderr)

    def test_adapter_preset_installs_capability_metadata(self) -> None:
        self.run_json("--json", "adapter", "preset", "all")
        capability = self.run_json("--json", "adapter", "capability", "--adapter", "mock-python")
        self.assertEqual(len(capability), 1)
        capability = capability[0]

        self.assertEqual(capability["adapter_id"], "mock-python")
        self.assertIn("echo", capability["capabilities"])
        self.assertEqual(capability["verification_mode"], "argv")
        self.assertTrue(capability["supports_argv"])

    def test_adapter_conformance_reports_mock_preset_ready(self) -> None:
        self.run_json("--json", "adapter", "preset", "mock-python")
        conformance = self.run_json("--json", "adapter", "conformance", "--adapter", "mock-python")

        self.assertEqual(conformance["status"], "pass")
        self.assertEqual(len(conformance["results"]), 1)
        result = conformance["results"][0]
        self.assertEqual(result["adapter_id"], "mock-python")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["availability"], "present")
        self.assertEqual(result["metadata_errors"], [])

    def test_route_is_deterministic_for_same_input(self) -> None:
        self.seed_tools()
        args = [
            "route",
            "--json",
            "--summary",
            "Fix login regression",
            "--work-type",
            "bugfix",
            "--scope",
            "module",
            "--risk",
            "medium",
        ]
        first = self.run_json(*args)
        second = self.run_json(*args)

        for key in [
            "lane",
            "workflow",
            "skills",
            "required_capabilities",
            "missing_required_capabilities",
            "proof_policy",
        ]:
            self.assertEqual(first[key], second[key])
        self.assertEqual(first["lane"], "normal")
        self.assertEqual(first["workflow"], "debug-regression-loop")
        self.assertEqual(first["proof_policy"], "pass")

    def test_route_approval_required_for_irreversible_external_work(self) -> None:
        self.seed_tools()
        route = self.run_json(
            "route",
            "--json",
            "--summary",
            "Deploy production database migration",
            "--work-type",
            "migration",
            "--scope",
            "external_system",
            "--risk",
            "critical",
            "--reversibility",
            "irreversible",
        )

        self.assertEqual(route["lane"], "approval_required")
        self.assertEqual(route["workflow"], "approval-first")
        self.assertTrue(route["human_gate_required"])
        self.assertEqual(route["proof_policy"], "block")
        self.assertIn("artifact-lifecycle", route["skills"])
        self.assertIn("release-readiness", route["skills"])
        self.assertIn("human-gate", route["skills"])

    def test_route_high_risk_for_costly_uncertain_infrastructure_work(self) -> None:
        self.seed_tools()
        route = self.run_json(
            "route",
            "--json",
            "--summary",
            "Refactor deployment configuration",
            "--work-type",
            "refactor",
            "--scope",
            "infrastructure",
            "--uncertainty",
            "high",
            "--reversibility",
            "costly",
            "--risk",
            "high",
        )

        self.assertEqual(route["lane"], "high_risk")
        self.assertEqual(route["workflow"], "plan-gated")
        self.assertFalse(route["human_gate_required"])
        self.assertIn("high-risk-plan", route["skills"])
        self.assertEqual(route["proof_policy"], "pass")

    def test_route_tiny_file_change_stays_lightweight(self) -> None:
        self.seed_tools()
        route = self.run_json(
            "route",
            "--json",
            "--summary",
            "Fix one typo",
            "--work-type",
            "maintenance",
            "--scope",
            "file",
            "--uncertainty",
            "low",
            "--reversibility",
            "easy",
            "--risk",
            "low",
        )

        self.assertEqual(route["lane"], "tiny")
        self.assertEqual(route["workflow"], "tiny-change")
        self.assertEqual(route["skills"], ["tiny-change", "code-quality-review"])
        self.assertNotIn("spec-clarification", route["skills"])
        self.assertEqual(route["proof_policy"], "pass")


if __name__ == "__main__":
    unittest.main()
