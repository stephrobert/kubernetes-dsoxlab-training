# Challenge: Get inside a container with no shell using kubectl debug

## 📍 The situation

In the **`lab`** namespace, a team runs its own DNS resolver, the
**`distroless-app`** Pod. Its image is built on CoreDNS, and it is
**distroless**: a single static binary, with no shell, no `ls` and no `ps`.
That is good security practice, until the day you have to look at what happens
inside. `kubectl exec` answers that `sh` does not exist, and the logs say
nothing about what the process does.

The team asks you for the list of the processes that **really** run in that
container, seen from the inside.

## 🎯 What you must obtain

1. The `distroless-app` Pod has an ephemeral container named **`debugger`**,
   which shares the process space of the `distroless-app` container.
2. From that container, the list of processes has been written to
   **`/tmp/debug-output.txt`**: you can read in it the application's `coredns`
   process. The `debugger` container **stays alive**, so the file can be read
   again.

## 🧭 Useful landmarks

An ephemeral container is added to a running Pod, without restarting it, and
can never be removed from it. It only sees the processes of another container
if you ask for it explicitly.

The tool image does not matter, as long as it has a shell and `ps`: busybox is
enough.

## ✅ How you will know it works

The tests read the Pod definition, then read the file again in the `debugger`
container.

```bash
dsoxlab check cka-kubectl-debug
```
