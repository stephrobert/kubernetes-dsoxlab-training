# Lire l'état d'un Pod en erreur

Quand une application ne démarre pas, il faut d'abord **comprendre pourquoi**,
avant de corriger quoi que ce soit. Quatre commandes de kubectl répondent
chacune à une question, dans cet ordre :

- `kubectl get` : **quel** Pod va mal ?
- `kubectl describe` : **pourquoi** va-t-il mal ?
- `kubectl logs` : **qu'a écrit** l'application avant de s'arrêter ?
- `kubectl top` : **combien** consomme-t-elle ?

Dans ce cours, vous créez vous-même trois petites applications dans un
namespace d'essai, `essai-panne` : une qui marche, une dont l'image n'existe
pas, et une qui s'arrête en erreur. Puis vous les diagnostiquez. Le challenge
vous demandera de diagnostiquer d'autres pannes, dans le namespace
`diagnostic` : vous le ferez seul, à la fin.

Page associée : [Lire l'état du cluster : kubectl get, describe, logs et top](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-get-describe-logs-top/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-lire-l-etat-d-un-pod-en-erreur
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`lab` y tourne, et votre kubectl le vise déjà. L'outil de mesure
**metrics-server**, dont `kubectl top` a besoin, est installé.

Créez le namespace d'essai et ses trois applications :

```bash
kubectl create namespace essai-panne
kubectl create deployment front \
  --image=nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-panne
kubectl create deployment cache --image=nginx:9.99 -n essai-panne
kubectl create deployment tache \
  --image=busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e \
  -n essai-panne \
  -- sh -c 'echo "tache: lancement"; echo "erreur: fichier /etc/tache.conf introuvable" >&2; exit 3'
```

```text
namespace/essai-panne created
deployment.apps/front created
deployment.apps/cache created
deployment.apps/tache created
```

`front` est un serveur web qui marche. `cache` demande la version `9.99` de
nginx, qui n'existe pas. `tache` écrit un message d'erreur, puis s'arrête avec
le code `3`. Attendez une minute avant de continuer, le temps que Kubernetes
essaie de les lancer.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026.

## 📚 Exercice 1 : repérer le Pod qui va mal

Listez les Pods du namespace :

```bash
kubectl get pods -n essai-panne
```

```text
NAME                     READY   STATUS         RESTARTS      AGE
cache-6bcb8d84c5-4hhx5   0/1     ErrImagePull   0             61s
front-545fdfbcf8-8v4ph   1/1     Running        0             61s
tache-7794c9cf45-q4xzs   0/1     Error          3 (48s ago)   60s
```

Trois colonnes suffisent pour repérer les problèmes :

- `READY` : `0/1` veut dire qu'aucun conteneur du Pod n'est prêt ;
- `STATUS` : `ErrImagePull` pour `cache` (l'image ne se télécharge pas),
  `Error` pour `tache` (le programme s'est arrêté en erreur) ;
- `RESTARTS` : `tache` a déjà redémarré 3 fois. Un compteur qui monte veut dire
  que le programme démarre puis s'arrête, en boucle.

Pour ne voir qu'une application, filtrez sur son étiquette avec `-l` :

```bash
kubectl get pods -n essai-panne -l app=front
```

```text
NAME                     READY   STATUS    RESTARTS   AGE
front-545fdfbcf8-8v4ph   1/1     Running   0          61s
```

## 📚 Exercice 2 : afficher plus de colonnes, ou une seule valeur

L'option `-o wide` ajoute des colonnes, dont l'adresse du Pod et le nœud où il
tourne :

```bash
kubectl get pods -n essai-panne -o wide
```

```text
NAME                     READY   STATUS         RESTARTS      AGE   IP            NODE                NOMINATED NODE   READINESS GATES
cache-6bcb8d84c5-4hhx5   0/1     ErrImagePull   0             61s   10.244.0.12   lab-control-plane   <none>           <none>
front-545fdfbcf8-8v4ph   1/1     Running        0             61s   10.244.0.11   lab-control-plane   <none>           <none>
tache-7794c9cf45-q4xzs   0/1     Error          3 (48s ago)   60s   10.244.0.13   lab-control-plane   <none>           <none>
```

À l'inverse, `-o jsonpath` n'affiche qu'une valeur. Demandez l'image du Pod
`cache` :

```bash
kubectl get pods -n essai-panne -l app=cache -o jsonpath='{.items[0].spec.containers[0].image}'; echo
```

```text
nginx:9.99
```

Le `; echo` ajoute le retour à la ligne que `jsonpath` ne met pas.

## 📚 Exercice 3 : comprendre pourquoi `cache` ne démarre pas

`kubectl describe` affiche tout ce que Kubernetes sait du Pod. La sortie est
longue : `grep` ne garde ici que les lignes utiles. Avec `-l`, `describe`
cache les événements, sauf si vous ajoutez `--show-events=true`.

```bash
kubectl describe pod -n essai-panne -l app=cache --show-events=true \
  | grep -E "^(Name|Status):|Image:|State:|Reason:|Warning"
```

```text
Name:             cache-6bcb8d84c5-4hhx5
Status:           Pending
    Image:          nginx:9.99
    State:          Waiting
      Reason:       ErrImagePull
  Warning  Failed     20s (x3 over 60s)  kubelet            spec.containers{nginx}: Failed to pull image "nginx:9.99": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:9.99": failed to resolve reference "docker.io/library/nginx:9.99": docker.io/library/nginx:9.99: not found
  Warning  Failed     20s (x3 over 60s)  kubelet            spec.containers{nginx}: Error: ErrImagePull
  Warning  Failed     8s (x3 over 59s)   kubelet            spec.containers{nginx}: Error: ImagePullBackOff
```

Lisez dans cet ordre :

1. `State: Waiting` avec `Reason: ErrImagePull` : le conteneur attend, il n'a
   jamais démarré ;
2. les lignes `Warning` donnent la cause : `nginx:9.99: not found`, cette
   version d'image n'existe pas.

`(x3 over 60s)` veut dire que Kubernetes a essayé trois fois en 60 secondes.

## 📚 Exercice 4 : comprendre pourquoi `tache` s'arrête

Pour `tache`, l'histoire est différente : le conteneur a bien démarré, puis
s'est arrêté.

```bash
kubectl describe pod -n essai-panne -l app=tache \
  | grep -E "State:|Reason:|Exit Code:|Restart Count:"
```

```text
    State:          Terminated
      Reason:       Error
      Exit Code:    3
    Last State:     Terminated
      Reason:       Error
      Exit Code:    3
    Restart Count:  3
```

`State: Terminated` : le conteneur s'est arrêté. `Exit Code: 3` est le code
de sortie du programme : tout code autre que 0 veut dire un échec.
`Last State` décrit l'exécution d'avant, qui s'est arrêtée de la même façon.
Kubernetes a fait son travail : le problème est dans le programme. Pour savoir
pourquoi il s'arrête, il faut lire ce qu'il a écrit (exercice 6).

## 📚 Exercice 5 : voir tous les avertissements du namespace

`describe` montre les événements d'un seul Pod. `kubectl get events` montre
ceux de tout le namespace. Ne gardez que les avertissements :

```bash
kubectl get events -n essai-panne --field-selector type=Warning
```

```text
LAST SEEN   TYPE      REASON    OBJECT                       MESSAGE
20s         Warning   Failed    pod/cache-6bcb8d84c5-4hhx5   Failed to pull image "nginx:9.99": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:9.99": failed to resolve reference "docker.io/library/nginx:9.99": docker.io/library/nginx:9.99: not found
20s         Warning   Failed    pod/cache-6bcb8d84c5-4hhx5   Error: ErrImagePull
8s          Warning   Failed    pod/cache-6bcb8d84c5-4hhx5   Error: ImagePullBackOff
20s         Warning   BackOff   pod/tache-7794c9cf45-q4xzs   Back-off restarting failed container busybox in pod tache-7794c9cf45-q4xzs_essai-panne(2df306c3-14b0-43f1-9a5c-91459e6441f1)
```

En une commande, vous voyez les deux pannes. `BackOff` veut dire que
Kubernetes attend un peu avant de relancer `tache`, et attend de plus en plus
longtemps à chaque échec.

## 📚 Exercice 6 : lire ce que l'application a écrit

`kubectl logs` affiche ce que le programme a écrit. Lisez les journaux de
`tache` :

```bash
kubectl logs deployment/tache -n essai-panne
```

```text
erreur: fichier /etc/tache.conf introuvable
tache: lancement
```

Voilà la cause : un fichier de configuration manque. Les deux lignes ne sont
pas dans l'ordre où elles ont été écrites : le message normal et le message
d'erreur passent par deux canaux différents, que kubectl mélange.

Essayez maintenant les journaux de `cache` :

```bash
kubectl logs deployment/cache -n essai-panne
```

```text
Error from server (BadRequest): container "nginx" in pod "cache-6bcb8d84c5-4hhx5" is waiting to start: image can't be pulled
```

Il n'y a pas de journal : un conteneur qui n'a jamais démarré n'a rien écrit.
Pour lui, c'est `describe` qui donnait la réponse.

L'option `--previous` lit les journaux de l'exécution d'avant, celle qui a
planté. Sur `front`, qui n'a jamais redémarré, elle ne trouve rien :

```bash
kubectl logs deployment/front -n essai-panne --previous
```

```text
Error from server (BadRequest): previous terminated container "nginx" in pod "front-545fdfbcf8-8v4ph" not found
```

Ce message veut dire « pas de redémarrage », et donc pas de plantage à
expliquer.

## 📚 Exercice 7 : mesurer la consommation

`kubectl top` affiche ce que consomment les Pods en ce moment : processeur
(en millièmes de cœur, `m`) et mémoire (en `Mi`).

```bash
kubectl top pods -n essai-panne
```

```text
NAME                     CPU(cores)   MEMORY(bytes)
front-545fdfbcf8-8v4ph   0m           3Mi
```

Seul `front` apparaît : un Pod qui ne tourne pas ne consomme rien, il n'a donc
pas de mesure. `top` ne sert pas à trouver un Pod en panne, il sert à repérer
celui qui consomme trop.

Classez les Pods d'un namespace plus chargé, `kube-system`, par mémoire :

```bash
kubectl top pods -n kube-system --sort-by=memory | head -4
```

```text
NAME                                        CPU(cores)   MEMORY(bytes)
kube-apiserver-lab-control-plane            35m          249Mi
kube-controller-manager-lab-control-plane   12m          77Mi
etcd-lab-control-plane                      19m          49Mi
```

Le premier de la liste est celui qui consomme le plus de mémoire.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Ses trois applications disparaissent avec
lui :

```bash
kubectl delete namespace essai-panne
```

```text
namespace "essai-panne" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-lire-l-etat-d-un-pod-en-erreur
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```

```text
╭─ Résultat : k8s-lire-l-etat-d-un-pod-en-erreur ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests                │
╰─────────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : diagnostiquer les deux applications en panne du
namespace `diagnostic`, et trouver celle qui consomme le plus de mémoire, sans
rien réparer.

```bash
dsoxlab run k8s-lire-l-etat-d-un-pod-en-erreur
dsoxlab challenge k8s-lire-l-etat-d-un-pod-en-erreur
```
