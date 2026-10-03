import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).with_name("no-hosted-runners.yml")


def scanner_source():
    source = WORKFLOW.read_text()
    return textwrap.dedent(source[source.index("          import glob, re, sys") :])


class NoHostedRunnersScannerTest(unittest.TestCase):
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
