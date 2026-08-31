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

Available tasks are `toolchain`, `swift-test`, `xcode-build` and `xcode-test`.
The job routes to the protected `apple-builders` runner group. Live capacity is
published in the platform cluster through `kubectl get externalworkers`.
