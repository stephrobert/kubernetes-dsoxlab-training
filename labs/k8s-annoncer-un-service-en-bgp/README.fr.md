# Annoncer un Service en BGP

La leçon active le plan de contrôle BGP de Cilium, monte les sessions avec
un routeur et lui annonce le réseau des Pods et les adresses de
LoadBalancer. C'est aussi le challenge du lab : ce cours laisse BGP éteint.
Il travaille sur la moitié du sujet qui se règle sans lui, l'attribution des
adresses de LoadBalancer par Cilium (LB IPAM) : ce que dit un agent quand
BGP est éteint, une adresse attribuée qui n'est annoncée à personne, un pool
qui s'épuise, une adresse partagée par deux Services, et une adresse demandée
hors du pool.

Vous travaillez dans le namespace `essai-bgp`, avec un pool d'essai
`172.31.0.0/30` réservé à ce namespace. Le challenge porte sur un autre pool,
un autre Service et les sessions BGP : vous le ferez seul, à la fin.

Page associée : [Annoncer des Services en BGP](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/annoncer-services-bgp/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-annoncer-un-service-en-bgp
```

Vous êtes maintenant connecté à `net-cp.lab`, le plan de contrôle du cluster
Cilium. Le routeur du lab tourne hors du cluster ; vous ne le touchez pas
dans ce cours.

Les sorties montrées dans ce cours ont été relevées sur ces machines le
22 novembre 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🔌 Exercice 1 : ce que dit un agent quand BGP est éteint

Avant de chercher pourquoi un routeur ne voit pas le cluster, vérifiez que
le cluster parle BGP. Interrogez un agent, la configuration de Cilium, puis
le port 179, celui de BGP, sur un worker :

```bash
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg bgp peers; echo "code=$?"
kubectl -n kube-system get cm cilium-config -o yaml | grep -c bgp
ssh net-w1.lab 'sudo ss -ltn "sport = :179"'
```

```text
BGP Control Plane is disabled
code=0
0
State Recv-Q Send-Q Local Address:Port Peer Address:PortProcess
```

L'agent répond `BGP Control Plane is disabled`, mais sort en **0** : un
script qui ne regarde que le code de sortie croirait que tout va bien. La
configuration de Cilium ne contient pas une seule ligne qui parle de BGP, et
personne n'écoute sur le port 179 du worker. Un routeur qui tente de joindre
ces nœuds reste donc en `Active`, sans jamais obtenir de session.

## 🏷️ Exercice 2 : une adresse attribuée n'est pas une adresse annoncée

LB IPAM attribue les adresses de LoadBalancer, même quand BGP est éteint.
Créez un pool d'essai limité au namespace `essai-bgp` par son
`serviceSelector`, puis une application et un Service LoadBalancer :

```bash
kubectl create namespace essai-bgp; cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: essai-pool
spec:
  allowFirstLastIPs: "No"
  blocks:
    - cidr: 172.31.0.0/30
  serviceSelector:
    matchLabels:
      io.kubernetes.service.namespace: essai-bgp
YAML
kubectl -n essai-bgp create deployment essai-web --image=nginx:1.30.6 --replicas=1
kubectl -n essai-bgp expose deployment essai-web --name=essai-a --type=LoadBalancer --port 80
kubectl -n essai-bgp rollout status deployment essai-web --timeout=120s
sleep 5; kubectl -n essai-bgp get svc essai-a
```

```text
namespace/essai-bgp created
ciliumloadbalancerippool.cilium.io/essai-pool created
deployment.apps/essai-web created
service/essai-a exposed
Waiting for deployment "essai-web" rollout to finish: 0 of 1 updated replicas are available...
deployment "essai-web" successfully rolled out
NAME      TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
essai-a   LoadBalancer   10.100.225.168   172.31.0.1    80:32739/TCP   6s
```

Le Service a reçu `172.31.0.1`. Le `serviceSelector` compte : sans lui, le
pool servirait aussi le Service `web` du challenge, qui attend encore son
adresse. Appelez maintenant cette adresse depuis `net-cp`, et regardez la
route que le noyau choisit pour elle :

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://172.31.0.1/
ip route get 172.31.0.1
```

```text
200
172.31.0.1 via 10.10.50.1 dev enp1s0 src 10.10.50.14 uid 1001
    cache
```

L'adresse répond `200`, et pourtant le noyau l'enverrait vers la passerelle
`10.10.50.1`, qui ne la connaît pas. Sur un nœud du cluster, c'est Cilium qui
intercepte l'appel et le sert lui-même, avant toute route. **Un test lancé
depuis un nœud ne prouve donc rien sur l'annonce** : seul un appel depuis une
machine hors du cluster, comme le routeur du challenge, le prouve. Le
`sleep 5` n'est pas décoratif : lors d'un premier essai, le même `curl`,
lancé une seconde après la création du Service, a échoué. Laissez à Cilium
quelques secondes avant de conclure qu'une adresse ne répond pas.

## 🔢 Exercice 3 : un pool qui s'épuise

Le bloc `/30` compte quatre adresses, et le pool porte
`allowFirstLastIPs: "No"`, qui réserve la première et la dernière. Créez deux
Services de plus sur la même application :

```bash
kubectl -n essai-bgp expose deployment essai-web --name=essai-b --type=LoadBalancer --port 81 --target-port 80
kubectl -n essai-bgp expose deployment essai-web --name=essai-c --type=LoadBalancer --port 82 --target-port 80
sleep 5; kubectl -n essai-bgp get svc
kubectl -n essai-bgp get svc essai-c -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
```

```text
service/essai-b exposed
service/essai-c exposed
NAME      TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
essai-a   LoadBalancer   10.100.225.168   172.31.0.1    80:32739/TCP   11s
essai-b   LoadBalancer   10.109.116.46    172.31.0.2    81:30162/TCP   5s
essai-c   LoadBalancer   10.109.134.36    <pending>     82:30848/TCP   5s
cilium.io/IPAMRequestSatisfied=False out_of_ips: All enabled CiliumLoadBalancerIPPools that match this service ran out of allocatable IPs
```

Le pool n'a donné que `172.31.0.1` et `172.31.0.2` : `172.31.0.0` et
`172.31.0.3` sont bien réservées par `allowFirstLastIPs: "No"`. Le troisième
Service reste en `<pending>`, et la raison n'est pas dans les événements mais
dans les **conditions** du Service : `out_of_ips`.

## 🤝 Exercice 4 : deux Services sur une même adresse

Quand les adresses sont rares, deux Services peuvent partager la même, à
condition d'écouter sur des ports différents. L'annotation
`lbipam.cilium.io/sharing-key` les associe. Libérez le Service en attente,
donnez une clé à `essai-a`, puis créez un Service qui porte la même clé, sur
le port 8080 :

```bash
kubectl -n essai-bgp delete svc essai-c
kubectl -n essai-bgp annotate svc essai-a lbipam.cilium.io/sharing-key=vitrine
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: essai-d
  namespace: essai-bgp
  annotations:
    lbipam.cilium.io/sharing-key: vitrine
spec:
  type: LoadBalancer
  selector:
    app: essai-web
  ports:
    - port: 8080
      targetPort: 80
YAML
sleep 5; kubectl -n essai-bgp get svc
curl -s -o /dev/null -w '%{http_code}\n' http://172.31.0.1:8080/
```

```text
service "essai-c" deleted from essai-bgp namespace
service/essai-a annotated
service/essai-d created
NAME      TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
essai-a   LoadBalancer   10.100.225.168   172.31.0.1    80:32739/TCP     16s
essai-b   LoadBalancer   10.109.116.46    172.31.0.2    81:30162/TCP     10s
essai-d   LoadBalancer   10.104.163.211   172.31.0.1    8080:32018/TCP   5s
200
```

`essai-d` a reçu `172.31.0.1`, l'adresse de `essai-a`, alors que le pool
était plein : le partage ne consomme pas d'adresse. L'application répond sur
le port 8080 de cette adresse, comme sur le port 80.

## 🎯 Exercice 5 : une adresse demandée hors du pool

Un Service peut demander une adresse précise avec l'annotation
`lbipam.cilium.io/ips`. Demandez `172.31.0.9`, qui n'est dans aucun pool :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: essai-e
  namespace: essai-bgp
  annotations:
    lbipam.cilium.io/ips: 172.31.0.9
spec:
  type: LoadBalancer
  selector:
    app: essai-web
  ports:
    - port: 83
      targetPort: 80
YAML
sleep 5; kubectl -n essai-bgp get svc essai-e
kubectl -n essai-bgp get svc essai-e -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
```

```text
service/essai-e created
NAME      TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
essai-e   LoadBalancer   10.108.211.50   <pending>     83:31638/TCP   5s
cilium.io/IPAMRequestSatisfied=False no_pool: No pool exists with a CIDR containing '172.31.0.9'
```

Même symptôme qu'à l'exercice 3, `<pending>`, mais une autre raison :
`no_pool`, et le message nomme l'adresse demandée. Devant un Service en
`<pending>`, lisez toujours ses conditions avant de toucher au pool.

## 🧹 Nettoyage

Supprimez le namespace d'essai, puis le pool, qui n'est rattaché à aucun
namespace. Vérifiez que le Service du challenge attend toujours son adresse :

```bash
kubectl delete namespace essai-bgp --wait=true --timeout=120s
kubectl delete ciliumloadbalancerippool essai-pool
kubectl -n bgp-demo get svc web
```

```text
namespace "essai-bgp" deleted
ciliumloadbalancerippool.cilium.io "essai-pool" deleted
NAME   TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
web    LoadBalancer   10.98.192.205   <pending>     80:31147/TCP   3m28s
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-annoncer-un-service-en-bgp
dsoxlab check k8s-annoncer-un-service-en-bgp
```

```text
╭─ Résultat : k8s-annoncer-un-service-en-bgp ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests            │
╰─────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : activer BGP dans Cilium, monter les sessions avec
le routeur du réseau, et lui annoncer le réseau des Pods et l'adresse du
Service `web`.

```bash
dsoxlab run k8s-annoncer-un-service-en-bgp
dsoxlab challenge k8s-annoncer-un-service-en-bgp
```
