# Switch traffic from one version to the other: blue-green

## The situation

In the **`lab`** namespace, the team wants to ship a new version of its
application with no downtime at all and with an instant rollback. The method
they picked: two versions running **at the same time**, `blue` in production
and `green` ready to take over, and a single Service, **`app-prod`**, that
decides which one receives the traffic.

So that the switch can be seen, each version answers with its own name. A Pod
named **`client`** is already there to query it: it is the measuring
instrument of this lab, not part of what you have to build, so leave it
alone.

## What you must achieve

1. A Deployment **`app-blue`** with 2 replicas available, whose Pods carry the
   labels `app=myapp` and `version=blue`, and **each of which answers `blue`
   over HTTP on port 8080**.

2. A Deployment **`app-green`** with 2 replicas available, labels `app=myapp`
   and `version=green`, each Pod answering `green` on the same port.

3. A Service **`app-prod`** listening on port **8080**, whose selector names
   **both** `app=myapp` and `version=green`.

4. The endpoints of `app-prod` are **exactly** the ready green Pods, and from
   `client`, **every** request to `http://app-prod:8080/` answers `green`.

Read item 1 again: it is measured **after** the switch. `app-blue` must still
be standing and still answering `blue` when you run the check. That is not a
detail, it is the whole point of blue-green: the rollback is instant only
because the old version never stopped serving.

## Useful bearings

A server that answers with its own name fits in one line of busybox: `httpd -f`
serves a directory, and an `echo` into `index.html` before starting it is
enough. A container that only sleeps carries the right labels and serves
nothing.

In real life, you create `app-prod` pointing at blue, you watch it, then you
switch it to green. The tests measure the end state, so nothing forces you
through that intermediate step; the trace the method leaves is blue still
standing and still serving.

A Service selector can be changed in place, and the endpoints follow within a
few seconds: that is the whole switch, and it is also the rollback.

## How you will know it works

The tests read both Deployments and the labels of their Pods, query **each
Pod on its own address** to check it serves its version, then read the
Service selector and its endpoints, and finally make six requests from
`client`.

```bash
dsoxlab check ckad-blue-green-deployment
```
