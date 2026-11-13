# Detect and migrate removed APIs

## The situation

A team is preparing its cluster upgrade. Its manifest repository,
**`~/manifestes`**, is several versions old: part of it uses APIs Kubernetes has
**removed** since. As long as they stay that way, these files no longer apply,
and an automated deployment would break on upgrade day.

You are on **`k8s-cp.lab`**, with `kubectl` configured. The **`migration`**
namespace exists and is empty: none of these manifests is applied.

## What you must achieve

1. **`~/manifestes/rapport.txt`** names, one per line, the manifests that used a
   **removed API**, and only them.
2. The **six** manifests of the repository are still there, and the API server
   **accepts them all**. A file gets migrated, not deleted.
3. The migrated objects are **applied** in the `migration` namespace.
4. They describe **exactly** what the legacy manifests described: same values,
   same targets. A migration changes the API, not the intent.

## Useful bearings

- `kubectl apply --dry-run=server -f <file>` asks the API server whether it
  accepts a manifest, without creating anything. The error message names the API
  it no longer serves.
- `kubectl api-resources` and `kubectl explain <type>` tell under which API a
  type is served today, and which fields it expects.
- A removed API does not always change only its version: some fields changed
  **shape** in the current version. Read the error to the end.

## How you will know it works

The tests read the report, submit each file to the API server, then compare the
objects of the `migration` namespace with what the original manifests described.

```bash
dsoxlab check k8s-detecter-les-api-depreciees
```
