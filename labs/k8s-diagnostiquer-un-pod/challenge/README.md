# Challenge: Diagnose two failing Pods

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. In the **`pods-en-panne`** namespace, two Pods created by
hand do not work:

- **`image-fausse`** never started;
- **`plante`** starts, then stops, again and again.

The **`~/pods-en-panne/releve.txt`** file waits for what you read in the
cluster.

## 🎯 What you must obtain

1. After **`raison-image-fausse`**: the reason why the `image-fausse`
   container is waiting.

2. After **`code-sortie-plante`**: the exit code of the `plante` container
   when it last stopped.

3. **`image-fausse` runs**, on the **`nginx:1.30.5`** image, and it is **the
   same Pod** as at the start: you corrected its image without recreating it.

4. **`plante` runs without restarting**, still named `plante` and on the same
   `busybox:1.38.0` image. Only its command changed, for a command that keeps
   running (a one-hour wait, for example).

## 🧭 Useful landmarks

Start with the overview, then go down into the detail.
`kubectl get pods -n pods-en-panne` shows the `STATUS` and `RESTARTS` columns.
`kubectl describe pod` shows the container's state, and its events at the end
give the cause. The exit code of the last stop is stored in the Pod's state.

The two repairs are not done the same way, and that is the heart of the lab.
Once created, a Pod hardly changes anymore. **Its image** is one of the few
fields you can change on an existing Pod. **Its command** is not: to change it,
fetch the Pod's YAML file, correct it, then recreate the Pod under the same
name. Recreating `image-fausse`, or keeping `plante` under another name, does
not answer the request.

## ✅ How you will know it is right

The tests read your file, then the state of both Pods in the cluster. They also
check that `image-fausse` is indeed the starting Pod.

```bash
dsoxlab check k8s-diagnostiquer-un-pod
```
