# Diagnostiquer deux Pods en échec

Un **Pod** est la plus petite chose que Kubernetes fait tourner : un ou
plusieurs conteneurs qui vivent ensemble. La leçon montre comment créer un Pod,
l'observer, et reconnaître une image introuvable ou un programme qui s'arrête
en boucle. Ce cours vous fait **réparer** ces Pods. Une fois créé, un Pod ne se
modifie presque plus : vous voyez ce qui se change en place, ce que l'API
refuse, et comment recréer un Pod sous le même nom. Vous finissez par un Pod
qu'aucun nœud n'accepte.

Vous travaillez dans un namespace d'essai, `essai-pods`. Le challenge vous
demandera de diagnostiquer et de réparer deux autres Pods : vous le ferez
seul, à la fin.

Page associée : [Pods Kubernetes : créer, observer et diagnostiquer](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pods/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-diagnostiquer-un-pod
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Le cluster kind
`boutique` y tourne, et votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026.

## 📚 Exercice 1 : relever la raison d'attente d'un Pod

Créez le namespace d'essai et un Pod `apercu` qui demande une version de nginx
qui n'existe pas :

```bash
kubectl create namespace essai-pods
kubectl run apercu --image=nginx:9.9 -n essai-pods
```

```text
namespace/essai-pods created
pod/apercu created
```

Attendez une vingtaine de secondes, puis lisez la raison de deux façons : la
colonne `STATUS`, et le champ exact de l'état du conteneur, que `jsonpath`
extrait seul.

```bash
kubectl get pod apercu -n essai-pods
kubectl get pod apercu -n essai-pods -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}{"\n"}'
```

```text
NAME     READY   STATUS             RESTARTS   AGE
apercu   0/1     ImagePullBackOff   0          20s
ImagePullBackOff
```

Selon le moment, vous lirez `ErrImagePull` ou `ImagePullBackOff` : Kubernetes
réessaie en espaçant ses tentatives. Notez aussi l'**UID** du Pod,
l'identifiant unique que Kubernetes lui a donné à sa création :

```bash
kubectl get pod apercu -n essai-pods -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
d378b6aa-f14b-4a85-8de2-1b30e58b62a5
```

## 📚 Exercice 2 : corriger l'image d'un Pod sans le recréer

L'image d'un conteneur fait partie des rares champs qu'on peut changer sur un
Pod existant. `kubectl set image` demande le nom du **conteneur**, pas celui du
Pod. Avec `kubectl run`, les deux portent le même nom, mais vérifiez-le :

```bash
kubectl describe pod apercu -n essai-pods | grep -A1 "^Containers:"
```

```text
Containers:
  apercu:
```

Changez l'image, attendez que le Pod soit prêt, puis relisez son UID :

```bash
kubectl set image pod/apercu apercu=nginx:1.30.5 -n essai-pods
kubectl wait --for=condition=Ready pod/apercu -n essai-pods --timeout=120s
kubectl get pod apercu -n essai-pods
kubectl get pod apercu -n essai-pods -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
pod/apercu image updated
pod/apercu condition met
NAME     READY   STATUS    RESTARTS   AGE
apercu   1/1     Running   0          20s
d378b6aa-f14b-4a85-8de2-1b30e58b62a5
```

Même UID qu'à l'exercice 1 : c'est le même Pod, réparé en place. Son âge
(`AGE`) n'est pas revenu à zéro.

## 📚 Exercice 3 : voir l'API refuser une nouvelle commande

Créez un Pod `calcul` dont le programme s'arrête en erreur, avec le code 4 :

```bash
kubectl run calcul \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  -n essai-pods -- sh -c "echo calcul: division par zéro >&2; exit 4"
```

```text
pod/calcul created
```

Quinze secondes plus tard, il a déjà redémarré deux fois :

```bash
kubectl get pod calcul -n essai-pods
```

```text
NAME     READY   STATUS   RESTARTS      AGE
calcul   0/1     Error    2 (14s ago)   15s
```

Enregistrez le manifeste du Pod dans un fichier, puis remplacez sa commande
par une attente d'une heure :

```bash
kubectl get pod calcul -n essai-pods -o yaml > ~/essai-calcul.yaml
sed -i "s|echo calcul: division par zéro >&2; exit 4|sleep 3600|" ~/essai-calcul.yaml
grep -n -A3 "args:" ~/essai-calcul.yaml
```

```text
14:  - args:
15-    - sh
16-    - -c
17-    - 'sleep 3600'
```

Essayez maintenant d'envoyer cette nouvelle commande au Pod existant.
`kubectl replace` remplace l'objet du cluster par celui qu'on lui donne :

```bash
kubectl get pod calcul -n essai-pods -o yaml \
  | sed "s|echo calcul: division par zéro >&2; exit 4|sleep 3600|" \
  | kubectl replace -f -
```

```text
The Pod "calcul" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`,`spec.initContainers[*].image`,`spec.activeDeadlineSeconds`,`spec.tolerations` (only additions to existing tolerations),`spec.terminationGracePeriodSeconds` (allow it to be set to 1 if it was previously negative)
```

L'API refuse, et sa réponse donne la liste complète de ce qu'on peut changer
sur un Pod existant : les images, un délai, des tolérances. La commande n'en
fait pas partie. La commande lit le Pod juste avant de l'envoyer : un fichier
lu plus tôt pourrait donner une autre erreur, `Conflict`, si le Pod a redémarré
entre-temps.

## 📚 Exercice 4 : recréer le Pod sous le même nom

Pour changer la commande, il faut supprimer le Pod et le recréer.
`kubectl replace --force` fait les deux, à partir du fichier corrigé à
l'exercice 3. Relevez l'UID avant :

```bash
kubectl get pod calcul -n essai-pods -o jsonpath='{.metadata.uid}{"\n"}'
kubectl replace --force -f ~/essai-calcul.yaml
kubectl wait --for=condition=Ready pod/calcul -n essai-pods --timeout=120s
kubectl get pod calcul -n essai-pods
kubectl get pod calcul -n essai-pods -o jsonpath='{.metadata.uid} {.spec.containers[0].args}{"\n"}'
```

```text
58ba8d33-d3de-453c-b748-dc3b80d96d04
pod "calcul" deleted from essai-pods namespace
pod/calcul replaced
pod/calcul condition met
NAME     READY   STATUS    RESTARTS   AGE
calcul   1/1     Running   0          0s
b8137c1f-8559-4d01-ae67-d660b3304b74 ["sh","-c","sleep 3600"]
```

Le Pod porte le même nom, mais c'est un autre objet : nouvel UID, âge `0s`,
aucun redémarrage. Le fichier venait de `kubectl get -o yaml` et contenait
encore l'ancien UID, la `resourceVersion` et tout un bloc `status` :
`replace --force` les ignore à la recréation. Comparez avec l'exercice 2 :
une image corrigée garde le Pod, une commande corrigée le remplace.

## 📚 Exercice 5 : un Pod qu'aucun nœud n'accepte

La leçon annonce une troisième panne : le Pod qui reste `Pending`. Écrivez un
Pod qui réserve 16 processeurs :

```bash
cat > ~/essai-gourmand.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: gourmand
  namespace: essai-pods
spec:
  containers:
    - name: gourmand
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      resources:
        requests:
          cpu: "16"
EOF
kubectl apply -f ~/essai-gourmand.yaml
```

```text
pod/gourmand created
```

Le champ `requests` dit ce que le Pod réserve sur un nœud. Regardez où il en
est, puis lisez ses événements :

```bash
kubectl get pod gourmand -n essai-pods
kubectl describe pod gourmand -n essai-pods | sed -n '/^Events:/,$p'
```

```text
NAME       READY   STATUS    RESTARTS   AGE
gourmand   0/1     Pending   0          5s
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  6s    default-scheduler  0/1 nodes are available: 1 Insufficient cpu. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

Ici, aucun conteneur n'existe : ni image à télécharger, ni journal à lire.
C'est le **scheduler**, qui choisit le nœud de chaque Pod, qui explique son
refus : `Insufficient cpu`. Vérifiez ce que le nœud offre :

```bash
kubectl get nodes -o custom-columns=NOM:.metadata.name,CPU:.status.allocatable.cpu
```

```text
NOM                      CPU
boutique-control-plane   2
```

Deux processeurs, pour une demande de seize : le Pod restera `Pending` tant
que sa demande ne baisse pas ou qu'aucun nœud plus grand n'arrive.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le namespace
d'essai, avec ses trois Pods, et les deux fichiers.

```bash
kubectl delete namespace essai-pods
rm ~/essai-calcul.yaml ~/essai-gourmand.yaml
```

```text
namespace "essai-pods" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-diagnostiquer-un-pod
dsoxlab check k8s-diagnostiquer-un-pod
```

```text
╭─ Résultat : k8s-diagnostiquer-un-pod ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : diagnostiquer les deux Pods en panne du namespace
`pods-en-panne`, puis les réparer, chacun de la bonne façon.

```bash
dsoxlab run k8s-diagnostiquer-un-pod
dsoxlab challenge k8s-diagnostiquer-un-pod
```
