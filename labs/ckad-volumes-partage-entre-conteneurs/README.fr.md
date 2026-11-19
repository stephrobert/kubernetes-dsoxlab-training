# Faire lire à un conteneur ce qu'un autre écrit

Deux conteneurs d'un même Pod partagent le réseau, mais pas leurs fichiers :
chacun voit le système de fichiers de son image. Pour faire passer des
fichiers de l'un à l'autre, on leur donne un **volume** commun. Dans ce cours,
vous constatez cette séparation, vous voyez qu'on ne peut pas ajouter un volume
à un Pod qui tourne, vous partagez un répertoire et un seul, vous le montez en
lecture seule, vous voyez combien de temps vit un volume `emptyDir`, et vous
en placez un en mémoire.

Vous travaillez dans un namespace d'essai, `essai-volumes`, avec un Pod
`atelier` et ses conteneurs `ecrivain` et `relecteur`. Le challenge vous
demandera de réparer un autre Pod, dans un autre namespace : vous le ferez
seul, à la fin.

Page associée : [Les volumes applicatifs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/volumes-applicatifs/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-volumes-partage-entre-conteneurs
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : même Pod, fichiers séparés

Créez le namespace d'essai et un Pod `atelier` à deux conteneurs, **sans**
volume. L'écrivain crée `/partage/note.txt`, le relecteur ne fait qu'attendre :

```bash
kubectl create namespace essai-volumes
cat > ~/atelier-sans-volume.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: atelier
spec:
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "mkdir -p /partage; echo note de l ecrivain > /partage/note.txt; sleep 3600"]
    - name: relecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
YAML
kubectl apply -n essai-volumes -f ~/atelier-sans-volume.yaml && kubectl wait --for=condition=Ready pod/atelier -n essai-volumes --timeout=120s
```

```text
namespace/essai-volumes created
pod/atelier created
pod/atelier condition met
```

Lisez le fichier depuis chacun des deux conteneurs (`-c` choisit le
conteneur) :

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- cat /partage/note.txt; kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
note de l ecrivain
cat: can't open '/partage/note.txt': No such file or directory
command terminated with exit code 1
```

L'écrivain voit son fichier, le relecteur non. Pourtant, ils partagent bien le
réseau : ils ont la même adresse IP.

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- hostname -i; kubectl exec atelier -n essai-volumes -c relecteur -- hostname -i
```

```text
10.244.38.116
10.244.38.116
```

## 📚 Exercice 2 : on ne change pas les volumes d'un Pod en marche

Écrivez la version avec volume. Un volume se déclare à **deux** niveaux :

- une fois pour le Pod, sous `spec.volumes` : ici un `emptyDir`, un répertoire
  vide créé avec le Pod ;
- puis dans chaque conteneur qui doit le voir, sous `volumeMounts`, avec son
  chemin.

Le relecteur le monte en lecture seule (`readOnly: true`). L'écrivain écrit
aussi un brouillon **hors** du volume, dans `/ailleurs` :

```bash
cat > ~/atelier.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: atelier
spec:
  volumes:
    - name: partage
      emptyDir: {}
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo note de l ecrivain > /partage/note.txt; mkdir -p /ailleurs; echo brouillon prive > /ailleurs/brouillon.txt; sleep 3600"]
      volumeMounts:
        - name: partage
          mountPath: /partage
    - name: relecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: partage
          mountPath: /partage
          readOnly: true
YAML
kubectl apply -n essai-volumes -f ~/atelier.yaml 2>&1 | head -1 | cut -c1-160
```

```text
The Pod "atelier" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`,`spec.initContainers[*].image`,`spec.acti
```

Refusé : on ne peut changer presque rien d'un Pod qui existe, et surtout pas
ses volumes (`head` et `cut` raccourcissent ici un message très long). Il faut
supprimer le Pod et le recréer :

```bash
kubectl delete pod atelier -n essai-volumes --wait=true && kubectl apply -n essai-volumes -f ~/atelier.yaml && kubectl wait --for=condition=Ready pod/atelier -n essai-volumes --timeout=120s
```

```text
pod "atelier" deleted from essai-volumes namespace
pod/atelier created
pod/atelier condition met
```

## 📚 Exercice 3 : ce qui traverse, et ce qui ne traverse pas

Le relecteur voit maintenant la note :

```bash
kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
note de l ecrivain
```

Et le brouillon, écrit hors du volume ?

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- cat /ailleurs/brouillon.txt; kubectl exec atelier -n essai-volumes -c relecteur -- cat /ailleurs/brouillon.txt
```

```text
brouillon prive
cat: can't open '/ailleurs/brouillon.txt': No such file or directory
command terminated with exit code 1
```

Seul le répertoire monté est partagé. Tout le reste de chaque conteneur reste à
lui. C'est pourquoi on monte le volume là où passent les fichiers à échanger,
et pas plus haut : sur `/`, il partagerait tout. Voici le montage vu du
relecteur :

```bash
kubectl exec atelier -n essai-volumes -c relecteur -- sh -c 'mount | grep /partage'
```

```text
/dev/vda1 on /partage type ext4 (ro,relatime,discard,errors=remount-ro,commit=30)
```

`ro` : lecture seule. Le volume est un répertoire du disque du nœud
(`/dev/vda1`), monté dans le conteneur.

## 📚 Exercice 4 : un montage en lecture seule

Le relecteur essaie d'écrire dans le volume :

```bash
kubectl exec atelier -n essai-volumes -c relecteur -- sh -c 'echo correction > /partage/note.txt'
```

```text
sh: line 0: can't create /partage/note.txt: Read-only file system
command terminated with exit code 1
```

Refusé. L'écrivain, lui, peut toujours écrire, et le relecteur voit l'ajout :

```bash
kubectl exec atelier -n essai-volumes -c ecrivain -- sh -c 'echo ajout de l ecrivain >> /partage/note.txt'; kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
note de l ecrivain
ajout de l ecrivain
```

## 📚 Exercice 5 : la vie d'un emptyDir

Combien de temps vit un `emptyDir` ? Créez un Pod `compteur` dont l'écrivain
note l'heure de son démarrage, attend 8 secondes, puis s'arrête. Kubernetes
le redémarre à chaque fois. Un relecteur reste debout pour lire le volume :

```bash
cat <<'YAML' | kubectl apply -n essai-volumes -f -
apiVersion: v1
kind: Pod
metadata:
  name: compteur
spec:
  volumes:
    - name: partage
      emptyDir: {}
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo demarrage a $(date +%T) >> /partage/demarrages.txt; sleep 8"]
      volumeMounts:
        - name: partage
          mountPath: /partage
    - name: relecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: partage
          mountPath: /partage
YAML
```

```text
pod/compteur created
```

40 secondes plus tard :

```bash
sleep 40; kubectl get pod compteur -n essai-volumes; kubectl exec compteur -n essai-volumes -c relecteur -- cat /partage/demarrages.txt
```

```text
NAME       READY   STATUS     RESTARTS      AGE
compteur   1/2     NotReady   2 (24s ago)   40s
demarrage a 21:14:17
demarrage a 21:14:25
demarrage a 21:14:48
```

L'écrivain a redémarré 2 fois, et le fichier garde une ligne par démarrage :
le volume **survit au redémarrage d'un conteneur**. Supprimez maintenant le Pod
`atelier`, puis recréez-le depuis le même fichier :

```bash
kubectl delete pod atelier -n essai-volumes --wait=true && kubectl apply -n essai-volumes -f ~/atelier.yaml && kubectl wait --for=condition=Ready pod/atelier -n essai-volumes --timeout=120s && kubectl exec atelier -n essai-volumes -c relecteur -- cat /partage/note.txt
```

```text
pod "atelier" deleted from essai-volumes namespace
pod/atelier created
pod/atelier condition met
note de l ecrivain
```

La ligne `ajout de l ecrivain` de l'exercice 4 a disparu : un `emptyDir`
**naît et meurt avec son Pod**. Il sert à faire passer des fichiers, pas à les
garder.

## 📚 Exercice 6 : un emptyDir en mémoire

Un `emptyDir` peut vivre en mémoire plutôt que sur le disque du nœud :
`medium: Memory`. `sizeLimit` borne sa taille :

```bash
cat <<'YAML' | kubectl apply -n essai-volumes -f -
apiVersion: v1
kind: Pod
metadata:
  name: rapide
spec:
  volumes:
    - name: cache
      emptyDir:
        medium: Memory
        sizeLimit: 32Mi
  containers:
    - name: ecrivain
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: cache
          mountPath: /cache
YAML
kubectl wait --for=condition=Ready pod/rapide -n essai-volumes --timeout=120s
```

```text
pod/rapide created
pod/rapide condition met
```

Comparez les deux volumes avec `df` :

```bash
kubectl exec rapide -n essai-volumes -- df -h /cache
kubectl exec atelier -n essai-volumes -c ecrivain -- df -h /partage
```

```text
Filesystem                Size      Used Available Use% Mounted on
tmpfs                    32.0M         0     32.0M   0% /cache
Filesystem                Size      Used Available Use% Mounted on
/dev/vda1                18.3G      4.3G     14.0G  24% /partage
```

`/cache` est un `tmpfs` (un système de fichiers en mémoire) de 32 Mo.
`/partage` est sur le disque du nœud, dont il partage la place.

## 🧹 Nettoyage

Supprimez le namespace d'essai et les fichiers de travail :

```bash
kubectl delete namespace essai-volumes; rm -f ~/atelier.yaml ~/atelier-sans-volume.yaml
```

```text
namespace "essai-volumes" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-volumes-partage-entre-conteneurs
dsoxlab check ckad-volumes-partage-entre-conteneurs
```

```text
╭─ Résultat : ckad-volumes-partage-entre-conteneurs ─╮
│  0 / 100 pts                                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                   │
╰────────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un autre Pod, dont le lecteur ne trouve pas ce que
le producteur écrit. Faites passer le bon répertoire, et seulement lui.

```bash
dsoxlab run ckad-volumes-partage-entre-conteneurs
dsoxlab challenge ckad-volumes-partage-entre-conteneurs
```
