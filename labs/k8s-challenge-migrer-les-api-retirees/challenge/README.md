# Challenge: Migrate removed APIs before an upgrade

## 📍 The situation

The platform team is preparing the next upgrade of the cluster. Its manifest
repository, **`~/plateforme`**, is several years old: some of the files use
APIs that Kubernetes has **removed**. Nobody knows which ones. The
**`plateforme`** namespace exists, and nothing is applied in it. You are on
the control plane, with `kubectl` configured.

## 🎯 What you must obtain

1. A report **`~/plateforme/rapport.txt`** that names, one line per file,
   each manifest that used a removed API, in the form
   **`<file>;<removed API>;<replacement API>`**, for example
   `example.yaml;batch/v1beta1;batch/v1`. The files that used no removed API
   do not appear in it. **Blocking requirement.**
2. **All** the manifests of the repository are still there, and the API
   server **accepts them all**. A file is migrated, never deleted.
   **Blocking requirement.**
3. The migrated repository is **applied**: `kubectl diff` on the repository
   finds no gap.
4. The objects describe **exactly** what the inherited manifests described:
   same values, same targets. A migration changes the API, not the intent.
5. The `registre` Deployment runs with its two replicas.

## 🧭 Useful landmarks

Some removed APIs have a replacement whose fields do not have quite the same
shape.

## ✅ How you will know it works

The tests check the report against the files, submit each file to the API
server, run `kubectl diff` again, then compare the objects with what the
original manifests described. The files in a removed API are drawn at random
during the preparation. The pass mark is 80%, and both blocking requirements
must be met.

```bash
dsoxlab check k8s-challenge-migrer-les-api-retirees
```
