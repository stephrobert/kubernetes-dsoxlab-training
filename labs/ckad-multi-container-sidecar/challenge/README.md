# Challenge: A native sidecar that follows the application logs

## 📍 The situation

An old application, in the **`lab`** namespace, does not write its logs to
standard output. It writes them to a file, **`/var/log/app/output.log`**, one
line per second. So `kubectl logs` shows nothing, and the operations team wants
those lines where everyone reads them.

Rather than change the application, you add a **sidecar** to it that follows
the file and copies it to its own standard output. A sidecar is declared in a
precise way, which guarantees that it starts before the application and stops
after it.

## 🎯 What you must obtain

1. A Pod **`app-with-sidecar`** in `lab`, with a volume **`logs`** of type
   `emptyDir`.
2. A main container **`app`**, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, that writes
   one line per second into `/var/log/app/output.log`, on that volume.
3. A **native sidecar** named **`log-shipper`**, same image, declared the way
   it should be, that follows that file continuously and copies it to its
   standard output.
4. The Pod runs, the file fills up, and `kubectl logs` on the sidecar shows the
   application's lines.

## 🧭 Useful landmarks

A native sidecar is not a second container under `containers`: it is an init
container that is given a `restartPolicy`. That detail changes everything, and
it is what the exam expects.

The two containers share nothing by default, not even a directory: the volume
must be mounted in both.

## ✅ How you will know it works

The tests read the Pod definition, go into the container to read the file, and
read the sidecar's logs.

```bash
dsoxlab check ckad-multi-container-sidecar
```
