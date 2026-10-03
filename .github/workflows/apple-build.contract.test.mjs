import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const workflow = readFileSync(
  fileURLToPath(new URL("./apple-build.yml", import.meta.url)),
  "utf8",
);

describe("Apple reusable workflow contract", () => {
  it("is reusable only and keeps legacy callers on their immutable caller commit", () => {
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
    assert.match(
      workflow,
      /if: \$\{\{ github\.event\.repository\.private == true \}\}/,
    );
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
      /apple-toolchain-inventory-\$\{\{ github\.run_id \}\}/,
    );
    assert.match(workflow, /timeout-minutes: 60/);
    assert.match(workflow, /labels: apple-builder/);
    assert.match(
      workflow,
      /wc -c < "\$RUNNER_TEMP\/simulator-runtimes\.json"\)" -le 1048576/,
    );
  });
});
