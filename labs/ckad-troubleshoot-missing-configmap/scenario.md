# A Pod blocked by a ConfigMap that does not exist

## The situation

In the **`lab`** namespace, the Pod **`broken-app`** was delivered an hour
ago, and it still has not started. `kubectl logs` returns nothing: there is
not even a container to query. The application reads a configuration file at
startup, **`/config/settings.conf`**, then serves web pages.

The colleague who delivered it has left on holiday. Its manifest is in the
cluster; its configuration, apparently, is not.

## What you must achieve

1. The cause of the blockage, read in the Pod's **events**.

2. The missing resource created, with the key **`settings.conf`** whose
   content carries the line `mode=production`.

3. The Pod `broken-app` **`Running`**, without your having recreated it:
   Kubernetes retries on its own as soon as what was missing appears.

4. The application **serves**: its page answers over HTTP.

## Useful bearings

A Pod in `ContainerCreating` that does not move has no logs: the container
does not exist yet. What keeps it from being born is told in its events, at
the bottom of `kubectl describe pod`, with the name of what is missing.

A volume that references an absent ConfigMap blocks the Pod indefinitely,
and unblocks it as soon as the ConfigMap exists: no need to delete it.

## How you will know it works

The tests read the ConfigMap, the state of the Pod, and query the
application from the node.

```bash
dsoxlab check ckad-troubleshoot-missing-configmap
```
