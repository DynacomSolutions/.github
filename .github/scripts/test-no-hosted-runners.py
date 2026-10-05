"""Exercise the workflow's inline runner scanner against small fixture repos."""

import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest


WORKFLOW = pathlib.Path(__file__).parents[1] / "workflows/no-hosted-runners.yml"
SCANNER_START = "          import glob, re, sys\n"
SCANNER_END = "          PY\n"


def scanner_source():
    workflow = WORKFLOW.read_text()
    start = workflow.index(SCANNER_START)
    end = workflow.index(SCANNER_END, start)
    return textwrap.dedent(workflow[start:end])


class RunnerScannerTests(unittest.TestCase):
    def scan(self, files):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            return subprocess.run(
                [sys.executable, "-c", scanner_source()],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_accepts_self_hosted_and_resolves_safe_matrix(self):
        result = self.scan(
            {
                ".github/workflows/ci.yml": """\
                    name: CI
                    on: pull_request
                    jobs:
                      fixed:
                        runs-on:
                          group: linux
                          labels: [self-hosted, linux]
                      matrix:
                        strategy:
                          matrix:
                            runner: [team-runners]
                        runs-on: ${{ matrix.runner }}
                """
            }
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK: no GitHub-hosted runners referenced", result.stdout)

    def test_rejects_direct_hosted_label_and_matrix_include(self):
        result = self.scan(
            {
                ".github/workflows/ci.yaml": """\
                    jobs:
                      direct:
                        runs-on: ubuntu-latest
                      matrix:
                        strategy:
                          matrix:
                            runner: [team-runners]
                            include:
                              - runner: windows-latest
                        runs-on: ${{ matrix.runner }}
                """
            }
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("GitHub-hosted runner 'ubuntu-latest'", result.stdout)
        self.assertIn("GitHub-hosted runner 'windows-latest'", result.stdout)

    def test_rejects_unsupported_runner_expression(self):
        result = self.scan(
            {
                ".github/workflows/ci.yml": """\
                    jobs:
                      dynamic:
                        runs-on: ${{ vars.RUNNER }}
                """
            }
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unsupported runner expression", result.stdout)

    def test_parse_error_fails_closed(self):
        result = self.scan({".github/workflows/broken.yml": "jobs: [unterminated"})
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("parse failed", result.stdout)

    def test_workflow_uses_bounded_native_python_provisioning(self):
        workflow = WORKFLOW.read_text()
        self.assertNotIn("actions/setup-python", workflow)
        self.assertIn("python3 --version", workflow)
        self.assertIn("Python 3.12 is required", workflow)
        self.assertIn("pyyaml-6.0.2.tar.gz", workflow)
        self.assertIn(
            "d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e",
            workflow,
        )
        self.assertIn("archive.extractfile(member)", workflow)
        self.assertIn('assert yaml.__version__ == "6.0.2"', workflow)
        self.assertIn('timeout 120s python3 - <<\'PY\'', workflow)
        self.assertEqual(workflow.count("timeout-minutes:"), 4)


if __name__ == "__main__":
    unittest.main()
