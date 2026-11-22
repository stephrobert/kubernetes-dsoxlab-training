# Sécuriser un Pod existant sans changer ce qu'il fait

La leçon montre comment régler le `securityContext` d'un Pod : identité du
processus, système de fichiers, capacités. Ce cours montre **pourquoi** ces
réglages comptent, en mesurant ce qu'un Pod voit de son nœud et de l'API selon
sa définition : les processus du nœud, ses disques, et le jeton d'accès monté
dans chaque conteneur.

Vous travaillez dans le namespace `essai-exposition`. Le challenge porte sur un
autre namespace et un autre Pod : vous le ferez seul, à la fin.

Page associée : [Security Context](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-secure-existing-pod
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2.

## 👁️ Exercice 1 : un Pod qui voit les processus du nœud

Lancez deux Pods identiques, sauf que `voisin` partage l'espace des processus
du nœud (`hostPID: true`) :

```bash
kubectl create namespace essai-exposition; kubectl run voisin --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition --overrides='{"spec":{"hostPID":true}}' -- sleep 3600; kubectl run cloisonne --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-exposition --timeout=60s
```

```text
namespace/essai-exposition created
pod/voisin created
pod/cloisonne created
pod/cloisonne condition met
pod/voisin condition met
```

Comptez les processus que chacun voit, et ceux qui s'appellent `kubelet` ou
`containerd` :

```bash
for p in cloisonne voisin; do printf '%s : ' $p; kubectl exec $p -n essai-exposition -- sh -c 'ps -o comm | tail -n +2 | wc -l; ps -o comm | grep -c -x -E "kubelet|containerd"; true' | tr '\n' ' '; echo; done
```

```text
cloisonne : 5 0 
voisin : 180 2 
```

`cloisonne` ne voit que ses propres processus, et aucun processus du nœud.
`voisin` voit tous ceux du nœud, dont le kubelet et containerd : il peut lire
leurs lignes de commande et leurs variables d'environnement, et leur envoyer
des signaux s'il tourne en root. Un champ de la spécification suffit à
ouvrir cette porte.

## 💽 Exercice 2 : un Pod privilégié voit les disques

Ajoutez un Pod privilégié (`privileged: true`) et comparez ce que chacun voit
dans `/dev` :

```bash
kubectl run tout-voir --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition --overrides='{"spec":{"containers":[{"name":"t","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"privileged":true}}]}}' -- true; kubectl wait --for=condition=Ready pod/tout-voir -n essai-exposition --timeout=60s; for p in cloisonne tout-voir; do printf '%s : ' $p; kubectl exec $p -n essai-exposition -- sh -c 'ls /dev | wc -l; ls /dev | grep -m2 -E "^(vd|sd)" || echo aucun-disque' | tr '\n' ' '; echo; done
```

```text
pod/tout-voir created
pod/tout-voir condition met
cloisonne : 16 aucun-disque 
tout-voir : 187 vda vda1 
```

`cloisonne` voit 16 entrées et aucun disque. `tout-voir` en voit plus de 180,
dont `vda`, le disque du nœud : avec les droits root qu'il a déjà, il peut le
monter et lire ou modifier tout le système de fichiers de la machine. C'est
pour cela qu'un Pod privilégié équivaut à un accès root au nœud.

## 🔑 Exercice 3 : le jeton monté par défaut

Chaque Pod reçoit, sans rien demander, le jeton de son compte de service :

```bash
kubectl exec cloisonne -n essai-exposition -- ls /var/run/secrets/kubernetes.io/serviceaccount/
```

```text
ca.crt
namespace
token
```

Utilisez ce jeton depuis le Pod pour interroger l'API du cluster :

```bash
kubectl exec cloisonne -n essai-exposition -- sh -c 'wget -qO- --no-check-certificate --header "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" https://kubernetes.default/api/v1/namespaces/essai-exposition/pods 2>&1 | head -c 120; echo'
```

```text
wget: server returned error: HTTP/1.1 403 Forbidden
```

`403 Forbidden`, et non `401` : l'API server a **reconnu** le jeton (c'est
celui du compte `default` du namespace), mais ce compte n'a aucun droit. Le
jour où quelqu'un lui en donne, tout processus du Pod, y compris un attaquant
qui y serait entré, les obtient aussi.

## 🚫 Exercice 4 : un Pod sans jeton

Un Pod qui n'a pas besoin de parler à l'API peut refuser le jeton avec
`automountServiceAccountToken: false` :

```bash
kubectl run sans-jeton --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition --overrides='{"spec":{"automountServiceAccountToken":false}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sans-jeton -n essai-exposition --timeout=60s; kubectl exec sans-jeton -n essai-exposition -- ls /var/run/secrets/kubernetes.io/serviceaccount/; echo "(code de ls)"
```

```text
pod/sans-jeton created
pod/sans-jeton condition met
ls: /var/run/secrets/kubernetes.io/serviceaccount/: No such file or directory
command terminated with exit code 1
(code de ls)
```

Le dossier du jeton n'existe pas : il n'y a rien à voler. Le même réglage
existe sur le compte de service lui-même, pour tous ses Pods à la fois.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses quatre Pods :

```bash
kubectl delete namespace essai-exposition
```

```text
namespace "essai-exposition" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-secure-existing-pod
dsoxlab check cks-secure-existing-pod
```

```text
╭─ Résultat : cks-secure-existing-pod ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests     │
╰──────────────────────────────────────╯
```

C'est le résultat attendu sur un lab neuf. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Pod en production qui cumule plusieurs défauts,
à remplacer par un Pod qui fait le même travail sans aucun d'eux.

```bash
dsoxlab run cks-secure-existing-pod
dsoxlab challenge cks-secure-existing-pod
```
