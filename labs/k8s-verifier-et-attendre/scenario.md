# Preview with diff, wait with wait

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the
**`paiements`** namespace runs **`facturation`** at version 1, on 2 replicas. Its
versioned folder, **`~/deploiement/`**, holds `facturation.yaml` and
**`migration.yaml`**, a migration Job that was never applied.

Version 2:

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## What you must obtain

1. In the folder, `facturation.yaml` describes **version 2**, and **the cluster
   matches the folder**: comparing it with the cluster finds no difference.
2. **Every Pod** of `facturation` runs version 2 and is Ready, and the
   **`migration` Job is complete**.
3. **`~/deploiement/releve.txt`** gives the exit code of `kubectl diff` in the
   three cases, as you measured it:

   ```text
   aucune-difference: <code>
   differences: <code>
   erreur: <code>
   ```

4. **`~/deploiement/deployer.sh`**, executable, takes a folder as argument,
   compares that folder with the cluster, applies if there are differences, then
   waits for the end of the rollout. It **exits with 0** when nothing differs, and
   it **stops on error, without applying anything**, when `kubectl diff` cannot
   compare the folder.

## Useful landmarks

Preview every change before applying it. The exit code of `kubectl diff` does not
mean what one thinks: measure it, do not assume it. A `set -e` script that ignores
this quirk stops at the wrong moment.

A Deployment can say Available while old Pods still serve: wait for the real end
of the rollout, not only for its availability. Wait for the end of a Job without
getting stuck if it fails.

A `kubectl apply` on a folder where one object is refused still applies the
others.

## How you will know it works

The tests compare your folder with the cluster, read the record, check the image
of every Pod and the state of the Job, then run your script twice: on the
unchanged folder, and on a copy that holds an object refused by the server.

```bash
dsoxlab check k8s-verifier-et-attendre
```
