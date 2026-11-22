# Confiner un Pod avec un profil AppArmor

La leçon montre comment charger un profil AppArmor sur un nœud et l'appliquer
à un Pod. Ce cours ajoute ce qu'elle ne fait que citer : le profil que le
runtime pose quand on ne demande rien, un profil en mode **complain** qui
laisse passer et consigne, son passage en **enforce** qui refuse, et ce qui
arrive quand un Pod demande un profil absent du nœud.

Vous travaillez dans le namespace `essai-apparmor`, avec un profil d'essai
chargé sur `k8s-w1.lab`. Le challenge porte sur un autre profil et un autre
Pod : vous le ferez seul, à la fin.

Page associée : [AppArmor](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-apparmor-confiner-un-pod
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, et `ssh` atteint les
workers. Un profil AppArmor se charge **sur le nœud** où tourne le Pod : les
Pods de ce cours sont donc placés sur `k8s-w1.lab` (`nodeName`).

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2 et containerd sur Ubuntu 24.04.

## 🛡️ Exercice 1 : le profil qu'un Pod reçoit sans rien demander

Lancez un Pod sans aucun réglage AppArmor, et lisez le profil de son
processus principal :

```bash
kubectl create namespace essai-apparmor; kubectl run defaut --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-apparmor --overrides='{"spec":{"nodeName":"k8s-w1.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/defaut -n essai-apparmor --timeout=60s; kubectl exec defaut -n essai-apparmor -- cat /proc/1/attr/current
```

```text
namespace/essai-apparmor created
pod/defaut created
pod/defaut condition met
cri-containerd.apparmor.d (enforce)
```

Le Pod n'est pas libre : containerd lui applique son profil par défaut,
`cri-containerd.apparmor.d`, en `enforce`. Ce profil bloque déjà des gestes
dangereux (monter un système de fichiers, écrire dans certains fichiers de
`/proc`). Un profil à vous ne part donc pas de rien : il remplace celui-ci.

## 👀 Exercice 2 : un profil en mode complain

En mode **complain**, AppArmor n'interdit rien : il laisse passer et consigne
dans le journal du noyau ce qu'il aurait refusé. C'est le moyen de tester un
profil sur une application réelle sans la casser. Écrivez un profil qui
n'autorise que la lecture partout, et l'écriture dans `/tmp`, `/dev` et
`/proc`. La règle `signal` laisse le runtime envoyer ses signaux au conteneur,
donc l'arrêter. Chargez-le en complain sur `k8s-w1.lab` :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'cat > /tmp/essai-lecture <<"AA"
#include <tunables/global>
profile essai-lecture flags=(attach_disconnected,mediate_deleted,complain) {
  #include <abstractions/base>
  signal,
  /{,**} rix,
  /tmp/{,**} rw,
  /dev/{,**} rw,
  /proc/{,**} rw,
}
AA
sudo apparmor_parser -r /tmp/essai-lecture; sudo aa-status | grep -A0 essai'
```

```text
   essai-lecture
```

Lancez un Pod sous ce profil, et écrivez dans `/etc`, ce que le profil
n'autorise pas :

```bash
kubectl run prudent --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-apparmor --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"appArmorProfile":{"type":"Localhost","localhostProfile":"essai-lecture"}}}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/prudent -n essai-apparmor --timeout=60s; kubectl exec prudent -n essai-apparmor -- sh -c 'echo x > /etc/essai; echo écriture : code $?'; kubectl exec prudent -n essai-apparmor -- cat /proc/1/attr/current
```

```text
pod/prudent created
pod/prudent condition met
écriture : code 0
essai-lecture (complain)
```

L'écriture réussit (code 0), et le profil est bien `essai-lecture
(complain)`. Le journal du noyau du nœud dit ce qui aurait été refusé :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo journalctl -k --since "-1 min" --no-pager | grep -m1 -oE "apparmor=.ALLOWED. operation=.[a-z]+. .*profile=.essai-lecture. name=.[^ ]+"'
```

```text
apparmor="ALLOWED" operation="mknod" class="file" profile="essai-lecture" name="/etc/essai"
```

