# Cloisonner trois tiers avec des NetworkPolicy ingress et egress

La leçon montre des NetworkPolicies qui filtrent l'entrée et la sortie des
Pods. Ce cours se concentre sur la sortie (egress), mesurée port par port, et
ajoute des cas que la leçon ne montre pas : une plage de ports avec `endPort`,
une sortie ouverte vers l'adresse d'un Service qui ne marche pas, un port
autorisé vers n'importe quelle destination, et une sortie vers un Pod d'un
autre namespace.

Vous travaillez dans un namespace d'essai, `essai-sortie`, avec un serveur
`ports` qui écoute sur plusieurs ports et un client `poste`, puis dans un
second namespace, `essai-voisin`. Le challenge porte sur d'autres objets :
vous le ferez seul, à la fin.

Page associée : [Network Policies](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-networkpolicy-ingress-egress
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le réseau des Pods est
fourni par Calico, qui applique les NetworkPolicies.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace, le serveur et le client. Le serveur `ports` (image
agnhost, mode `porter`) écoute sur les ports 8000, 8050, 8099 et 9000. Un
Service l'expose sur le port 80, renvoyé vers 8000 :

```bash
kubectl create namespace essai-sortie
kubectl run ports --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-sortie --labels=app=ports --env=SERVE_PORT_8000=a --env=SERVE_PORT_8050=b --env=SERVE_PORT_8099=c --env=SERVE_PORT_9000=d -- porter; kubectl expose pod ports --port=80 --target-port=8000 -n essai-sortie; kubectl run poste --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sortie --labels=app=poste -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-sortie --timeout=120s
```

```text
namespace/essai-sortie created
pod/ports created
service/ports exposed
pod/poste created
pod/ports condition met
pod/poste condition met
```

Chaque essai de ce cours lance `nc -z` depuis `poste` vers l'adresse du Pod
`ports`, sur chaque port, avec un délai de 3 secondes. `ouvert` veut dire que
la connexion a réussi. Sans politique, tout passe :

```bash
IP=$(kubectl get pod ports -n essai-sortie -o jsonpath='{.status.podIP}'); for p in 8000 8050 8099 9000; do printf '%-5s -> ' $p; kubectl exec poste -n essai-sortie -- nc -z -w 3 $IP $p >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
8000  -> ouvert
8050  -> ouvert
8099  -> ouvert
9000  -> ouvert
```

## 🎚️ Exercice 1 : une plage de ports

Une politique de sortie s'applique au Pod qui émet, ici `poste`. Autorisez sa
sortie vers `ports`, sur la plage 8000 à 8050, avec `port` et `endPort` :

```bash
cat <<'YAML' | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels: {app: ports}
      ports:
        - protocol: TCP
          port: 8000
          endPort: 8050
YAML
```

```text
sleep 5
networkpolicy.networking.k8s.io/poste-sortie created
```

```bash
IP=$(kubectl get pod ports -n essai-sortie -o jsonpath='{.status.podIP}'); for p in 8000 8050 8099 9000; do printf '%-5s -> ' $p; kubectl exec poste -n essai-sortie -- nc -z -w 3 $IP $p >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
8000  -> ouvert
8050  -> ouvert
8099  -> ferme
9000  -> ferme
```

8000 et 8050 passent : les deux bornes sont comprises dans la plage. 8099 et
9000 sont bloqués. Dès qu'une politique de type `Egress` vise un Pod, toute
sortie qu'elle n'autorise pas est refusée, y compris vers le DNS du cluster.
Les essais utilisent donc l'adresse du Pod et non son nom.

## 🎯 Exercice 2 : ouvrir la sortie vers l'adresse du Service

Idée tentante : autoriser la sortie vers l'adresse du Service, avec un
`ipBlock` en `/32`. La commande lit cette adresse, l'écrit dans la politique,
puis appelle le Service sur son port 80 :

```bash
SVC=$(kubectl get service ports -n essai-sortie -o jsonpath='{.spec.clusterIP}'); echo "Service : $SVC"; cat <<YAML | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - to:
        - ipBlock: {cidr: $SVC/32}
      ports:
        - {protocol: TCP, port: 8000}
YAML
sleep 5; kubectl exec poste -n essai-sortie -- nc -z -w 3 $SVC 80; echo "vers le Service : code $?"
```

```text
Service : 10.96.156.194
networkpolicy.networking.k8s.io/poste-sortie configured
command terminated with exit code 1
vers le Service : code 1
```

Refusé, alors que la politique vise exactement l'adresse appelée. L'adresse
d'un Service n'est qu'une étape : avant que le paquet quitte le nœud, elle est
remplacée par celle d'un Pod derrière le Service. Regardez laquelle :

```bash
kubectl get endpointslices -n essai-sortie -l kubernetes.io/service-name=ports -o jsonpath='{.items[0].endpoints[0].addresses[0]}{"\n"}'
```

```text
10.244.38.73
```

Calico compare la politique à cette adresse de Pod, sur le port 8000, pas à
celle du Service. Une politique se rédige donc vers les Pods, avec
`podSelector`, comme à l'exercice 1, et jamais vers l'adresse d'un Service.

## 🌐 Exercice 3 : un port vers n'importe quelle destination

Une règle `egress` sans champ `to` vaut pour toutes les destinations.
Autorisez seulement le port 9000, vers n'importe où :

```bash
cat <<'YAML' | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - ports:
        - {protocol: TCP, port: 9000}
YAML
```

```text
sleep 5
networkpolicy.networking.k8s.io/poste-sortie configured
```

```bash
IP=$(kubectl get pod ports -n essai-sortie -o jsonpath='{.status.podIP}'); for p in 8000 9000; do printf '%-5s -> ' $p; kubectl exec poste -n essai-sortie -- nc -z -w 3 $IP $p >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
8000  -> ferme
9000  -> ouvert
```

9000 passe, 8000 non : la plage de l'exercice 1 a disparu, car la politique a
été remplacée (même nom, `configured`).

## 🏘️ Exercice 4 : une sortie vers un autre namespace

Créez un second namespace avec un serveur `voisin` :

```bash
kubectl create namespace essai-voisin; kubectl run voisin --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-voisin --labels=app=voisin; kubectl wait --for=condition=Ready pod/voisin -n essai-voisin --timeout=120s
```

```text
namespace/essai-voisin created
pod/voisin created
pod/voisin condition met
```

Autorisez la sortie vers le Pod `app=voisin` du namespace `essai-voisin`. Le
`namespaceSelector` et le `podSelector` sont dans le même élément de la liste
`to` (un seul tiret) : il faut que les deux conditions soient vraies. Chaque
namespace porte automatiquement l'étiquette `kubernetes.io/metadata.name` :

```bash
cat <<'YAML' | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels: {kubernetes.io/metadata.name: essai-voisin}
          podSelector:
            matchLabels: {app: voisin}
      ports:
        - {protocol: TCP, port: 80}
YAML
```

```text
sleep 5; V=$(kubectl get pod voisin -n essai-voisin -o jsonpath='{.status.podIP}'); kubectl exec poste -n essai-sortie -- nc -z -w 3 $V 80; echo "vers voisin : code $?"
networkpolicy.networking.k8s.io/poste-sortie configured
vers voisin : code 0
```

La connexion passe. Changez l'étiquette du Pod voisin et réessayez :

```bash
kubectl label pod voisin -n essai-voisin app=autre --overwrite; sleep 5; V=$(kubectl get pod voisin -n essai-voisin -o jsonpath='{.status.podIP}'); kubectl exec poste -n essai-sortie -- nc -z -w 3 $V 80; echo "vers voisin relabellisé : code $?"
```

```text
pod/voisin labeled
command terminated with exit code 1
vers voisin relabellisé : code 1
```

Refusé : le namespace correspond toujours, mais plus le Pod. Selon la
spécification, avec deux tirets (`- namespaceSelector` puis `- podSelector`),
les deux conditions seraient devenues deux autorisations séparées, et la seconde aurait visé les Pods
`app=voisin` du namespace de la politique. Un tiret de trop ou de moins change
le sens de la règle.

## 🧹 Nettoyage

Supprimez les deux namespaces d'essai :

```bash
kubectl delete namespace essai-sortie essai-voisin
```

```text
namespace "essai-sortie" deleted
namespace "essai-voisin" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-networkpolicy-ingress-egress
dsoxlab check ckad-networkpolicy-ingress-egress
```

```text
╭─ Résultat : ckad-networkpolicy-ingress-egress ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests               │
╰────────────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : trois tiers à cloisonner, en entrée et en sortie.

```bash
dsoxlab run ckad-networkpolicy-ingress-egress
dsoxlab challenge ckad-networkpolicy-ingress-egress
```
