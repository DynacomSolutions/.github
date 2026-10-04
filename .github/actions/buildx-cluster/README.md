# buildx-cluster

Composite action that points `docker buildx` at the cluster's node-local
BuildKit daemon (remote driver) so image builds reuse a persistent layer cache,
and computes `cache-from` / `cache-to` values for a shared registry cache.

It reads two runner environment variables, set by the runner scale-set
templates, so nothing cluster-specific is committed here:

- `CI_BUILDKIT_ADDR`, for example `tcp://host:1234`
- `CI_REGISTRY_CACHE`, a plain-HTTP registry `host:port` used for cache refs

If the daemon is unreachable (for example on a node without one) the action
falls back to a local `docker-container` builder, so a workflow never fails
because of it. Without the variables it still works as a plain buildx setup.

```yaml
- uses: actions/checkout@v5
- id: bx
  uses: DynacomSolutions/.github/.github/actions/buildx-cluster@main
  with:
    cache-name: web
- uses: docker/build-push-action@v6
  with:
    context: .
    push: false
    load: true
    cache-from: ${{ steps.bx.outputs.cache-from }}
    cache-to: ${{ steps.bx.outputs.cache-to }}
```

`push-cache: auto` (default) exports the registry cache only on pushes to the
default branch; pull requests import it. The node-local layer cache is used by
every build regardless.

## Several images in one job

Call the action once, then build each image against its own cache repository
using the prefix outputs:

```yaml
- id: bx
  uses: DynacomSolutions/.github/.github/actions/buildx-cluster@main
- run: |
    docker buildx build --builder "${{ steps.bx.outputs.builder }}" --load \
      --cache-from "type=registry,ref=${{ steps.bx.outputs.cache-base }}/core:${{ steps.bx.outputs.cache-default-slug }}" \
      ${{ steps.bx.outputs.cache-export == 'true' && format('--cache-to "type=registry,ref={0}/core:{1},mode=max,image-manifest=true,oci-mediatypes=true"', steps.bx.outputs.cache-base, steps.bx.outputs.cache-slug) || '' }} \
      -t core:ci .
```
