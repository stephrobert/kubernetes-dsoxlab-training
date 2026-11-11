# Diagnose two failing Pods

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. In the **`pods-en-panne`** namespace, two bare Pods refuse to work:

- **`image-fausse`** has never started;
- **`plante`** starts, then stops, again and again.

The record **`~/pods-en-panne/releve.txt`** waits for what you read in the
cluster.

## What you must obtain

1. **`raison-image-fausse`** gives the reason why the container of
   `image-fausse` is waiting.

2. **`code-sortie-plante`** gives the exit code of the container of `plante`
   when it last stopped.

3. **`image-fausse` runs**, on the image **`nginx:1.30.5`**, and it is **the
   same Pod** as at the start: its image was corrected in place.

4. **`plante` runs without restarting**, still named `plante` and on the same
   image `busybox:1.38.0`: only its command changed, for a command that keeps
   running (a one-hour wait, for example).

## Useful landmarks

Always start from the overview, then go down to the detail:
`kubectl get pods -n pods-en-panne` gives the STATUS and RESTARTS columns,
`kubectl describe pod` gives the container state and, at the end of its output,
the **Events** that say the cause. A container that crashed keeps a trace of
its last stop in the Pod status, field by field.

The two repairs are not done the same way, and that is the heart of the lab. A
Pod is almost frozen once created: **its image** is one of the few fields that
change on an existing Pod. **Its command** does not: to change it, you fetch its
manifest, correct it, then recreate the Pod under the same name. Recreating
`image-fausse`, or keeping `plante` under another name, does not answer the
request.

## How you will know it is right

The tests read the record, then the state of both Pods in the cluster. The
identity of `image-fausse` is compared with the one at the start.

```bash
dsoxlab check k8s-diagnostiquer-un-pod
```
