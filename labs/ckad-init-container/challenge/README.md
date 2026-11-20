# Challenge: Repair the gatekeeper of an application

## 📍 The situation

In the **`lab`** namespace, the **`facturation`** Pod computes invoices with
the prices of the pricing service. That service is exposed by the
**`tarifs-svc`** Service. Without it, invoicing produces zero amounts.

An init container, **`attendre-tarifs`**, was meant to keep `facturation`
from starting as long as the pricing service does not answer. Yet
`facturation` already runs, while nothing answers behind `tarifs-svc`. The
gatekeeper held nothing back.

## 🎯 What you must obtain

1. A Pod **`facturation`** in `lab`, whose init container
   **`attendre-tarifs`** waits for a real answer from `tarifs-svc`, then a
   main container **`main`**, image
   `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`.
2. As long as nothing answers behind `tarifs-svc`, `facturation` stays in
   **`Init`**: see it for yourself.
3. A Pod **`tarifs`** in `lab`, same nginx image, that `tarifs-svc` selects.
4. Once `tarifs` is ready, the init container ends and `facturation` goes
   `Running` without you doing anything else.

## 🧭 Useful landmarks

Start by reading what the current gatekeeper does and how the Service is
declared: its selector and its port. `kubectl describe` shows both.

You cannot change the init containers of an existing Pod: it must be
recreated.

A bounded wait is better than an endless one: a gatekeeper that gives up
after a number of tries puts the Pod in error, which shows, and Kubernetes
restarts it. An `until` loop with `wget` makes a good gatekeeper, in the
image
`busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`.

## ✅ How you will know it works

The tests read the definition of `facturation`, query `tarifs-svc`, and
compare the start order of the two Pods.

```bash
dsoxlab check ckad-init-container
```
