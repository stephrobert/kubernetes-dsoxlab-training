# Get a Deployment out of CrashLoopBackOff

## The situation

In the **`production`** namespace, the **`api-server`** Deployment is supposed
to run two replicas. Since the last release, its Pods **restart in a loop**:
`kubectl get pods` shows them in `CrashLoopBackOff`, with a restart counter
climbing.

The team swears the image has not changed. They dropped the application's
configuration into the namespace, and say that "everything is there". The
team's rule is simple: an application reads its configuration at the location
given by the **`APP_CONFIG_PATH`** environment variable, and that location is
**`/etc/config`**.

## What you must achieve

1. The `api-server` Deployment has **two available replicas**.

2. No `api-server` Pod restarts in a loop any more.

3. Inside the Pods, `APP_CONFIG_PATH` is `/etc/config`, and the application
   really finds its `app.conf` file there.

4. The application **answers**: it serves its `app.conf` on its port.

The fix is made **on the Deployment**, not on the Pods: a Pod patched by hand
would be replaced at the next opportunity.

## Useful bearings

`CrashLoopBackOff` is not a cause, it is a consequence: the container starts,
stops right away, and the kubelet spaces out its restarts. The why is in what
the process wrote before it died, and in what the Deployment gives it, or does
not give it.

Look at what the namespace holds besides the Deployment.

## How you will know it works

The tests read the state of the Deployment and of its Pods, then they enter a
Pod to read the configuration file and query the application.

```bash
dsoxlab check cka-troubleshoot-crashloopbackoff
```
