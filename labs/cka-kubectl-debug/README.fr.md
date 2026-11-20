# Entrer dans un conteneur sans shell avec kubectl debug

Beaucoup d'images de production n'ont **pas de shell** : un seul binaire, et
rien d'autre. C'est plus sûr, mais `kubectl exec` n'a alors rien à lancer à
l'intérieur. `kubectl debug` répond à ce problème : il ajoute au Pod un
**conteneur éphémère**, qui apporte ses propres outils, sans redémarrer le
Pod. Dans ce cours, vous butez sur un conteneur sans shell, vous lui ajoutez un
conteneur éphémère, d'abord aveugle puis capable de voir ses processus, vous
vérifiez que le Pod n'a pas été touché, puis vous déboguez un nœud.

Vous travaillez dans un namespace d'essai, `essai-debug`, avec un Pod `muet`
bâti sur l'image `pause` de Kubernetes, qui n'a pas de shell. Le challenge
porte sur une autre application, dans un autre namespace : vous la visiterez
seul, à la fin.

Page associée : [Déboguer une application](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-kubectl-debug
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un conteneur sans shell

Créez le namespace d'essai et le Pod `muet`, sur l'image `pause` :

```bash
kubectl create namespace essai-debug
kubectl run muet --image=registry.k8s.io/pause:3.10.2@sha256:f548e0e8e3dc1896ca956272154dde3314e8cc4fde0a57577ee9fa1c63f5baf4 -n essai-debug && kubectl wait --for=condition=Ready pod/muet -n essai-debug --timeout=120s
```

```text
namespace/essai-debug created
pod/muet created
pod/muet condition met
```

Essayez d'y lancer une commande (`cut` raccourcit le message) :

```bash
kubectl exec muet -n essai-debug -- sh -c 'ps' 2>&1 | cut -c1-160
```

```text
error: Internal error occurred: Internal error occurred: error executing command in container: failed to start exec "ea6b7ed96717a7
```

Échec : il n'y a pas de `sh` dans cette image, donc rien à lancer. Les logs ne
disent rien non plus :

```bash
kubectl logs muet -n essai-debug; echo '(fin des logs)'
```

```text
(fin des logs)
```

Notez l'identifiant unique (uid) du Pod et son nombre de redémarrages, pour
les comparer plus tard :

```bash
kubectl get pod muet -n essai-debug -o jsonpath='uid={.metadata.uid} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'
```

```text
uid=1a5c8792-4109-4dbe-8b0d-12da46f510cc redemarrages=0
```

## 📚 Exercice 2 : un conteneur éphémère qui ne voit que lui

`kubectl debug` ajoute au Pod un conteneur éphémère nommé `regard` (`-c`), sur
une image qui a un shell et `ps` (busybox). Sa commande liste les processus,
puis dort pour rester en vie :

```bash
kubectl debug muet -n essai-debug -c regard --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -- sh -c 'ps; sleep 3600'
```

La commande ne répond rien. Lisez ce que le conteneur éphémère a écrit :

```bash
sleep 8; kubectl logs muet -n essai-debug -c regard
```

```text
PID   USER     TIME  COMMAND
    1 root      0:00 sh -c ps; sleep 3600
    7 root      0:00 ps
```

Le conteneur éphémère ne voit que ses propres processus. Par défaut, chaque
conteneur d'un Pod a son propre espace de processus : celui de `muet` reste
invisible.

## 📚 Exercice 3 : partager les processus avec --target

`--target=muet` demande au conteneur éphémère de partager l'espace de
processus du conteneur `muet`. Ajoutez un second conteneur éphémère, `loupe` :

```bash
kubectl debug muet -n essai-debug -c loupe --target=muet --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -- sh -c 'ps; sleep 3600'
```

```text
Targeting container "muet". If you don't see processes from this container it may be because the container runtime doesn't support this feature.
```

```bash
sleep 8; kubectl logs muet -n essai-debug -c loupe
```

```text
PID   USER     TIME  COMMAND
    1 65535     0:00 /pause
   13 root      0:00 sh -c ps; sleep 3600
   19 root      0:00 ps
```

Cette fois, le processus `/pause` de l'application apparaît, avec le numéro 1.
Par `/proc/1/`, `loupe` peut même lire le système de fichiers de `muet` et la
ligne de commande de son processus. `kubectl exec` fonctionne dans `loupe`,
qui a un shell :

```bash
kubectl exec muet -n essai-debug -c loupe -- sh -c 'ls /proc/1/root/ | head -5; cat /proc/1/cmdline; echo'
```

```text
dev
etc
pause
proc
sys
/pause 
```

Le binaire `pause` est bien seul à la racine de l'image.

## 📚 Exercice 4 : le Pod n'a pas été recréé

Relisez l'uid, les redémarrages, et la liste des conteneurs éphémères :

```bash
kubectl get pod muet -n essai-debug -o jsonpath='uid={.metadata.uid} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}{range .spec.ephemeralContainers[*]}ephemere {.name} cible={.targetContainerName}{"\n"}{end}'
kubectl get pod muet -n essai-debug
```

```text
uid=1a5c8792-4109-4dbe-8b0d-12da46f510cc redemarrages=0
ephemere regard cible=
ephemere loupe cible=muet
NAME   READY   STATUS    RESTARTS   AGE
muet   1/1     Running   0          18s
```

Même uid, aucun redémarrage : c'est le même Pod. Les deux conteneurs éphémères
sont listés dans `spec.ephemeralContainers`, et seul `loupe` a une cible.
`READY 1/1` ne compte pas les conteneurs éphémères. Essayez d'en retirer un :

```bash
kubectl patch pod muet -n essai-debug --subresource ephemeralcontainers --type=json -p '[{"op":"remove","path":"/spec/ephemeralContainers/0"}]' 2>&1 | head -1 | cut -c1-160
```

```text
The Pod "muet" is invalid: spec.ephemeralContainers: Forbidden: existing ephemeral containers "regard" may not be removed
```

Refusé : un conteneur éphémère ne se retire pas. Il reste attaché au Pod
jusqu'à la suppression du Pod.

## 📚 Exercice 5 : déboguer un nœud

`kubectl debug node/<nœud>` lance un Pod de débogage **sur un nœud**, avec le
système de fichiers du nœud monté dans `/host` :

```bash
kubectl debug node/k8s-w1.lab -n essai-debug --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -- sh -c 'cat /host/etc/hostname; ls /host/var/log/pods | head -3' 2>&1 | grep -v -i 'warning'
```

```text
Creating debugging pod node-debugger-k8s-w1.lab-vctct with container debugger on node k8s-w1.lab.
```

Regardez où il tourne, ce qu'il partage avec le nœud, et ce qu'il a lu :

```bash
sleep 10; P=$(kubectl get pods -n essai-debug -o name | grep node-debugger | head -1); kubectl get $P -n essai-debug -o jsonpath='noeud={.spec.nodeName} hostPID={.spec.hostPID} hostNetwork={.spec.hostNetwork}{"\n"}'; kubectl logs $P -n essai-debug
```

```text
noeud=k8s-w1.lab hostPID=true hostNetwork=true
k8s-w1.lab
calico-system_calico-node-hgw4d_451810c1-b102-4623-8de3-48544409830b
calico-system_csi-node-driver-lh854_fd4423c9-9020-4461-8993-0d327ba326ce
essai-debug_muet_1a5c8792-4109-4dbe-8b0d-12da46f510cc
```

Le Pod tourne sur `k8s-w1.lab`, partage les processus (`hostPID`) et le
réseau (`hostNetwork`) du nœud, et lit ses fichiers : son nom, et les
journaux des Pods qu'il héberge, dont `muet`. C'est puissant : réservez ce
geste au dépannage d'un nœud.

## 🧹 Nettoyage

Supprimez le namespace d'essai. C'est le seul moyen de retirer les conteneurs
éphémères, et le Pod de débogage du nœud part avec lui :

```bash
kubectl delete namespace essai-debug
```

```text
namespace "essai-debug" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-kubectl-debug
dsoxlab check cka-kubectl-debug
```

```text
╭── Résultat : cka-kubectl-debug ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests  │
╰───────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une autre application sans shell, dont il faut lister
les processus de l'intérieur avec un conteneur éphémère.

```bash
dsoxlab run cka-kubectl-debug
dsoxlab challenge cka-kubectl-debug
```
