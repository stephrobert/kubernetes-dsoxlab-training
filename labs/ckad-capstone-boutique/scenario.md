# Capstone: ship the shop, from the specification alone

## The situation

You are handed a specification, the way a team hands one over: what the
delivery must satisfy, not how to get there. Nothing below names a Kubernetes
object. Choosing them is the exercise.

Everything happens in the **`boutique`** namespace, which already exists. Two
client Pods are already running there, `frontend` and `intrus`. **Do not touch
them**: they are not part of the delivery, they are what the last requirement
is measured with.

Budget about **45 minutes**, and treat it as an exam: you may not finish
everything, and the pass mark is **66 %**. Four requirements fully satisfied
are worth more than six half done.

## What the delivery must satisfy

1. **The catalogue runs in two copies**, under the name `catalogue`, from the
   `nginxinc/nginx-unprivileged:1.27-alpine` image. If one copy disappears,
   another takes its place.

2. **The display message is configurable without rebuilding the image.** The
   container receives the text `Bienvenue dans la boutique` in the `MESSAGE`
   environment variable, and that value lives outside the Pod definition,
   under the name `catalogue-config`.

3. **The database password never appears in a manifest.** It is
   `s3cr3t-boutique`, held under the name `catalogue-db` in the `password`
   key, and the container reads it from the file `/etc/db/password`.

4. **The cluster knows when to send traffic, and when to restart.** Two checks
   on the HTTP port of the container: one decides whether a copy receives
   traffic, the other whether it must be restarted. Neither may make the Pod
   fail while nginx starts normally.

5. **The container does not run as root**, and it is the manifest that says
   so, not the image. Its user id is `101`.

6. **Only the frontend gets in.** The catalogue answers at the stable name
   `catalogue-svc` on port `80` inside the namespace. Pods labelled
   `role=frontend` may reach it; anything else in the namespace may not.

## Useful bearings

None of this hints at which object to use. These are the traps this capstone
has actually caught.

- A process that does not run as root cannot bind a port below 1024. This
  image listens on **8080**, not on 80. The name and the port in requirement
  6 are what the *client* sees, which is not necessarily what the container
  listens on.
- A network policy that allows nothing is not the same as no policy at all.
  Once a policy selects a Pod, everything it does not name is denied,
  including what used to work.
- `kubectl explain` works without network access and knows the whole schema.
  It is faster than hunting for an example.

## How you will know it is done

The tests read the state of the cluster, never the commands you typed. They
enter the container to check what it actually receives, and the last one is
the only one that proves the isolation: it opens a connection from
`frontend`, which must succeed, and from `intrus`, which must not.

```bash
dsoxlab check  ckad-capstone-boutique
dsoxlab submit ckad-capstone-boutique
```
