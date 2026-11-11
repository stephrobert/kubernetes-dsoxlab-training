# Expose a Deployment through a ClusterIP Service

## The situation

In the **`lab`** namespace, the team wants a web server in **three replicas**,
reachable by the other applications of the cluster under a stable name,
**`web-svc`**, whichever Pod answers. To check the spread, each Pod must answer
with **its own name**.

A Pod named **`client`** is there to query the Service. It is the lab's
measuring instrument, not part of the work: leave it in place. If you delete
it, `dsoxlab reset ckad-expose-service` puts it back.

## What you must achieve

1. A Deployment **`web`** in `lab`, **three replicas**, image
   **`busybox:1.38.0`** (the tests read the image of the running Pods), where
   each Pod serves **its own hostname** over HTTP on port **8080**. Its Pods
   carry the label **`app=web`**.

   The three replicas must be **available**: a container whose command exits
   right away restarts in a loop and never becomes available.

2. A Service **`web-svc`** of type **ClusterIP**, port **80**, pointing at port
   **8080** of the `app=web` Pods. The target port may be written as the
   number `8080` or as the **name of a `containerPort` whose value is 8080**:
   both are accepted.

3. The Service must have **exactly three ready endpoints**. No other Pod of the
   namespace may carry the label `app=web`: a stray Pod from an earlier attempt
   enters the Service too, and makes a fourth endpoint appear.

4. From `client`, `http://web-svc/` answers to **ten requests out of ten**, every
   answer is the name of a **Pod that really exists**, and over those ten
   requests **at least two different Pods** answer.

   Each Pod is also queried on its own `127.0.0.1:8080` and must answer **its
   own name**: serving an invented identifier, even one that looks like a Pod
   name, is refused.

## Useful bearings

A server that answers with its hostname fits in one busybox command: write
`hostname` into a file of a directory, then serve that directory with `httpd`
in the foreground. The flags that matter are **`-f`** (stay in the foreground,
otherwise the container exits), **`-p 8080`** (the port the exercise asks for,
`httpd` listens on 80 by default) and **`-h <directory>`** (the directory to
serve). Inside a Pod, the hostname is the Pod name.

`kubectl expose deployment` creates the Service in a single command, if you
tell it the port and the target port.

## How you will know it works

Eleven criteria, one per state asked above: the Deployment and its Pods, the
Service and its endpoints, then ten requests from `client` plus one direct
request to each Pod.

```bash
dsoxlab check ckad-expose-service
```
