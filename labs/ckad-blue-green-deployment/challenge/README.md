# Challenge: Ship a new version with no downtime, blue-green style

## 📍 The situation

You are on the control plane of the kubeadm cluster, and your kubectl is
configured. In the **`lab`** namespace, the team wants to ship a new version of
its application with no downtime at all, and to be able to roll back at once.

The chosen method:

- two versions run **at the same time**: `blue` in production, `green` ready to
  take over;
- a single Service, **`app-prod`**, decides which one receives the traffic.

So that the switch can be seen, each version answers its name. A **`client`**
Pod is already there to query the Service. It is used to measure the result:
leave it alone.

## 🎯 What you must obtain

1. A Deployment **`app-blue`** with 2 available Pods. Its Pods have the labels
   `app=myapp` and `version=blue`, and **each one answers `blue` over HTTP on
   port 8080**.

2. A Deployment **`app-green`** with 2 available Pods, labels `app=myapp` and
   `version=green`. Each one answers `green`, on the same port.

3. A Service **`app-prod`** listening on port **8080**. Its selector asks for
   **both** `app=myapp` and `version=green`.

4. The endpoints of `app-prod` are **exactly** the ready green Pods. From
   `client`, **every** request to `http://app-prod:8080/` answers `green`.

Watch out for item 1: it is checked **after** the switch. `app-blue` must
therefore still be running and answering `blue` when the check runs. That is
the very principle of blue-green: the rollback is immediate only because the
old version never stopped serving.

## 🧭 Useful landmarks

A server that answers its name fits in one line of busybox: an `echo` into
`index.html`, then `httpd -f` to serve the directory. A container that only
sleeps has the right labels, but serves nothing.

In real life, you first create `app-prod` pointing at blue, you watch it, then
you switch it to green. The tests only look at the end state: you do not have
to go through the blue step. But blue must stay up and keep answering.

A Service selector can be changed without recreating it, and the endpoints
follow within a few seconds. That is the whole switch, and it is also the
rollback.

## ✅ How you will know it is right

The tests read both Deployments and the labels of their Pods. They query **each
Pod on its own address**, to check that it answers its version. They then read
the Service selector and its endpoints, and send six requests from `client`.

```bash
dsoxlab check ckad-blue-green-deployment
```
