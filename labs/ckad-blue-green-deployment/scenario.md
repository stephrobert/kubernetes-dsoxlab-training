# Switch traffic from one version to the other: blue-green

## The situation

In the **`lab`** namespace, the team wants to ship a new version of its
application with no downtime at all and with an instant rollback. The method
they picked: two versions running **at the same time**, `blue` in production
and `green` ready to take over, and a single Service, **`app-prod`**, that
decides which one receives the traffic.

So that the switch can be seen, each version answers with its own name. A Pod
named **`client`** is there to query it.

## What you must achieve

1. A Deployment **`app-blue`** with 2 replicas, whose Pods carry the labels
   `app=myapp` and `version=blue`, and answer `blue` over HTTP on port 8080.

2. A Deployment **`app-green`** with 2 replicas, labels `app=myapp` and
   `version=green`, answering `green` on the same port.

3. A Service **`app-prod`**, port 8080, pointing at the blue version first.

4. The switch: `app-prod` points at the green version. Its endpoints are
   exactly the green Pods, and from `client`, **every** request to
   `http://app-prod:8080/` answers `green`.

## Useful bearings

A server that answers with its own name fits in one line of busybox: `httpd -f`
serves a directory, and an `echo` into `index.html` before starting it is
enough.

A Service selector can be changed in place, and the endpoints follow within a
few seconds: that is the whole switch, and it is also the rollback.

## How you will know it works

The tests read both Deployments, the Service selector and its endpoints, and
make several requests from `client`.

```bash
dsoxlab check ckad-blue-green-deployment
```
