# Record who reads Secrets, and only the metadata of everything else

## The situation

The cluster keeps **no trace** of who reads what. A Secret read by a
compromised account leaves nothing behind: not the time, not the author, not
even the fact that the read happened.

In the **`coffre`** namespace, the **`dossier-medical`** Secret is waiting to
be read. The compliance team wants to be able to answer "who read this Secret,
and when?", without copying the cluster's entire traffic to disk.

## What you must achieve

1. The API server applies an **audit policy** that tells two cases apart:
   accesses to **Secrets** are recorded with the **full body** of the request
   and the response; **everything else** only at the **metadata** level.

2. The audit log is written to a file **on the node**, at a location that
   survives a restart of the API server Pod.

3. **The API server still answers** once the change is made. That is the part
   most often got wrong, and this lab measures it.

4. The log **actually** contains the trace of a Secret being read, at the right
   level, and that of an ordinary read, at metadata level only.

## Useful bearings

The audit policy is **not a Kubernetes object**. It is a file on the node,
which the API server reads **at startup**: it must therefore restart to pick it
up, and the kubelet takes care of that as soon as the static manifest changes.

The API server is a **Pod**. It only sees what you show it of the node: giving
a file path in a flag is not enough, that path must also be mounted inside the
container. This is the cause of nearly every failure on this subject, and
`crictl logs` on the `kube-apiserver` container names it in one line.

A policy is an **ordered list** of rules. The API server keeps the **first**
one that matches the request, and ignores the rest.

Four levels exist, from quietest to most verbose: `None`, `Metadata`,
`Request`, `RequestResponse`.

## How you will know it works

The tests read the node and the cluster. The last one triggers two real
operations, one sensitive and one ordinary, then reads back **what the cluster
has just written**. A policy that recorded everything at the maximum level
fails just as much as a missing one.

```bash
dsoxlab check cks-audit-log-policy
```
