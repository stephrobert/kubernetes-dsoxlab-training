# Reach an application: expose and port-forward

## The situation

The kind cluster **`boutique`** runs on the machine, and your `kubectl` already
targets it. In the **`acces`** namespace, the Deployment **`echo`** runs two
agnhost Pods listening on **port 8080**. On the `/hostname` path, each Pod
answers its own name. No Service exposes them yet.

The record **`~/acces/releve.txt`** waits for what you read through the tunnel.

## What you must obtain

1. A Service **`echo`** exposes the Deployment on **port 80**, towards the
   **port 8080** of the Pods.

2. The Service counts the **two Pods** as ready endpoints.

3. **`pod-du-tunnel`** gives the name of the Pod that answered you through a
   **`kubectl port-forward` tunnel to the Service**.

## Useful landmarks

`kubectl expose` does several things for you: it copies the selector of the
Deployment, and without `--target-port` it reuses the value of `--port`.
Generate the manifest first without creating anything to check what it will
write.

A `kubectl port-forward` tunnel is a process, not an object: it lives as long
as the command runs. Start it in the background with its output in a log,
query it from the machine, then stop it. Ports read "local, then remote".
Towards a Service, the tunnel attaches to a single Pod, chosen at launch.

## How you will know it is right

The tests read the Service and its EndpointSlices, then compare your record
with the echo Pods that exist.

```bash
dsoxlab check k8s-atteindre-une-application
```
