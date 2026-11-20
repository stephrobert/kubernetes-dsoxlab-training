# Ouvrir une application hors du cluster avec un Service NodePort

Un Service de type `ClusterIP` n'est joignable que depuis l'intérieur du
cluster. Pour qu'un utilisateur, à l'extérieur, joigne l'application, le type
**NodePort** ouvre en plus un port sur **chaque nœud** du cluster. Une requête
envoyée à ce port, sur n'importe quel nœud, arrive à l'un des Pods. La leçon
crée un Service NodePort. Ce cours vous le fait joindre par chaque nœud, fixer
son port, et rencontrer deux limites : un port de nœud déjà pris, et
`externalTrafficPolicy: Local`, qui ferme les nœuds sans Pod.

Vous travaillez dans un namespace d'essai, `essai-nodeport`, avec une
application `vitrine`. Le challenge vous demandera de réparer un autre Service
NodePort : vous le ferez seul, à la fin.

Page associée : [Services Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-service-nodeport-reparer
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : l'application, et les adresses des nœuds

Créez le namespace d'essai, puis l'application `vitrine`, en deux Pods qui
servent le texte `vitrine` sur le port 8080 :

```bash
kubectl create namespace essai-nodeport
cat <<'YAML' | kubectl apply -n essai-nodeport -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vitrine
  template:
    metadata:
      labels:
        app: vitrine
    spec:
      terminationGracePeriodSeconds: 5
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "mkdir -p /www && echo vitrine > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
YAML
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
```

```text
namespace/essai-nodeport created
deployment.apps/vitrine created
deployment "vitrine" successfully rolled out
```

Le champ `terminationGracePeriodSeconds: 5` raccourcit l'arrêt d'un Pod. Pour
arrêter un conteneur, Kubernetes envoie un signal d'arrêt au processus
principal, celui qui porte le numéro 1. Un processus numéro 1 qui n'a rien
prévu pour ce signal l'ignore : ici, c'est le cas de `httpd` comme de `sh`.
Kubernetes attend alors le délai prévu, 30 secondes par défaut, avant de
couper le conteneur. Mesuré sur ce cluster : 31 secondes avec `exec httpd`,
32 sans. Le délai de 5 secondes évite cette attente quand un Pod disparaît.

Un NodePort se joint par l'adresse d'un nœud. Ces adresses se lisent dans la
colonne `INTERNAL-IP`. La commande `awk` ne garde que trois colonnes :

```bash
kubectl get nodes -o wide | awk '{print $1, $2, $6}' | column -t
```

```text
NAME        STATUS  INTERNAL-IP
k8s-cp.lab  Ready   10.10.50.11
k8s-w1.lab  Ready   10.10.50.12
```

## 📚 Exercice 2 : un Service NodePort

`kubectl expose` crée le Service. L'option `--type=NodePort` en fait un
NodePort :

```bash
kubectl expose deployment vitrine --type=NodePort --port=80 --target-port=8080 -n essai-nodeport
kubectl get service vitrine -n essai-nodeport
kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0]}{"\n"}'
```

```text
service/vitrine exposed
NAME      TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.101.247.28   <none>        80:30275/TCP   0s
{"nodePort":30275,"port":80,"protocol":"TCP","targetPort":8080}
```

La colonne `PORT(S)` dit `80:30275`. Un Service NodePort a en effet **trois**
ports :

- `port` (80) : le port du Service à l'intérieur du cluster ;
- `targetPort` (8080) : le port du conteneur, où arrivent les requêtes ;
- `nodePort` (30275) : le port ouvert sur **chaque nœud**. Vous ne l'avez pas
  choisi : Kubernetes l'a tiré au hasard dans sa plage, de 30000 à 32767.

## 📚 Exercice 3 : joindre l'application par chaque nœud

Interrogez le port du nœud sur les deux nœuds. La variable `NP` reprend le
`nodePort`, puisqu'il a été tiré au hasard. Le `sleep 3` laisse au cluster le
temps d'ouvrir ce port sur les nœuds :

```bash
sleep 3; NP=$(kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

Les deux nœuds répondent. Passez maintenant l'application à un seul Pod, puis
regardez sur quel nœud il tourne :

```bash
kubectl scale deployment vitrine --replicas=1 -n essai-nodeport
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
sleep 10; kubectl get pods -n essai-nodeport -o wide | awk '{print $1, $3, $7}' | column -t
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
NAME                      STATUS   NODE
vitrine-668ff869cd-68fq5  Running  k8s-cp.lab
```

Le seul Pod tourne sur `k8s-cp.lab`. Interrogez encore les deux nœuds :

```bash
curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

`k8s-w1.lab` répond aussi, alors qu'il n'a aucun Pod de `vitrine`. Le port est
ouvert sur **tous** les nœuds, et chacun transmet la requête au Pod, où qu'il
tourne.

## 📚 Exercice 4 : choisir le port du nœud

Un port tiré au hasard ne convient pas à des utilisateurs : il faut leur
donner une adresse fixe. Fixez le `nodePort` à `30095` avec `kubectl patch`.
Le port est désigné par son `port` (80), pour que Kubernetes sache lequel
modifier :

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"nodePort":30095}]}}'
kubectl get service vitrine -n essai-nodeport
sleep 3; curl -s http://10.10.50.11:30095/
```

```text
service/vitrine patched
NAME      TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.101.247.28   <none>        80:30095/TCP   14s
vitrine
```

`80:30095` : le port du nœud est désormais celui que vous avez choisi.

## 📚 Exercice 5 : un port hors de la plage

Essayez un port du nœud plus facile à retenir, `8080` :

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"nodePort":8080}]}}'
kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}{"\n"}'
```

