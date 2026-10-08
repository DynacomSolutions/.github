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
    def test_scanner_uses_static_shell_and_pinned_runner_python_yaml(self):
        source = WORKFLOW.read_text()
        self.assertIn("        shell: bash\n", source)
        # Runner's own Python must be exactly 3.12.
        self.assertIn("python3 --version\n", source)
        self.assertIn(
            "sys.version_info[:2] != (3, 12)",
            source,
        )
        self.assertIn("Python 3.12 is required", source)
        # YAML parser comes from a pinned source archive, verified by SHA-256.
        self.assertIn("- name: Provision pinned YAML parser\n", source)
        self.assertIn(
            'url = "https://files.pythonhosted.org/packages/54/ed/79a089b6be93607fa5cdaedf301d7dfb23af5f25c398d5ead2525b063e17/pyyaml-6.0.2.tar.gz"',
            source,
        )
        self.assertIn(
            'expected = "d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e"',
            source,
        )
        self.assertIn("hashlib.sha256(archive_bytes).hexdigest() != expected", source)
        self.assertIn("PyYAML 6.0.2 source archive checksum mismatch", source)
        self.assertIn('assert yaml.__version__ == "6.0.2"', source)
        self.assertIn("          python3 - <<'PY'\n", source)
        # No unpinned toolchain installs or dynamic shell.
        self.assertNotIn("actions/setup-python", source)
        self.assertNotIn("pip install", source)
        self.assertNotIn("shell: ${{ runner.temp }}", source)

    def test_run_script_has_no_literal_expression_opener(self):
        # GitHub evaluates expression openers inside run scripts, even in comments.
        opener = "$" + "{{"
        source = WORKFLOW.read_text()
        self.assertNotIn(opener, scanner_source())
        in_run = False
        for number, line in enumerate(source.splitlines(), 1):
            if line.strip().startswith("run:") and line.rstrip().endswith("|"):
                in_run = True
                indent = len(line) - len(line.lstrip())
                continue
            if in_run and line.strip() and len(line) - len(line.lstrip()) <= indent:
                in_run = False
            if in_run:
                self.assertNotIn(opener, line, f"line {number}")

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

    def test_conditional_between_two_literal_self_hosted_labels_is_accepted(self):
        runs_on = (
            "${{ (github.event_name == 'push' || startsWith(github.head_ref, 'train/'))"
            " && 'k3s-runners-main' || 'k3s-runners' }}"
        )
        result = self.run_scanner(f"jobs:\n  build:\n    runs-on: {runs_on}\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_conditional_with_a_hosted_literal_branch_fails(self):
        for runs_on in (
            "${{ github.event_name == 'push' && 'k3s-runners-main' || 'ubuntu-latest' }}",
            "${{ github.event_name == 'push' && 'windows-latest' || 'k3s-runners' }}",
            "${{ github.event_name == 'push' && inputs.runner || 'k3s-runners' }}",
        ):
            with self.subTest(runs_on=runs_on):
                result = self.run_scanner(f"jobs:\n  build:\n    runs-on: {runs_on}\n")
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_conditional_bypass_forms_fail(self):
        for runs_on in (
            "${{ inputs.r || github.event_name == 'push' && 'k3s-runners' || 'k3s-runners' }}",
            "${{ github.event_name == 'push' || inputs.r && 'k3s-runners' || 'k3s-runners' }}",
            "${{ github.event.inputs.r || x && 'k3s-runners' || 'k3s-runners' }}",
            "${{ vars.r || x && 'k3s-runners' || 'k3s-runners' }}",
            "${{ env.r || x && 'k3s-runners' || 'k3s-runners' }}",
            "${{ matrix.r || x && 'k3s-runners' || 'k3s-runners' }}",
            "${{ inputs.r && 'k3s-runners' || 'k3s-runners' }}",
            "${{ (a || b && 'k3s-runners' || 'k3s-runners' }}",
        ):
            with self.subTest(runs_on=runs_on):
                result = self.run_scanner(f"jobs:\n  build:\n    runs-on: {runs_on}\n")
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_conditional_allows_or_only_inside_one_parenthesised_group(self):
        runs_on = "${{ (a == 'x' || b == 'y') && 'k3s-runners-main' || 'k3s-runners' }}"
        result = self.run_scanner(f"jobs:\n  build:\n    runs-on: {runs_on}\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_function_calls_and_nested_braces_in_runs_on_fail_closed(self):
        o, c = "$" + "{{", "}}"
        for runs_on in (
            o + " format('{0}-latest', 'ubuntu') " + c,
            o + " x && format('{0}-24.04', 'ubuntu') || 'k3s-runners' " + c,
            o + " join(fromJSON('[\"ubuntu\",\"latest\"]'), '-') " + c,
            o + " fromJSON('\"ubuntu-latest\"') " + c,
            o + " fromJSON(toJSON('ubuntu-latest')) " + c,
            o + " toJSON('ubuntu-latest') " + c,
            o + " fromJSON('{\"a\":{\"b\":\"ubuntu-latest\"}}').a.b " + c,
            o + " x && '}' || format('{0}-latest', 'ubuntu') " + c,
            o + " format('{0}}}-latest', 'ubuntu') " + c,
            o + " x && 'k3s-runners' || 'k3s-runners'",
            "ubuntu-" + o + " matrix.v " + c,
            o + " 'k3s-runners' " + c + " " + o + " format('ubuntu-latest') " + c,
        ):
            with self.subTest(runs_on=runs_on):
                quoted = '"' + runs_on.replace("\\", "\\\\").replace('"', '\\"') + '"'
                result = self.run_scanner(f"jobs:\n  build:\n    runs-on: {quoted}\n")
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_function_calls_in_runs_on_list_and_group_forms_fail(self):
        o, c = "$" + "{{", "}}"
        expression = o + " format('{0}-latest', 'ubuntu') " + c
        for runs_on in (
            "['" + expression + "']",
            "{group: x, labels: '" + expression + "'}",
        ):
            with self.subTest(runs_on=runs_on):
                result = self.run_scanner(f"jobs:\n  build:\n    runs-on: {runs_on}\n")
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_brace_inside_a_literal_label_string_fails_closed(self):
        o, c = "$" + "{{", "}}"
        runs_on = o + " x && 'k3s-}-runners' || 'k3s-runners' " + c
        result = self.run_scanner(f'jobs:\n  build:\n    runs-on: "{runs_on}"\n')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_matrix_include_that_is_an_expression_or_has_non_mapping_items_fails(self):
        o, c = "$" + "{{", "}}"
        expression = o + " fromJSON(needs.prepare.outputs.extra) " + c
        for include in (
            f"'{expression}'",
            f"[\"{expression}\"]",
            "[plain-scalar]",
            f"[{{runner: k3s-runners}}, \"{expression}\"]",
        ):
            with self.subTest(include=include):
                result = self.run_scanner(
                    "jobs:\n  build:\n    runs-on: " + o + " matrix.runner " + c + "\n"
                    "    strategy:\n      matrix:\n        runner: [k3s-runners]\n"
                    f"        include: {include}\n"
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_matrix_include_of_literal_mappings_is_still_accepted(self):
        o, c = "$" + "{{", "}}"
        result = self.run_scanner(
            "jobs:\n  build:\n    runs-on: " + o + " matrix.runner " + c + "\n"
            "    strategy:\n      matrix:\n        runner: [k3s-runners]\n"
            "        include:\n          - runner: k3s-runners-main\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_external_reusable_workflow_fails_unless_allow_listed(self):
        for uses, accepted in (
            ("other-org/repo/.github/workflows/ci.yml@main", False),
            ("DynacomSolutions/ergon/.github/workflows/ci.yml@main", False),
            ("DynacomSolutions/.github-evil/.github/workflows/ci.yml@main", False),
            ("./.github/workflows/local.yml", True),
            ("DynacomSolutions/.github/.github/workflows/ci.yml@main", True),
        ):
            with self.subTest(uses=uses):
                result = self.run_scanner(f"jobs:\n  call:\n    uses: {uses}\n")
                if accepted:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_group_only_runs_on_fails_unless_the_group_is_allow_listed(self):
        for runs_on, accepted in (
            ("{group: Default}", False),
            ("{group: larger-hosted-runners}", False),
            ("{}", False),
            ("{group: windows-builders}", True),
        ):
            with self.subTest(runs_on=runs_on):
                result = self.run_scanner(f"jobs:\n  build:\n    runs-on: {runs_on}\n")
                if accepted:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
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

    def test_self_hosted_windows_builders_group_is_accepted(self):
        result = self.run_scanner(
            """jobs:
  build:
    runs-on:
      group: windows-builders
      labels: dynacom-dev-windows
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_windows_builders_group_does_not_excuse_hosted_labels(self):
        result = self.run_scanner(
            """jobs:
  build:
    runs-on:
      group: windows-builders
      labels: windows-latest
"""
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_malformed_yaml_fails_closed(self):
        result = self.run_scanner("jobs:\n  build:\n    runs-on: [self-hosted\n")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
