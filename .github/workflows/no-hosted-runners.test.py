import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).with_name("no-hosted-runners.yml")


def scanner_source():
    source = WORKFLOW.read_text()
    start = source.index("          import glob, re, sys")
    end = source.index("\n          PY", start)
    return textwrap.dedent(source[start:end])


class NoHostedRunnersScannerTest(unittest.TestCase):
    def test_scanner_uses_static_shell_and_invokes_venv_python(self):
        source = WORKFLOW.read_text()
        self.assertIn("        shell: bash\n", source)
        self.assertIn(
            '          "$RUNNER_TEMP/no-hosted-runner-venv/bin/python" - <<\'PY\'\n',
            source,
        )
        self.assertNotIn("shell: ${{ runner.temp }}", source)

    def run_scanner(self, workflow):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".github" / "workflows"
            target.mkdir(parents=True)
            (target / "fixture.yml").write_text(workflow)
            scanner = root / "scanner.py"
            scanner.write_text(scanner_source())
            return subprocess.run(
                ["python3", str(scanner)], cwd=root, text=True, capture_output=True
            )

    def test_names_comments_and_strings_are_not_runner_labels(self):
        result = self.run_scanner(
            """# windows-release.yml windows-rust-toolchain-missing Windows-target windows-sys
            name: windows-release.yml
            jobs:
              windows-rust-toolchain-missing:
                runs-on: [self-hosted, linux]
                steps:
                  - run: echo windows-target windows-sys
            """
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hosted_static_matrix_and_dynamic_literals_fail(self):
        for runs_on in ("windows-latest", "${{ matrix.runner }}", "${{ 'windows-latest' }}"):
            with self.subTest(runs_on=runs_on):
                result = self.run_scanner(
                    f"""jobs:\n  build:\n    runs-on: {runs_on}\n    strategy:\n      matrix:\n        runner: [self-hosted, windows-latest]\n    steps: []\n"""
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unresolved_dynamic_expression_fails_closed(self):
        result = self.run_scanner("jobs:\n  build:\n    runs-on: ${{ inputs.runner }}\n")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_matrix_resolution_is_scoped_to_the_current_job(self):
        result = self.run_scanner(
            """jobs:
  build:
    runs-on: ${{ matrix.runner }}
    strategy:
      matrix:
        runner: [self-hosted, linux]
  other:
    runs-on: self-hosted
    strategy:
      matrix:
        runner: [windows-latest]
    steps: []
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_matrix_include_values_are_resolved(self):
        result = self.run_scanner(
            """jobs:
  build:
    runs-on: ${{ matrix.runner }}
    strategy:
      matrix:
        include:
          - runner: windows-latest
"""
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_self_hosted_matrix_include_is_accepted(self):
        result = self.run_scanner(
            """jobs:
  build:
    runs-on: ${{ matrix.runner }}
    strategy:
      matrix:
        include:
          - runner: [self-hosted, linux]
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dynamic_matrix_requires_literal_self_hosted_constraint(self):
        fixtures = (
            (
                """runs-on:
      group: ${{ matrix.runner_group }}
      labels: [self-hosted, '${{ matrix.runner_label }}']
""",
                True,
            ),
            (
                """runs-on:
      group: ${{ matrix.runner_group }}
      labels: ${{ matrix.runner_label }}
""",
                False,
            ),
        )
        for runs_on, accepted in fixtures:
            with self.subTest(runs_on=runs_on):
                result = self.run_scanner(
                    "jobs:\n  build:\n    "
                    + runs_on
                    + "    strategy:\n      matrix: ${{ fromJSON(needs.prepare.outputs.matrix) }}\n"
                )
                if accepted:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_group_self_hosted_does_not_count_as_runner_label(self):
        result = self.run_scanner(
            """jobs:
  build:
    runs-on:
      group: self-hosted
      labels: ${{ matrix.runner_label }}
    strategy:
      matrix: ${{ fromJSON(needs.prepare.outputs.matrix) }}
"""
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nested_matrix_expression_requires_self_hosted_label(self):
        fixtures = (
            ("runs-on: ${{ matrix.runner }}\n", False),
            ("runs-on: [self-hosted, '${{ matrix.runner }}']\n", True),
        )
        for runs_on, anchored in fixtures:
            with self.subTest(anchored=anchored):
                result = self.run_scanner(
                    "jobs:\n  build:\n    "
                    + runs_on
                    + "    strategy:\n      matrix:\n        runner: ${{ inputs.runner }}\n"
                )
                if anchored:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mixed_self_hosted_and_hosted_labels_fail(self):
        result = self.run_scanner(
            "jobs:\n  build:\n    runs-on: [self-hosted, windows-latest]\n"
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_malformed_yaml_fails_closed(self):
        result = self.run_scanner("jobs:\n  build:\n    runs-on: [self-hosted\n")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
