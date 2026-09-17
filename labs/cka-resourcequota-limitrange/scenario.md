# Cap a namespace without blocking those who forget to declare

## The situation

The **`equipe-produit`** namespace was opened for a team, and it has **neither a ceiling
nor defaults**.

Two consequences, and one is not immediately visible. The team can claim the
whole cluster, nobody will stop them. And their developers deploy containers
declaring no resources at all, which the scheduler then places blind.

An application, the **`catalogue`** Deployment, already runs in that namespace.
It requests 50m of CPU and 32Mi of memory.

## What you must achieve

1. A Pod requesting **64 CPU** is **refused at creation**. Today it is accepted
   and merely waits for room that does not exist: nobody refused it.

2. A Pod declaring **no** resources is **accepted**, and comes back with
   `requests` **and** `limits` it never wrote.

3. The `catalogue` Deployment keeps running.

## Useful bearings

Two objects are needed, and they do not do the same thing. One caps the
**total** consumed by the namespace. The other supplies default values to every
container declaring none, **on arrival**.

Creating the first one **alone** breaks the namespace, and that is this lab's
trap: as soon as a cap applies to `requests`, any Pod declaring none becomes
invalid, the API being unable to count what is not declared.

On the defaults side, **two distinct fields** must be filled: one feeds what the
container requests, the other what it may not exceed. They do not share a name,
and you need both.

Too low a cap would keep `catalogue` from being scheduled again on its next
restart. That would be an outage, not resource control.

## How you will know it works

Both tests are **active** proofs: they really create the two Pods, the
extravagant one and the silent one, and observe the first being refused and the
second being completed. Re-reading the objects would prove nothing: a cap that
does not apply to the right resources is a perfectly valid object that caps
nothing.

```bash
dsoxlab check cka-resourcequota-limitrange
```
