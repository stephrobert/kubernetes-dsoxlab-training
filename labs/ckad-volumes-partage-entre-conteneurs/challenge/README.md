# Challenge: Let one container read what another writes, and nothing else

## 📍 The situation

In the **`journalisation`** namespace, the **`collecteur`** Pod has two
containers.

The **`producteur`** container writes a line every five seconds into
`/var/trace/messages`. The **`lecteur`** container should read that file back
to send it elsewhere, but it finds nothing.

Both are in the same Pod. They share the network and the IP address, but each
one keeps the filesystem of its own image.

## 🎯 What you must obtain

1. The `lecteur` container sees the `/var/trace/messages` file, and it is not
   empty.
2. What the producer writes **elsewhere**, outside that directory, stays
   invisible to the reader.
3. The Pod is still called `collecteur`, and both containers keep their names.

Nothing must be kept once the Pod is gone: the point is to pass files along,
not to store them.

## 🧭 Useful landmarks

What you must add is declared at **two** levels: the object itself, once for
the Pod, then its mount in each container that must see it. Declaring without
mounting does nothing, and mounting on one side only shares nothing.

The type that fits here **is born with the Pod and dies with it**. It is not
there to keep things, but to pass them along, and it needs no storage prepared
in advance.

The mount path must be the same on both sides.

You cannot change a Pod's volumes while it runs: it must be created again.

## ✅ How you will know it works

The last test checks **both sides**. It checks that the file crosses, then it
makes the producer write **outside** the shared directory and checks that this
second file **does not cross**. Mounting the volume too high, on the root or on
`/var`, would pass the first half and fail the second.

```bash
dsoxlab check ckad-volumes-partage-entre-conteneurs
```
