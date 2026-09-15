# Three probes on one Pod: startup, liveness, readiness

## The situation

The **`probed-app`** application in the **`lab`** namespace is a web server,
image `nginx:1.27-alpine`, answering on port 80. It has two known defects: it
sometimes **takes a long time to start**, up to a minute, and it sometimes
**freezes** without dying. With no probes, Kubernetes believes it healthy in
both cases, and sends traffic to it.

The team wants all three probes, each for what it is good at.

## What you must achieve

1. A Pod **`probed-app`** in `lab`, with that image, declaring its port 80.

2. A **startup** probe over HTTP on that port, tolerating a slow start: at
   least **one minute** of consecutive failures before it gives up.

3. A **liveness** probe over HTTP on that port, restarting the container when
   it stops answering.

4. A **readiness** probe over HTTP on that port, pulling the Pod out of
   traffic for as long as it does not answer.

5. The Pod is **`Running`** and **`Ready`**, with no restart: that is the
   proof that all three probes find what they are looking for.

## Useful bearings

An HTTP probe aimed at a wrong path or a wrong port fails silently: the Pod
stays `Running`, but never becomes `Ready`, or restarts in a loop.
`kubectl describe pod` reports every probe failure in its events.

The tolerance of a probe is a product: the number of failures allowed
multiplied by the interval between two attempts.

## How you will know it works

The tests read the three probes in the Pod definition, then its state:
`Ready`, with no restart.

```bash
dsoxlab check ckad-probes-all-types
```
