# Challenge: Three probes on one Pod: startup, liveness, readiness

## 📍 The situation

The **`probed-app`** application in the **`lab`** namespace is a web server,
image `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`, that answers on port 80. It has two known
defects: it sometimes **takes a long time to start**, up to a minute, and it
sometimes **freezes** without dying. With no probes, Kubernetes thinks it is
healthy in both cases, and sends traffic to it.

The team wants all three probes, each one for what it does best.

## 🎯 What you must obtain

1. A Pod **`probed-app`** in `lab`, with that image, that declares its
   port 80.
2. A **startup** probe over HTTP on that port, that allows a slow start: at
   least **one minute** of failures in a row before it gives up.
3. A **liveness** probe over HTTP on that port, that restarts the container
   when it no longer answers.
4. A **readiness** probe over HTTP on that port, that takes the Pod out of
   traffic as long as it does not answer.
5. The Pod is **`Running`** and **`Ready`**, with no restart: that is the
   proof that all three probes find what they look for.

## 🧭 Useful landmarks

An HTTP probe aimed at a wrong path or a wrong port fails without a word: the
Pod stays `Running`, but never becomes `Ready`, or restarts in a loop.
`kubectl describe pod` reports every probe failure in its events.

The tolerance of a probe is a product: the number of failures allowed times
the interval between two tries.

## ✅ How you will know it works

The tests read the three probes in the Pod definition, then its state:
`Ready`, with no restart.

```bash
dsoxlab check ckad-probes-all-types
```
