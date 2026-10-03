import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const workflow = readFileSync(
  fileURLToPath(new URL("./apple-build.yml", import.meta.url)),
  "utf8",
);

const jobBlock = (name) => {
  const jobsStart = workflow.indexOf("\njobs:\n");
  const start = workflow.indexOf(`  ${name}:\n`, jobsStart);
  assert.notEqual(start, -1, `workflow is missing the ${name} job`);
  const nextJob = workflow.slice(start + 2).match(/\n  [A-Za-z0-9_-]+:\n/);
  const end = nextJob ? start + 2 + nextJob.index : undefined;
  return workflow.slice(start, end);
};

describe("Apple reusable workflow contract", () => {
  it("is reusable only and keeps legacy callers on their immutable caller commit", () => {
    const apple = jobBlock("apple");
    assert.match(workflow, /^\s*workflow_call:/m);
    assert.doesNotMatch(workflow, /^\s*workflow_dispatch:/m);
    assert.match(
      workflow,
      /source-repository:[\s\S]*?required: false[\s\S]*?default: ""[\s\S]*?type: string/,
    );
    assert.match(
      workflow,
      /source-ref:[\s\S]*?required: false[\s\S]*?default: ""[\s\S]*?type: string/,
    );
    assert.match(
      workflow,
      /invocation-id:[\s\S]*?required: false[\s\S]*?default: ""[\s\S]*?type: string/,
    );
    assert.match(apple, /if: \$\{\{ github\.event\.repository\.private == true && inputs\.task != 'ios-log-capture' && inputs\.task != 'ios-interactive-session' \}\}/);
    assert.match(workflow, /inputs\.source-repository \|\| github\.repository/);
    assert.match(workflow, /inputs\.source-ref \|\| github\.sha/);
    assert.match(
      workflow,
      /\[\[ "\$APPLE_SOURCE_REPOSITORY" == "\$GITHUB_REPOSITORY" \]\]/,
    );
    assert.match(
      workflow,
      /\[\[ "\$GITHUB_REPOSITORY" == "DynacomSolutions\/ergon" \]\]/,
    );
    assert.match(
      workflow,
      /\[\[ -n "\$APPLE_SOURCE_REPOSITORY_INPUT" && -n "\$APPLE_SOURCE_REF_INPUT" && -n "\$APPLE_INVOCATION_ID_INPUT" \]\]/,
    );
    assert.match(workflow, /DynacomSolutions\/ergon/);
    assert.match(workflow, /\^\[0-9a-f\]\{40\}\$/);
  });

  it("isolates the specialised iOS jobs behind private Ergon workflow-dispatch gates", () => {
    const capture = jobBlock("ios_log_capture");
    const interactive = jobBlock("ios_interactive_session");

    assert.match(capture, /if: \$\{\{ github\.event\.repository\.private == true && inputs\.task == 'ios-log-capture' \}\}/);
    assert.match(interactive, /if: \$\{\{ github\.repository == 'DynacomSolutions\/ergon' && github\.event\.repository\.private == true && inputs\.task == 'ios-interactive-session' \}\}/);
    for (const job of [capture, interactive]) {
      assert.match(job, /group: apple-builders[\s\S]*labels: apple-builder/);
      assert.match(job, /timeout-minutes: 10/);
      assert.match(job, /id-token: write/);
      assert.match(job, /APPLE_SOURCE_REPOSITORY: \$\{\{ inputs\.source-repository \|\| github\.repository \}\}/);
      assert.match(job, /APPLE_SOURCE_REF: \$\{\{ inputs\.source-ref \|\| github\.sha \}\}/);
      assert.match(job, /uses: actions\/checkout@v6[\s\S]*repository: \$\{\{ env\.APPLE_SOURCE_REPOSITORY \}\}[\s\S]*ref: \$\{\{ env\.APPLE_SOURCE_REF \}\}[\s\S]*persist-credentials: false/);
      assert.match(job, /MOBILE_IOS_OIDC_AUDIENCE: \$\{\{ vars\.MOBILE_IOS_OIDC_AUDIENCE \}\}/);
      assert.match(job, /MOBILE_IOS_BRIDGE_(URL|ORIGIN): \$\{\{ vars\.MOBILE_IOS_BRIDGE_URL \}\}/);
      assert.match(job, /\[\[ "\$GITHUB_REPOSITORY" == DynacomSolutions\/ergon && "\$GITHUB_EVENT_NAME" == workflow_dispatch \]\]/);
      assert.match(job, /\[\[ "\$APPLE_SOURCE_REPOSITORY" == "\$GITHUB_REPOSITORY" && "\$APPLE_SOURCE_REF" =~ \^\[0-9a-f\]\{40\}\$ \]\]/);
      assert.match(job, /- name: Validate private/);
    }
    assert.match(capture, /MOBILE_IOS_CAPTURE_ID: \$\{\{ inputs\.capture-id \}\}/);
    assert.match(capture, /MOBILE_IOS_LEASE_ID: \$\{\{ inputs\.lease-id \}\}/);
    assert.match(capture, /MOBILE_IOS_RUNTIME_ID: \$\{\{ inputs\.runtime-id \}\}/);
    assert.match(capture, /\[\[ "\$MOBILE_IOS_CAPTURE_ID" =~ \^\[0-9a-f\]\{8\}-\[0-9a-f\]\{4\}-4\[0-9a-f\]\{3\}-\[89ab\]\[0-9a-f\]\{3\}-\[0-9a-f\]\{12\}\$ \]\]/);
    assert.match(capture, /\[\[ -n "\$MOBILE_IOS_LEASE_ID" && -n "\$MOBILE_IOS_RUNTIME_ID" \]\]/);
    assert.match(capture, /\[\[ -n "\$MOBILE_IOS_BRIDGE_URL" && -n "\$MOBILE_IOS_OIDC_AUDIENCE" \]\]/);
    assert.match(interactive, /MOBILE_IOS_LEASE_ID: \$\{\{ inputs\.lease-id \}\}/);
    assert.match(interactive, /MOBILE_IOS_RUNTIME_ID: \$\{\{ inputs\.runtime-id \}\}/);
    assert.match(interactive, /\[\[ "\$MOBILE_IOS_LEASE_ID" =~ \^\[a-f0-9\]\{32\}\$ \]\]/);
    assert.match(interactive, /\[\[ "\$MOBILE_IOS_RUNTIME_ID" =~ \^\[A-Za-z0-9_-\]\{1,80\}\$ \]\]/);
    assert.match(interactive, /\[\[ -n "\$MOBILE_IOS_BRIDGE_ORIGIN" && -n "\$MOBILE_IOS_OIDC_AUDIENCE" \]\]/);
  });

  it("checks out the exact commit without retaining credentials and emits bounded correlated evidence", () => {
    assert.match(workflow, /ref: \$\{\{ env\.APPLE_SOURCE_REF \}\}/);
    assert.match(
      workflow,
      /repository: \$\{\{ env\.APPLE_SOURCE_REPOSITORY \}\}/,
    );
    assert.match(workflow, /persist-credentials: false/);
    assert.doesNotMatch(workflow, /APPLE_DESTINATION,,/);
    assert.match(workflow, /args\+=\(-destination "\$execution_destination"\)/);
    assert.match(workflow, /\$APPLE_TASK runs on the macOS host/);
    assert.match(workflow, /\^platform=macos,\(arch\|variant\)=\[\^,\]\+\$/);
    assert.match(
      workflow,
      /\^platform=ios\[\[:space:\]\]simulator,\(name\|id\)=\[\^,\]\+\(,os=\[\^,\]\+\)\?\$/,
    );
    assert.match(workflow, /git rev-parse HEAD/);
    assert.match(workflow, /actualHeadSha/);
    assert.match(workflow, /apple-toolchain-inventory\.json/);
    assert.match(workflow, /apple-run-manifest\.json/);
    assert.match(workflow, /workflowRunAttempt/);
    assert.match(workflow, /retention-days: 7/);
    assert.match(workflow, /10485760/);
    assert.match(workflow, /104857600/);
    assert.match(
      workflow,
      /name: Admit bounded retained evidence[\s\S]*?if: always\(\)[\s\S]*?tail -c 10485760/,
    );
    assert.match(
      workflow,
      /steps\.evidence\.outputs\.xcresult_admitted == 'true'/,
    );
    assert.match(workflow, /steps\.evidence\.outputs\.log_admitted == 'true'/);
    assert.doesNotMatch(workflow, /hashFiles\(format\('\{0\}\/apple-/);
    assert.match(
      workflow,
      /\[\[ \$result_count -gt 0 \]\] \|\| admitted=false/,
    );
    assert.match(workflow, /steps\.apple_task\.outputs\.platform/);
    assert.match(workflow, /relative_to\(root\)/);
    assert.match(workflow, /resolve\(strict=True\)/);
    assert.match(workflow, /xcodebuild -version/);
    assert.match(workflow, /swift --version/);
    assert.match(workflow, /xcodebuild -showsdks/);
    assert.match(workflow, /xcrun simctl list runtimes --json/);
    assert.match(workflow, /schemaVersion': 1/);
    assert.match(workflow, /runnerGroup/);
    assert.match(workflow, /simulatorRuntimes/);
    assert.match(
      workflow,
      /apple-toolchain-inventory-\$\{\{ github\.run_id \}\}-attempt-\$\{\{ github\.run_attempt \}\}/,
    );
    assert.match(
      workflow,
      /name: apple-log-\$\{\{ steps\.apple_task\.outputs\.platform \}\}-attempt-\$\{\{ github\.run_attempt \}\}/,
    );
    assert.match(
      workflow,
      /name: apple-xcresult-\$\{\{ steps\.apple_task\.outputs\.platform \}\}-attempt-\$\{\{ github\.run_attempt \}\}/,
    );
    assert.match(workflow, /timeout-minutes: 60/);
    assert.match(workflow, /labels: apple-builder/);
    assert.match(
      workflow,
      /wc -c < "\$RUNNER_TEMP\/simulator-runtimes\.json"\)" -le 1048576/,
    );
  });
});
