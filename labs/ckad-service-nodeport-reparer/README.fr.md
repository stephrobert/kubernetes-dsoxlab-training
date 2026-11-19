# Ouvrir une application hors du cluster avec un Service NodePort

Un Service de type `ClusterIP` n'est joignable que depuis l'intérieur du
cluster. Pour qu'un utilisateur, à l'extérieur, joigne l'application, le type
**NodePort** ouvre en plus un port sur **chaque nœud** du cluster. Une requête
envoyée à ce port, sur n'importe quel nœud, arrive à l'un des Pods. Dans ce
cours, vous créez un Service NodePort, vous le joignez par chaque nœud, vous
choisissez son port, puis vous réparez un Service NodePort qui ne mène nulle
part.

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
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : l'application, et les adresses des nœuds

Créez le namespace d'essai :

```bash
kubectl create namespace essai-nodeport
```

```text
namespace/essai-nodeport created
```

L'application `vitrine` tourne en deux Pods, qui servent le texte `vitrine` sur
le port 8080. Le champ `terminationGracePeriodSeconds: 5` raccourcit l'arrêt
d'un Pod : le petit serveur `httpd` ignore le signal d'arrêt, et Kubernetes
attendrait sinon 30 secondes avant de le couper.

```bash
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
          command: ["sh", "-c", "echo vitrine > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - containerPort: 8080
YAML
kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
```

```text
deployment.apps/vitrine created
deployment "vitrine" successfully rolled out
```

Un NodePort se joint par l'adresse d'un nœud. Ces adresses se lisent dans la
colonne `INTERNAL-IP` de `kubectl get nodes -o wide`. La commande `awk` ne
garde que trois colonnes, pour que la sortie tienne à l'écran :

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
```

```text
service/vitrine exposed
NAME      TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.104.107.240   <none>        80:32338/TCP   0s
```

La colonne `PORT(S)` dit `80:32338`. Un Service NodePort a en effet **trois**
ports, que le détail montre tous :

```bash
kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0]}{"\n"}'
```

```text
{"nodePort":32338,"port":80,"protocol":"TCP","targetPort":8080}
```

- `port` (80) : le port du Service à l'intérieur du cluster ;
- `targetPort` (8080) : le port du conteneur, où arrivent les requêtes ;
- `nodePort` (32338) : le port ouvert sur **chaque nœud**. Vous ne l'avez pas
  choisi : Kubernetes l'a tiré au hasard dans sa plage, de 30000 à 32767.

## 📚 Exercice 3 : joindre l'application par chaque nœud

Interrogez le port du nœud sur les deux nœuds. La variable `NP` reprend le
`nodePort`, puisqu'il a été tiré au hasard. Le `sleep 3` laisse au cluster le
temps d'ouvrir ce port sur les nœuds :

```bash
sleep 3; NP=$(kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}'); curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

Les deux nœuds répondent. Passez maintenant l'application à un seul Pod, puis
regardez sur quel nœud il tourne :

```bash
kubectl scale deployment vitrine --replicas=1 -n essai-nodeport && kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
sleep 8; kubectl get pods -n essai-nodeport -o wide | awk '{print $1, $3, $7}' | column -t
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
NAME                      STATUS   NODE
vitrine-549565bb45-fgxbm  Running  k8s-cp.lab
```

Le seul Pod tourne sur `k8s-cp.lab`. Interrogez encore les deux nœuds :

```bash
NP=$(kubectl get service vitrine -n essai-nodeport -o jsonpath='{.spec.ports[0].nodePort}'); curl -s "http://10.10.50.11:$NP/"; curl -s "http://10.10.50.12:$NP/"
```

```text
vitrine
vitrine
```

`k8s-w1.lab` répond aussi, alors qu'il n'a aucun Pod de `vitrine`. Le port est
ouvert sur **tous** les nœuds, et chacun transmet la requête au Pod, où qu'il
tourne. Repassez à deux Pods :

```bash
kubectl scale deployment vitrine --replicas=2 -n essai-nodeport && kubectl rollout status deployment/vitrine -n essai-nodeport --timeout=120s | tail -1
```

```text
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
```

## 📚 Exercice 4 : choisir le port du nœud

Un port tiré au hasard ne convient pas à des utilisateurs : il faut leur
donner une adresse fixe. Fixez le `nodePort` à `30095` avec `kubectl patch`.
Le port est désigné par son `port` (80), pour que Kubernetes sache lequel
modifier :

```bash
kubectl patch service vitrine -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"nodePort":30095}]}}'
kubectl get service vitrine -n essai-nodeport
```

```text
service/vitrine patched
NAME      TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
vitrine   NodePort   10.104.107.240   <none>        80:30095/TCP   12s
```

`80:30095` : le port du nœud est désormais celui que vous avez choisi.

```bash
sleep 3; curl -s http://10.10.50.11:30095/
```

```text
vitrine
```

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

## 📚 Exercice 6 : réparer un Service qui ne mène nulle part

`kubectl create service nodeport` crée un Service NodePort sans partir d'un
Deployment. Créez-en un, `vitrine-cassee`, sur le port de nœud `30096`, avec un
port cible faux, `9090` :

```bash
kubectl create service nodeport vitrine-cassee --tcp=80:9090 --node-port=30096 -n essai-nodeport
kubectl get service vitrine-cassee -n essai-nodeport -o jsonpath='{.spec.selector}{"\n"}'
```

```text
service/vitrine-cassee created
{"app":"vitrine-cassee"}
```

Sans Deployment à copier, la commande a pris un sélecteur d'après le nom du
Service : `app=vitrine-cassee`. Aucun Pod ne porte ce label. Regardez les
endpoints, puis essayez le port du nœud :

```bash
kubectl get endpointslices -n essai-nodeport -l kubernetes.io/service-name=vitrine-cassee
sleep 3; curl -s -m 3 http://10.10.50.11:30096/ || echo "pas de réponse (code $?)"
```

```text
NAME                   ADDRESSTYPE   PORTS     ENDPOINTS   AGE
vitrine-cassee-w6v8m   IPv4          <unset>   <unset>     1s
pas de réponse (code 7)
```

Aucun endpoint, et `curl` sort en code 7 : la connexion est refusée. Premier
défaut, le sélecteur. Corrigez-le pour qu'il vise les Pods de `vitrine` :

```bash
kubectl set selector service vitrine-cassee app=vitrine -n essai-nodeport
sleep 3; kubectl get endpointslices -n essai-nodeport -l kubernetes.io/service-name=vitrine-cassee
curl -s -m 3 http://10.10.50.11:30096/ || echo "pas de réponse (code $?)"
```

```text
service/vitrine-cassee selector updated
NAME                   ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
vitrine-cassee-w6v8m   IPv4          9090    10.244.38.112,10.244.163.40   7s
pas de réponse (code 7)
```

Les deux Pods sont maintenant des endpoints, mais sur le port `9090`, où rien
n'écoute. Toujours pas de réponse. Second défaut, le port cible. Corrigez-le :

```bash
kubectl patch service vitrine-cassee -n essai-nodeport -p '{"spec":{"ports":[{"port":80,"targetPort":8080}]}}'
sleep 3; curl -s -m 3 http://10.10.50.11:30096/ || echo "pas de réponse (code $?)"
```

```text
service/vitrine-cassee patched
vitrine
```

L'application répond. Pour réparer un Service, avancez dans cet ordre :
d'abord les endpoints (le sélecteur), puis le port cible, puis le port du
nœud.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec tout ce qu'il contient :

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
