# Keep data beyond the life of a Pod

## The situation

On the kind cluster **`lab`**, which your `kubectl` already targets, the
archives team wants its application **`registre`** to keep its data when its Pod
goes away. It lives in the namespace **`archives`**. A claim is already there,
**`journal-ancien`**, set up by another team: it has stayed **Pending** since it
was created. The directory **`~/archives/`** is empty. The requirements say what
to obtain, not how.

The application image:

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## The requirements

1. A StorageClass **`conserve`**, served by the provisioner the cluster already
   uses for its default class. The claim **`registre-donnees`**, in `archives`,
   names it and requests **`256Mi`** in **`ReadWriteOnce`**. It is **Bound** to a
   volume this provisioner **created for it**: no volume prepared in advance.
2. A Deployment **`registre`**, with one replica, mounts `registre-donnees` on
   **`/var/lib/registre`**. The witness file **`/var/lib/registre/temoin.txt`**
   holds, on its **first line**, the **name of the Pod that wrote it**.
3. Delete that Pod. The Pod the Deployment recreates reads the witness again
   **intact**: same content, never rewritten since.
4. The volume of `registre-donnees` keeps its data if the claim goes away: its
   **reclaim policy** is **`Retain`**, read on the PersistentVolume.
5. **Before any correction**, write in **`~/archives/cause.txt`** why
   **`journal-ancien`** stays Pending: what it asks for without finding it, by
   its name, and that it is missing. Then leave it alone.
6. **`journal-ancien`** is **Bound**, and still requests **`100Mi`**.

## How you are graded

The challenge is graded on the **final state** of the cluster and of your files,
never on the commands typed. The **six requirements all weigh the same**. The
threshold is **70 out of 100**, and **three requirements are blocking**: they
must pass whatever the total. They are the volume created for
`registre-donnees` by the class (requirement 1), the witness read again intact
(requirement 3), and the cause recorded before the correction (requirement 5).

Four **hints** are offered, and each one takes points off the scale before the
grade is computed: 2, 3, 5 then 5, 15 at most. Without a hint, six requirements
give 100 and five give 83. With all four, six requirements give 85 and five give
71, still above the threshold. Four requirements are never enough: 67 at best.

No procedure is given: the lessons of the module taught everything.

```bash
dsoxlab check  k8s-challenge-donnees-qui-survivent
dsoxlab submit k8s-challenge-donnees-qui-survivent
```
