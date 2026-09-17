# Have the cluster itself refuse an unpinned image, with no webhook

## The situation

The **`production`** namespace accepts any image, including ones designated by a
plain **tag**. But a tag is only a name: it can be redirected to different
content without anything changing in the manifest, and the restarted Pod will
then pull something other than what was reviewed.

A neighbouring lab had you pin an image. This one asks for the operator's move,
which no longer relies on everyone's discipline: have the cluster **refuse**
what is not pinned.

A **`conforme`** Pod already runs in that namespace, pinned by its digest.
Leave it alone: it is there to check your policy does not block everything.

## What you must achieve

1. Creating a Pod in `production` whose image is designated by a **tag** is
   **refused**.

2. Creating a Pod whose image is **pinned by its digest** remains **accepted**.

3. The refusal comes from the **cluster itself**, with no extra component to
   install or keep alive.

4. Other namespaces are unaffected, starting with the system ones, whose images
   are not pinned.

## Useful bearings

What you must create is **native** and evaluated by the API server. `kubectl
api-resources --api-group=admissionregistration.k8s.io` lists them.

You need **two**: the rule, and what says **where** it applies. The first one
alone is a perfectly valid object that acts on nothing.

The rule is written in **CEL**. To walk a Pod's containers, one form requires
**all** of them to satisfy the condition, another requires **at least one** to.
They do not protect against the same thing.

On the binding side, two fields decide everything: the one choosing what
happens to violations, where two values out of three **let through**, and the
one restricting scope. Unrestricted, the policy would cover the **whole**
cluster.

Every namespace carries a label Kubernetes sets itself, equal to its name.

Give the API server a few seconds before concluding.

## How you will know it works

The last test really creates **both** Pods, one by tag and one by digest, and
checks the first is refused and the second accepted. Re-reading your policy
would prove nothing: a rule with no binding acts on nothing, and a binding that
merely warns lets through.

```bash
dsoxlab check cks-validating-admission-policy
```
