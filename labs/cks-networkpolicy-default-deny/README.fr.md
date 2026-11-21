# Tout interdire, puis rouvrir le strict nécessaire, DNS compris

La leçon montre le modèle zéro-confiance : une politique qui ferme tout, puis
des politiques qui rouvrent les flux utiles. Ce cours mesure chaque étape et
ajoute des cas que la leçon ne montre pas : un Pod créé après la fermeture, un
« port 53 ouvert partout » qui laisse passer bien plus que le DNS, le trafic
de réponse, l'API server derrière une sortie fermée, et une étiquette retirée
qui coupe un accès.

Vous travaillez dans un namespace d'essai, `essai-zc`, avec un serveur
`caisse` (nginx) et un client `comptoir` (busybox), puis dans un second
namespace, `essai-dehors`. Le challenge porte sur d'autres objets : vous le
ferez seul, à la fin.

Page associée : [Network Policies](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-networkpolicy-default-deny
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le réseau des Pods est
fourni par Calico, qui applique les NetworkPolicies.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et busybox 1.38.

Créez le namespace, le serveur exposé par un Service, et le client :

```bash
kubectl create namespace essai-zc; kubectl run caisse --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-zc --labels=app=caisse; kubectl expose pod caisse --port=80 -n essai-zc; kubectl run comptoir --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-zc --labels=app=comptoir -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-zc --timeout=120s
```

```text
namespace/essai-zc created
pod/caisse created
service/caisse exposed
pod/comptoir created
pod/caisse condition met
pod/comptoir condition met
```

## 🔒 Exercice 1 : tout fermer, y compris pour les Pods à venir

Avec `podSelector: {}`, une politique vise tous les Pods du namespace. Avec
les deux types `Ingress` et `Egress` et aucune règle, elle ferme l'entrée et
la sortie :

```bash
cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tout-fermer
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io/tout-fermer created
```

Créez un Pod après la politique, puis essayez de joindre `caisse` depuis
l'ancien et le nouveau client :

```bash
kubectl run tardif --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-zc -- sleep 3600; kubectl wait --for=condition=Ready pod/tardif -n essai-zc --timeout=120s; C=$(kubectl get pod caisse -n essai-zc -o jsonpath='{.status.podIP}'); for p in comptoir tardif; do printf '%-9s -> caisse : ' $p; kubectl exec $p -n essai-zc -- nc -z -w 3 $C 80 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
pod/tardif created
pod/tardif condition met
comptoir  -> caisse : ferme
tardif    -> caisse : ferme
```

`tardif` est fermé lui aussi : le sélecteur vide s'applique aux Pods présents
et à venir. Essayez maintenant une résolution de nom :

```bash
kubectl exec tardif -n essai-zc -- nslookup -timeout=3 kubernetes.default; echo "code $?"
```

```text
;; connection timed out; no servers could be reached

command terminated with exit code 1
code 1
```

Plus aucun serveur DNS n'est joignable : la sortie fermée bloque aussi les
questions DNS. C'est la première chose qui casse après une fermeture totale.

## 🕳️ Exercice 2 : un port 53 ouvert vers partout

Un serveur `relais` dans un autre namespace écoute en HTTP sur le port 53,
celui du DNS :

```bash
kubectl create namespace essai-dehors; kubectl run relais --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-dehors -- netexec --http-port=53; kubectl wait --for=condition=Ready pod/relais -n essai-dehors --timeout=120s
```

```text
namespace/essai-dehors created
pod/relais created
pod/relais condition met
```

Rouvrez la sortie sur le port 53, en UDP et en TCP, sans préciser de
destination. La commande teste ensuite une résolution, puis un appel HTTP
vers `relais` sur le port 53. Le nom est écrit en entier avec un point final,
pour que busybox ne parcoure pas sa liste de recherche :

```bash
cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-large
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
YAML
sleep 5; R=$(kubectl get pod relais -n essai-dehors -o jsonpath='{.status.podIP}'); kubectl exec comptoir -n essai-zc -- nslookup kubernetes.default.svc.cluster.local. | grep -A1 Name; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 "http://$R:53/hostname"; echo
```

```text
networkpolicy.networking.k8s.io/dns-large created
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
relais
```

Le DNS remarche, et `relais` répond aussi. La règle autorise le port 53 vers
n'importe quelle adresse, quel que soit ce qui écoute derrière. Un programme
qui veut sortir du namespace n'a qu'à utiliser ce port. Remplacez-la par une
règle qui vise seulement les Pods du DNS du cluster, dans `kube-system` :

```bash
kubectl delete networkpolicy dns-large -n essai-zc; cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-strict
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels: {kubernetes.io/metadata.name: kube-system}
          podSelector:
            matchLabels: {k8s-app: kube-dns}
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
YAML
sleep 5; R=$(kubectl get pod relais -n essai-dehors -o jsonpath='{.status.podIP}'); kubectl exec comptoir -n essai-zc -- nslookup kubernetes.default.svc.cluster.local. | grep -A1 Name; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 "http://$R:53/hostname"; echo "wget : code $?"
```

```text
networkpolicy.networking.k8s.io "dns-large" deleted from essai-zc namespace
networkpolicy.networking.k8s.io/dns-strict created
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
wget: download timed out
command terminated with exit code 1
wget : code 1
```

Le DNS répond toujours, mais `relais` ne passe plus. Une ouverture pour le
DNS se rédige donc avec sa destination : le namespace `kube-system` et
l'étiquette `k8s-app: kube-dns` des Pods CoreDNS.

## ↩️ Exercice 3 : la réponse passe, l'initiative inverse non

Rouvrez le flux de `comptoir` vers `caisse` sur le port 80. Il faut deux
politiques : une sortie pour `comptoir` et une entrée pour `caisse`, car la
fermeture totale bloque les deux côtés :

```bash
cat <<'YAML' | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: comptoir-vers-caisse
spec:
  podSelector:
    matchLabels: {app: comptoir}
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels: {app: caisse}
      ports:
        - {protocol: TCP, port: 80}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: caisse-depuis-comptoir
spec:
  podSelector:
    matchLabels: {app: caisse}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: comptoir}
      ports:
        - {protocol: TCP, port: 80}
YAML
sleep 5; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 http://caisse | grep -o '<title>.*</title>'
```

```text
networkpolicy.networking.k8s.io/comptoir-vers-caisse created
networkpolicy.networking.k8s.io/caisse-depuis-comptoir created
<title>Welcome to nginx!</title>
```

La page arrive. Vous n'avez rien ouvert pour la réponse de `caisse` vers
`comptoir` : Calico suit la connexion, et la réponse passe avec elle.
Maintenant, faites partir une connexion dans l'autre sens, depuis `caisse`
vers `comptoir` :

```bash
P=$(kubectl get pod comptoir -n essai-zc -o jsonpath='{.status.podIP}'); kubectl exec caisse -n essai-zc -- sh -c "curl -s -m 3 -o /dev/null 'http://$P:8080/'; echo code \$?"
```

```text
code 28
```

Code 28 : curl a abandonné au bout de son délai de 3 secondes. Un flux ouvert
dans un sens n'autorise que les réponses dans l'autre, jamais une connexion
nouvelle.

## 🎛️ Exercice 4 : joindre l'API server sous une sortie fermée

Un Pod qui parle à l'API (un opérateur, un outil de déploiement) a besoin
d'une sortie vers elle. Regardez les deux adresses de l'API : celle du
Service `kubernetes` et celle qui se trouve vraiment derrière :

```bash
kubectl get endpointslices -n default -l kubernetes.io/service-name=kubernetes -o jsonpath='{.items[0].endpoints[0].addresses[0]}:{.items[0].ports[0].port}{"\n"}'; kubectl get service kubernetes -n default -o jsonpath='{.spec.clusterIP}:{.spec.ports[0].port}{"\n"}'
```

```text
10.10.50.11:6443
10.96.0.1:443
```

Le Service répond en `10.96.0.1:443`, mais l'API server écoute en
`10.10.50.11:6443`, l'adresse du control plane. Ouvrez la sortie vers cette
adresse, sur le port 443 du Service, et testez :

```bash
API=$(kubectl get endpointslices -n default -l kubernetes.io/service-name=kubernetes -o jsonpath='{.items[0].endpoints[0].addresses[0]}'); cat <<YAML | kubectl apply -n essai-zc -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vers-api
spec:
  podSelector:
    matchLabels: {app: comptoir}
  policyTypes: [Egress]
  egress:
    - to:
        - ipBlock: {cidr: $API/32}
      ports:
        - {protocol: TCP, port: 443}
YAML
sleep 5; kubectl exec comptoir -n essai-zc -- nc -z -w 3 kubernetes.default 443; echo "port 443 : code $?"
```

```text
networkpolicy.networking.k8s.io/vers-api created
command terminated with exit code 1
port 443 : code 1
```

Refusé. L'adresse et le port du Service sont remplacés par ceux de l'API
server avant que la politique soit vérifiée : Calico voit le port 6443, pas
443.
Corrigez le port de la règle :

```bash
kubectl patch networkpolicy vers-api -n essai-zc --type json -p '[{"op":"replace","path":"/spec/egress/0/ports/0/port","value":6443}]'; sleep 5; kubectl exec comptoir -n essai-zc -- nc -z -w 3 kubernetes.default 443; echo "port 6443 autorisé : code $?"
```

```text
networkpolicy.networking.k8s.io/vers-api patched
port 6443 autorisé : code 0
```

Le client appelle toujours `kubernetes.default` sur le port 443, mais la
règle doit nommer le port 6443. Une règle vers l'API se lit sur
l'EndpointSlice du Service `kubernetes`, pas sur le Service.

## 🏷️ Exercice 5 : une étiquette retirée coupe l'accès

Retirez l'étiquette `app` de `comptoir` (le `-` final supprime l'étiquette),
puis rappelez `caisse` :

```bash
kubectl label pod comptoir -n essai-zc app-; sleep 5; kubectl exec comptoir -n essai-zc -- wget -qO- -T 3 http://caisse >/dev/null; echo "code $?"
```

```text
pod/comptoir unlabeled
wget: download timed out
command terminated with exit code 1
code 1
```

Les deux politiques de l'exercice 3 visaient `app=comptoir`. Sans
l'étiquette, `comptoir` ne reçoit plus que la fermeture totale, qui vise tous
les Pods. Dans un namespace en zéro-confiance, les étiquettes font partie des
règles de sécurité : les changer, c'est changer les accès.

## 🧹 Nettoyage

Supprimez les deux namespaces d'essai :

```bash
kubectl delete namespace essai-zc essai-dehors
```

```text
namespace "essai-zc" deleted
namespace "essai-dehors" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-networkpolicy-default-deny
dsoxlab check cks-networkpolicy-default-deny
```

```text
╭─ Résultat : cks-networkpolicy-default-deny ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests            │
╰─────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un namespace à fermer entièrement, puis à rouvrir
pour le seul flux utile, sans casser la résolution des noms.

```bash
dsoxlab run cks-networkpolicy-default-deny
dsoxlab challenge cks-networkpolicy-default-deny
```
