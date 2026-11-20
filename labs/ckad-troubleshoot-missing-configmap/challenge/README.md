# Challenge: A Pod blocked by a ConfigMap that does not exist

## 📍 The situation

In the **`lab`** namespace, the **`broken-app`** Pod was delivered an hour ago,
and it still has not started. `kubectl logs` returns nothing: there is not even
a container to ask. The application reads a configuration file at startup,
**`/config/settings.conf`**, then serves web pages.

The colleague who delivered it is on holiday. Its manifest is in the cluster;
its configuration, it seems, is not.

## 🎯 What you must obtain

1. The cause of the blockage, read in the Pod's **events**, recorded in
   **`~/broken-app/cause.txt`** **before any repair**: what the Pod waits for,
   by its name, and that it is missing. After that, leave this file alone.
2. The missing resource created, with the key **`settings.conf`** whose content
   holds the line `mode=production`.
3. The `broken-app` Pod **`Running`**, without you creating it again:
   Kubernetes tries again on its own as soon as what was missing appears.
4. The application **serves**: its page answers over HTTP.

## 🧭 Useful landmarks

A Pod in `ContainerCreating` that does not move has no logs: the container does
not exist yet. What keeps it from starting is told in its events, at the bottom
of `kubectl describe pod`, with the name of what is missing.

A volume that names a missing ConfigMap blocks the Pod for as long as it takes,
and unblocks it as soon as the ConfigMap exists: no need to delete it.

## ✅ How you will know it works

The tests read your record and its date, the ConfigMap, the state of the Pod,
and query the application from the node.

```bash
dsoxlab check ckad-troubleshoot-missing-configmap
```
