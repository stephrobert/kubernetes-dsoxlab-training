# Let one container read what another writes, and nothing else

## The situation

In the **`journalisation`** namespace, the **`collecteur`** Pod carries two containers.

The **`producteur`** container writes a line every five seconds into
`/var/trace/messages`. The **`lecteur`** container is supposed to read that file
back and ship it elsewhere, and it finds nothing.

Both are in the same Pod. They share the network and the IP address, but each
keeps the filesystem of its own image.

## What you must achieve

1. The `lecteur` container sees the `/var/trace/messages` file, and it is not
   empty.

2. What the producer writes **elsewhere**, outside that directory, stays
   invisible to the reader.

3. The Pod is still called `collecteur`, and both containers keep their names.

Nothing must survive the Pod's disappearance: this is about passing along, not
storing.

## Useful bearings

What you must add is declared at **two** levels: the object itself, once for the
Pod, then its mount in each container that must see it. Declaring without
mounting does nothing, and mounting on one side only shares nothing.

The type that fits here is **born with the Pod and dies with it**. It is not
there to keep, but to pass along, and it requires no storage prepared in
advance.

The mount path must be the same on both sides.

A Pod's volumes cannot be changed in place: it must be recreated.

## How you will know it works

The last test exercises **both sides**. It checks the file crosses, then makes
the producer write **outside** the shared directory and checks that second file
**does not cross**. Mounting the volume too high, on the root or on `/var`,
would pass the first half and fail the second.

```bash
dsoxlab check ckad-volumes-partage-entre-conteneurs
```
