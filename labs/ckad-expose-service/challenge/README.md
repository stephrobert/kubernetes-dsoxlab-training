# Challenge: Expose a Deployment through a ClusterIP Service

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. In the **`lab`** namespace, the team wants an internal contacts service in
**four copies**. The other applications of the cluster must reach it under a
stable name, **`contacts-svc`**, on port **8081**, whichever Pod answers. To
check that the requests are spread, each Pod must answer **its own name**.

A **`client`** Pod is there to query the Service. It is used to measure the
result: leave it in place. If you delete it,
`dsoxlab reset ckad-expose-service` puts it back.

## 🎯 What you must obtain

1. A Deployment **`contacts`** in `lab`, with **four Pods** and the image
   **`busybox:1.38.0`**. Each Pod serves **its own hostname** over HTTP on
   port **9090**, and carries the label **`app=contacts`**. The four Pods must
   be **available**: a container whose command ends right away restarts in a
   loop and never becomes available.

2. A Service **`contacts-svc`** of type **ClusterIP**, on port **8081**, which
   sends to port **9090** of the `app=contacts` Pods. The target port can be
   written with the number `9090`, or with the **name of a `containerPort`
   worth 9090**: both are accepted.

3. The Service has **exactly four ready endpoints**. No other Pod of the
   namespace may carry the label `app=contacts`, otherwise it enters the
   Service too and makes a fifth endpoint.

4. From `client`, `http://contacts-svc:8081/` answers **ten requests out of
   ten**. Each answer is the name of a **Pod that really exists**, and **at
   least two different Pods** answer over those ten requests. Each Pod is also
   queried on its own `127.0.0.1:9090`, and must answer **its own name**: a
   made-up name, even if it looks like a Pod name, is refused.

## 🧭 Useful landmarks

A server that answers its hostname fits in one busybox command: write the
output of `hostname` into a file, then serve the directory with `httpd`. Three
options matter:

- **`-f`**: stay in the foreground, otherwise the container stops;
- **`-p 9090`**: the requested port, as `httpd` listens on 80 by default;
- **`-h <directory>`**: the directory to serve.

In a Pod, the hostname is the Pod name.

`kubectl expose deployment` creates the Service in one command, if you give it
the port and the target port. Since the Service does not listen on 80, a
request must name its port.

## ✅ How you will know it is right

Eleven criteria, one per requirement asked above: the Deployment and its Pods,
the Service and its endpoints, then ten requests from `client` and one direct
request to each Pod.

```bash
dsoxlab check ckad-expose-service
```
