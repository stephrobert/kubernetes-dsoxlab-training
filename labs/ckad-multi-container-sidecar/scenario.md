# A native sidecar that tails the application logs

## The situation

An old application, in the **`lab`** namespace, does not write its logs to
standard output: it writes them to a file,
**`/var/log/app/output.log`**, one line per second. `kubectl logs` therefore
shows nothing, and the operations team wants those lines where everyone
reads them.

Rather than modify the application, you attach a **sidecar** to it that
tails the file and copies it to its own standard output. Since Kubernetes
1.33, a sidecar is declared in a specific way, which guarantees that it
starts before the application and stops after it.

## What you must achieve

1. A Pod **`app-with-sidecar`** in `lab`, with a volume **`logs`** of type
   `emptyDir`.

2. A main container **`app`**, image `busybox:1.36`, that writes one line per
   second into `/var/log/app/output.log`, on that volume.

3. A **native sidecar** named **`log-shipper`**, same image, declared the way
   it should be since 1.33, that tails that file continuously and copies it
   to its standard output.

4. The Pod is running, the file fills up, and `kubectl logs` on the sidecar
   shows the application lines.

## Useful bearings

A native sidecar is not a second container under `containers`: it is an init
container given a `restartPolicy`. That detail is what changes everything,
and it is what the exam expects.

The two containers share nothing by default, not even a directory: the
volume must be mounted in both.

## How you will know it works

The tests read the Pod definition, enter the container to read the file, and
read the sidecar logs.

```bash
dsoxlab check ckad-multi-container-sidecar
```
