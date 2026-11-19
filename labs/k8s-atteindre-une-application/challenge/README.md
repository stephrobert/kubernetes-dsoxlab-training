# Challenge: Reach an application: expose and port-forward

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. In the **`acces`** namespace, the **`echo`** Deployment runs
two agnhost Pods listening on **port 8080**. On the `/hostname` path, each Pod
answers its own name. No Service exposes them yet.

The file **`~/acces/releve.txt`** is waiting for what you will read through the
tunnel.

## 🎯 What you must obtain

1. A Service **`echo`** exposes the Deployment on **port 80**, to **port 8080**
   of the Pods.

2. The Service counts **both Pods** as ready endpoints.

3. A **`kubectl port-forward` tunnel to the Service** `echo` listens on local
   port **`18080`**. It is **still open** when you run the check.

4. After **`pod-du-tunnel`**, in the file: the name of the Pod that answers you
   through **this** tunnel.

## 🧭 Useful landmarks

`kubectl expose` picks values for you: it copies the Deployment selector, and
without `--target-port`, it reuses the value of `--port`. First look at the
manifest it would write, without creating anything.

A `kubectl port-forward` tunnel is a process, not an object: it lives as long as
the command runs. Start it in the background, with its messages in a log, query
it from the machine, and leave it running until the check: the checker goes
through it too. Ports read "local, then remote". Towards a Service, the tunnel
attaches to a single Pod, picked at start-up.

## ✅ How you will know it is right

The tests read the Service and its EndpointSlices. They look for your tunnel
among the processes of the machine, send a request through port 18080, and
compare your file with the Pod that answers. A name copied from
`kubectl get pods` is not enough.

```bash
dsoxlab check k8s-atteindre-une-application
```
