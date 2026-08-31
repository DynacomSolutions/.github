# Agent instructions

## Apple and macOS work

- Any task requiring Xcode, Swift on Darwin, Apple signing, notarisation,
  Simulator, DMG validation or Gatekeeper validation must use the shared
  `apple-builders` GitHub Actions runner group with the `apple-builder` label.
- Prefer `.github/workflows/apple-build.yml` from this repository as a reusable
  workflow rather than adding repository-specific SSH automation.
- Discover live availability with `kubectl get externalworkers`; the platform
  resource is `macbook-builder`.
- A Linux runner, including Linux hosted through OrbStack on Mac hardware, is
  not acceptance evidence for Apple-specific work.
- The MacBook is a personal machine and best-effort by explicit decision. Use
  only the declared build interface, preserve personal data, and do not block
  work by repeatedly questioning that accepted constraint.
