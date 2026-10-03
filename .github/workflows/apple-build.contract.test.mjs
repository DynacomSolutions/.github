import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const workflow = readFileSync(fileURLToPath(new URL('./apple-build.yml', import.meta.url)), 'utf8');

describe('Apple reusable workflow contract', () => {
  it('is reusable only and requires an allowlisted immutable source plus invocation UUID', () => {
    assert.match(workflow, /^\s*workflow_call:/m);
    assert.doesNotMatch(workflow, /^\s*workflow_dispatch:/m);
    assert.match(workflow, /source-repository:[\s\S]*?required: true[\s\S]*?type: string/);
    assert.match(workflow, /source-ref:[\s\S]*?required: true[\s\S]*?type: string/);
    assert.match(workflow, /invocation-id:[\s\S]*?required: true[\s\S]*?type: string/);
    assert.match(workflow, /DynacomSolutions\/ergon/);
    assert.match(workflow, /\^\[0-9a-f\]\{40\}\$/);
  });

  it('checks out the exact commit without retaining credentials and emits bounded correlated evidence', () => {
    assert.match(workflow, /ref: \$\{\{ inputs\.source-ref \}\}/);
    assert.match(workflow, /persist-credentials: false/);
    assert.match(workflow, /git rev-parse HEAD/);
    assert.match(workflow, /actualHeadSha/);
    assert.match(workflow, /apple-toolchain-inventory\.json/);
    assert.match(workflow, /apple-run-manifest\.json/);
    assert.match(workflow, /retention-days: 7/);
    assert.match(workflow, /10485760/);
    assert.match(workflow, /104857600/);
    assert.match(workflow, /relative_to\(root\)/);
    assert.match(workflow, /resolve\(strict=True\)/);
    assert.match(workflow, /xcodebuild -version/);
    assert.match(workflow, /swift --version/);
    assert.match(workflow, /xcodebuild -showsdks/);
    assert.match(workflow, /xcrun simctl list runtimes --json/);
    assert.match(workflow, /schemaVersion': 1/);
    assert.match(workflow, /runnerGroup/);
    assert.match(workflow, /simulatorRuntimes/);
    assert.match(workflow, /apple-toolchain-inventory-\$\{\{ github\.run_id \}\}/);
    assert.match(workflow, /timeout-minutes: 60/);
    assert.match(workflow, /labels: apple-builder/);
    assert.match(workflow, /wc -c < "\$RUNNER_TEMP\/simulator-runtimes\.json"\)" -le 1048576/);
  });
});
