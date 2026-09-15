# Un volume persistant : PersistentVolume, PersistentVolumeClaim et un Pod qui écrit

## La situation

Ce cluster n'a **aucune StorageClass** et aucun provisionneur : une
réclamation de volume y reste `Pending` pour toujours. L'équipe a besoin
d'un Pod, **`data-pod`**, qui écrive un fichier et le retrouve quand on le
recrée. Le répertoire **`/mnt/lab-data`** existe sur chaque nœud, réservé à
cet usage.

Vous êtes sur le control plane, avec `kubectl` configuré. Le namespace
**`lab`** existe.

## Ce que vous devez obtenir

1. Un PersistentVolume **`lab-pv`** de **1Gi**, en `ReadWriteOnce`, de
   StorageClass **`manual`**, adossé au répertoire `/mnt/lab-data` du nœud.

2. Un PersistentVolumeClaim **`lab-pvc`** dans `lab`, qui demande
   **500Mi** avec le même mode d'accès et la même StorageClass, et qui est
   **`Bound`** à `lab-pv`.

3. Un Pod **`data-pod`** dans `lab` qui monte cette réclamation sur
   **`/data`** et écrit `hello` dans **`/data/test.txt`** au démarrage.

4. Le fichier est **sur le disque du nœud**, dans `/mnt/lab-data`, là où le
   volume est adossé : c'est ce qui survivra au Pod.

## Les repères utiles

Sans provisionneur, c'est l'administrateur qui crée le PersistentVolume, et
la réclamation se lie à un volume dont la capacité, le mode d'accès et la
StorageClass conviennent. Une StorageClass nommée dans un PV et un PVC n'a
pas besoin d'exister comme objet : le nom suffit à les apparier.

Un volume adossé au disque d'un nœud vaut ce que vaut ce nœud : le Pod qui
le monte doit tourner là où sont les données. `hostPath` ne l'impose pas,
`local` l'impose par une affinité de nœud ; les deux sont acceptés ici.

## Comment vous saurez que c'est bon

Les tests lisent le PV, le PVC et sa liaison, le Pod et son montage, le
fichier dans le Pod, puis le même fichier sur le nœud où le Pod tourne.

```bash
dsoxlab check cka-pv-pvc-storageclass
```
