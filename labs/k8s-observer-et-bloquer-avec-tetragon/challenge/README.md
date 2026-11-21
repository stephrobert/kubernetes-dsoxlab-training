# Challenge: Observe a sensitive file being read with Tetragon, then block it

## The situation

In the **`comptes`** namespace, an API key is mounted from the `cle-api`
Secret, at **`/etc/comptes/cle`**, in two Pods: **`rapport`** and
**`vitrine`**. The security team suspects one of them of reading the key
regularly, for no reason. It wants to know which one and with which tool, then
prevent any read of the key.

**Tetragon 1.8.0** is installed on the cluster, with one agent per node.

## What you must achieve

1. Tetragon **sees** the reads of the key: each opening of a file under
   `/etc/comptes/` produces an event, with the Pod and the binary.

2. A ConfigMap **`constat-tetragon`**, in the `comptes` namespace, names:
   - `pod`: the Pod that reads the key on its own;
   - `binaire`: the binary that reads it, as Tetragon shows it, as a full path
     (for example `/bin/example`).

3. Any read of the key is then **blocked**: the process is killed.

4. The blocking **only targets the key**: the Pods' other files can still be
   read.

## Useful bearings

Tetragon writes each event as JSON in the `export-stdout` container of its
agent. An agent only sees the Pods of **its** node.

`tetra getevents`, run inside an agent, only shows upcoming events, not past
ones.

## How you will know it works

The tests trigger a read of the key in `vitrine` themselves, then look for the
event at the agent of its node. The binary that reads the key is drawn at
random during preparation: only Tetragon's event reveals it.

```bash
dsoxlab check k8s-observer-et-bloquer-avec-tetragon
```