`apparmor="ALLOWED"` : la création de `/etc/essai` a été laissée passer, et
consignée. En lisant ces lignes pendant que l'application tourne, vous savez
quelles règles il manque avant de passer en enforce.

Deux pièges relevés en préparant ce cours. Une règle `deny` explicite
s'applique **même** en mode complain, et elle ne laisse aucune trace dans le
journal : pour observer, n'en mettez pas. Et sans la règle `signal`, le
runtime ne peut plus arrêter le conteneur : la suppression du Pod reste
bloquée.

## 🚫 Exercice 3 : passer en enforce

Retirez `complain` des drapeaux et rechargez le profil. Le processus du Pod,
déjà lancé, reçoit aussitôt la nouvelle règle :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sed -i "s/,complain)/)/" /tmp/essai-lecture; sudo apparmor_parser -r /tmp/essai-lecture'; kubectl exec prudent -n essai-apparmor -- sh -c 'echo x > /etc/essai2; echo écriture : code $?; echo y > /tmp/essai; echo écriture dans /tmp : code $?'; kubectl exec prudent -n essai-apparmor -- cat /proc/1/attr/current
```

```text
écriture : code 1
sh: line 0: can't create /etc/essai2: Permission denied
écriture dans /tmp : code 0
essai-lecture (enforce)
```

L'écriture dans `/etc` est maintenant refusée, celle dans `/tmp` passe
toujours, et le profil est en `enforce`. Le journal le dit aussi :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo journalctl -k --since "-1 min" --no-pager | grep -m1 -oE "apparmor=.DENIED. operation=.[a-z]+. .*profile=.essai-lecture. name=.[^ ]+"'
```

```text
apparmor="DENIED" operation="mknod" class="file" profile="essai-lecture" name="/etc/essai2"
```

`apparmor="DENIED"`, sur le même type d'opération. C'est la ligne à chercher
quand une application confinée échoue sur un « Permission denied » que les
droits de fichiers n'expliquent pas.

## ❓ Exercice 4 : un profil qui n'existe pas sur le nœud

Demandez un profil qui n'a été chargé nulle part :

```bash
kubectl run ecoute --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-apparmor --overrides='{"spec":{"nodeName":"k8s-w1.lab","securityContext":{"appArmorProfile":{"type":"Localhost","localhostProfile":"essai-absent"}}}}' -- sleep 3600; sleep 10; kubectl get pod ecoute -n essai-apparmor; kubectl get pod ecoute -n essai-apparmor -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-200
```

```text
pod/ecoute created
NAME     READY   STATUS                 RESTARTS   AGE
ecoute   0/1     CreateContainerError   0          10s
failed to get container spec opts: failed to generate apparmor spec opts: apparmor profile not found essai-absent
```

Le Pod est accepté par l'API server, puis reste en `CreateContainerError` :
c'est containerd, sur le nœud, qui ne trouve pas le profil. Le message le
nomme. Sur un cluster de plusieurs nœuds, c'est le symptôme typique d'un
profil chargé sur un nœud et pas sur celui où le Pod a été placé.

## 🧹 Nettoyage

Supprimez le namespace d'essai, puis retirez le profil de `k8s-w1.lab` :

```bash
kubectl delete namespace essai-apparmor --wait=true --timeout=180s; ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo apparmor_parser -R /tmp/essai-lecture; rm -f /tmp/essai-lecture; sudo aa-status | grep -c essai'
```

```text
namespace "essai-apparmor" deleted
0
```

`aa-status` ne compte plus aucun profil d'essai (0, avec le code 1 de `grep
-c` quand il ne trouve rien).

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-apparmor-confiner-un-pod
dsoxlab check cks-apparmor-confiner-un-pod
```

```text
╭─ Résultat : cks-apparmor-confiner-un-pod ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests          │
╰───────────────────────────────────────────╯
```

C'est le résultat attendu sur un lab neuf. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un profil à charger en enforce sur le bon nœud, et
un Pod à confiner par ce profil, avec la preuve que le confinement agit.

```bash
dsoxlab run cks-apparmor-confiner-un-pod
dsoxlab challenge cks-apparmor-confiner-un-pod
```