```text
The Service "vitrine" is invalid: spec.ports[0].nodePort: Invalid value: 8080: provided port is not in the valid range. The range of valid ports is 30000-32767
30095
```

Refusé, et le Service garde `30095`. Le port d'un nœud doit être dans la plage
réservée à cet usage, de 30000 à 32767. Elle évite qu'un Service prenne le port
d'un programme du nœud lui-même, comme SSH (22).

## 📚 Exercice 6 : un port de nœud déjà pris

Un port de nœud est ouvert sur tous les nœuds : deux Services ne peuvent donc
pas avoir le même. `kubectl create service nodeport` crée un Service NodePort
sans partir d'un Deployment. Essayez d'en créer un second sur `30095`, puis
sur `30096` :

```bash
kubectl create service nodeport vitrine-bis --tcp=80:8080 --node-port=30095 -n essai-nodeport
kubectl create service nodeport vitrine-bis --tcp=80:8080 --node-port=30096 -n essai-nodeport
kubectl get services -n essai-nodeport
```

```text
error: failed to create NodePort service: Service "vitrine-bis" is invalid: spec.ports[0].nodePort: Invalid value: 30095: provided port is already allocated
service/vitrine-bis created
NAME          TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
vitrine       NodePort   10.101.247.28   <none>        80:30095/TCP   17s
vitrine-bis   NodePort   10.103.51.183   <none>        80:30096/TCP   0s
```

`provided port is already allocated` : `30095` appartient déjà au Service
`vitrine`, dans tout le cluster, quel que soit le namespace. `30096` est libre.

## 📚 Exercice 7 : fermer les nœuds sans Pod

Par défaut, un nœud sans Pod transmet la requête à un Pod d'un autre nœud,
comme à l'exercice 3. Ce détour masque l'adresse du client. Le réglage
`externalTrafficPolicy: Local` le supprime : chaque nœud ne sert que ses
propres Pods. Le Pod unique tourne toujours sur `k8s-cp.lab`. Passez le
Service en `Local`, puis interrogez les deux nœuds :

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"externalTrafficPolicy":"Local"}}'
sleep 3
curl -s -m 3 http://10.10.50.11:30095/ || echo "pas de réponse (code $?)"
curl -s -m 3 http://10.10.50.12:30095/ || echo "pas de réponse (code $?)"
```

```text
service/vitrine patched
vitrine
pas de réponse (code 28)
```

`k8s-w1.lab`, sans Pod de `vitrine`, ne répond plus : `curl` abandonne au bout
des 3 secondes de `-m 3` (code 28). Un utilisateur qui passe par ce nœud
n'atteint plus l'application.

Vérifiez-le depuis votre poste, hors du cluster. Ouvrez un second terminal sur
votre machine, celle d'où vous lancez `dsoxlab`, et lancez les deux mêmes
`curl` :

```text
vitrine
pas de réponse (code 28)
```

Même résultat. Attention : si votre Pod tourne sur `k8s-w1.lab`, c'est
`k8s-cp.lab` qui ne répondra pas depuis votre poste. Depuis `k8s-cp.lab`
lui-même, il répondra quand même, car un nœud répond toujours au trafic qu'il
émet lui-même : vérifiez toujours un réglage `Local` depuis une autre machine.

Repassez à deux Pods, un par nœud :

```bash
kubectl scale deployment vitrine --replicas=2 -n essai-nodeport
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
sleep 10; kubectl get pods -n essai-nodeport -o wide | awk '{print $1, $3, $7}' | column -t
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
NAME                      STATUS   NODE
vitrine-668ff869cd-68fq5  Running  k8s-cp.lab
vitrine-668ff869cd-n6zkt  Running  k8s-w1.lab
```

Depuis votre poste, les deux nœuds répondent de nouveau :

```text
vitrine
vitrine
```

Avec `Local`, un nœud ne répond que s'il porte un Pod de l'application.

## 🧹 Nettoyage

Supprimez d'abord ce que vous avez créé pendant les exercices : le namespace
d'essai, avec ses deux Services.

```bash
kubectl delete namespace essai-nodeport
```

```text
namespace "essai-nodeport" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-service-nodeport-reparer
dsoxlab check ckad-service-nodeport-reparer
```

```text
╭─ Résultat : ckad-service-nodeport-reparer ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests           │
╰────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une application que personne ne joint, derrière un
Service NodePort mal écrit. Trouvez ce qui cloche et réparez-le.

```bash
dsoxlab run ckad-service-nodeport-reparer
dsoxlab challenge ckad-service-nodeport-reparer
```
