# Dynacom Solutions shared GitHub configuration

Reusable workflows and organisation-wide contributor guidance live here.

## Apple build worker

Use the shared Apple workflow for Xcode, Swift-on-Darwin, Simulator and other
macOS-only validation:

```yaml
jobs:
  apple:
    uses: DynacomSolutions/.github/.github/workflows/apple-build.yml@main
    with:
      task: swift-test
```

Private callers may omit the provenance inputs: the workflow checks out the
calling repository at the immutable `github.sha` for that run. The Ergon
private wrapper supplies all three provenance inputs (`source-repository`, a
full `source-ref` commit SHA, and a UUID `invocation-id`); partial tuples and
explicit provenance from other callers are rejected. Public callers are
skipped before the self-hosted Apple runner can be queued.

`toolchain` and `swift-test` run on the macOS host and accept `destination:
macos`. Xcode tasks accept `macos` (normalised to `platform=macOS`) or a
concrete platform-qualified Xcode destination, such as
`platform=iOS Simulator,name=iPhone 17`.

Available tasks are `toolchain`, `swift-test`, `xcode-build` and `xcode-test`.
The job routes to the protected `apple-builders` runner group. Live capacity is
published in the platform cluster through `kubectl get externalworkers`.
