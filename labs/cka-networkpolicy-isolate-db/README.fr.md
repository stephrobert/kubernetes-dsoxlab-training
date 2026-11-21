# Isoler la base de données : seul le backend y accède

La leçon montre une NetworkPolicy qui ne laisse entrer qu'un client vers une
base de données. Ce cours mesure chaque règle par un essai de connexion, et
ajoute des cas que la leçon ne montre pas : un port désigné par son nom, une
liste de clients avec `matchExpressions`, deux politiques qui s'additionnent,
une sonde du kubelet qui passe sous un refus total, et un client qui partage
le réseau d'un nœud.

Vous travaillez dans un namespace d'essai, `essai-np`, avec un serveur
`coffre` et quatre clients : `guichet`, `migration`, `sauvegarde` et
`curieux`. Le challenge porte sur d'autres objets : vous le ferez seul, à la
fin.

Page associée : [Network Policies](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/network-policies/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-networkpolicy-isolate-db
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le réseau des Pods est
fourni par Calico, qui applique les NetworkPolicies.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace, puis le serveur et les quatre clients. Le serveur écoute
sur le port 7000, déclaré sous le nom `coffre-http`, et il est placé sur le
worker `k8s-w1.lab` (`nodeName`) :

```bash
kubectl create namespace essai-np
cat <<YAML | kubectl apply -n essai-np -f -
apiVersion: v1
kind: Pod
metadata:
  name: coffre
  labels: {app: coffre}
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: coffre
      image: registry.k8s.io/e2e-test-images/agnhost:2.53
      args: [netexec, --http-port=7000]
      ports:
        - {name: coffre-http, containerPort: 7000}
      readinessProbe:
        httpGet: {path: /healthz, port: coffre-http}
        periodSeconds: 3
YAML
kubectl expose pod coffre --port=7000 -n essai-np
for c in guichet migration sauvegarde curieux; do kubectl run $c --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-np --labels=app=$c -- sleep 3600 >/dev/null; done
kubectl wait --for=condition=Ready pod --all -n essai-np --timeout=120s
```

```text
namespace/essai-np created
pod/coffre created
service/coffre exposed
pod/coffre condition met
pod/curieux condition met
pod/guichet condition met
pod/migration condition met
pod/sauvegarde condition met
```

Chaque essai de ce cours lance `nc -z` depuis chaque client vers le Service
`coffre`, port 7000, avec un délai de 3 secondes. `ouvert` veut dire que la
connexion a réussi. Sans aucune politique, tout le monde entre :

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ouvert
sauvegarde  -> ouvert
curieux     -> ouvert
```

## 🏷️ Exercice 1 : un port désigné par son nom

Créez une politique qui ne laisse entrer que `guichet`, sur le port nommé
`coffre-http` et non sur le numéro :

```bash
cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coffre-guichet
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: guichet}
      ports:
        - port: coffre-http
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io/coffre-guichet created
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ferme
sauvegarde  -> ferme
curieux     -> ferme
```

Seul `guichet` entre. Le nom `coffre-http` est cherché dans les ports
déclarés par le conteneur du Pod visé. L'avantage : si l'application change de
port, il suffit de changer le Pod, la politique suit.

## 📋 Exercice 2 : une liste de clients avec matchExpressions

`matchLabels` exige une valeur exacte. Pour autoriser deux clients dans la
même règle, remplacez-le par `matchExpressions` avec l'opérateur `In` :

```bash
kubectl patch networkpolicy coffre-guichet -n essai-np --type json -p '[{"op":"replace","path":"/spec/ingress/0/from/0/podSelector","value":{"matchExpressions":[{"key":"app","operator":"In","values":["guichet","migration"]}]}}]'; sleep 5
```

```text
networkpolicy.networking.k8s.io/coffre-guichet patched
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ouvert
sauvegarde  -> ferme
curieux     -> ferme
```

`guichet` et `migration` entrent, les deux autres restent dehors.

## ➕ Exercice 3 : deux politiques s'additionnent

Créez une seconde politique, séparée, qui ouvre le serveur à `sauvegarde` :

```bash
cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coffre-sauvegarde
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: sauvegarde}
      ports:
        - port: 7000
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io/coffre-sauvegarde created
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
migration   -> ouvert
sauvegarde  -> ouvert
curieux     -> ferme
```

Trois clients entrent. Les politiques qui visent un même Pod s'additionnent :
chacune ajoute des autorisations, aucune n'en retire. Il n'existe pas de règle
« refuser » dans une NetworkPolicy. Pour savoir qui peut joindre un Pod, il
faut donc lire toutes les politiques qui le visent, pas seulement la dernière.

## 🚫 Exercice 4 : la sonde du kubelet sous un refus total

Une politique qui vise le serveur sans aucune règle `ingress` refuse toute
entrée. Créez-la, et supprimez les deux autres :

```bash
cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tout-fermer
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
YAML
kubectl delete networkpolicy coffre-guichet coffre-sauvegarde -n essai-np; sleep 10
```

```text
networkpolicy.networking.k8s.io/tout-fermer created
networkpolicy.networking.k8s.io "coffre-guichet" deleted from essai-np namespace
networkpolicy.networking.k8s.io "coffre-sauvegarde" deleted from essai-np namespace
```

```bash
for c in guichet migration sauvegarde curieux; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 coffre 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ferme
migration   -> ferme
sauvegarde  -> ferme
curieux     -> ferme
```

Plus personne n'entre. Le serveur a pourtant une sonde `readinessProbe` :
toutes les 3 secondes, le kubelet appelle `/healthz` sur son port. Regardez
son état :

```bash
kubectl get pod coffre -n essai-np -o jsonpath='{.status.conditions[?(@.type=="Ready")].status} redémarrages={.status.containerStatuses[0].restartCount}{"\n"}'
```

```text
True redémarrages=0
```

Le Pod est toujours Ready, sans redémarrage. Avec Calico, le nœud qui héberge
un Pod peut toujours le joindre, quelle que soit la politique : c'est ce qui
laisse passer la sonde du kubelet. Un refus total ne rend donc pas un Pod
NotReady. L'exercice suivant montre l'autre face de cette règle.

## 🏠 Exercice 5 : un client qui partage le réseau d'un nœud

Créez deux clients en `hostNetwork`, avec l'étiquette `app=guichet` : un sur
le worker, à côté du serveur, et un sur le control plane :

```bash
for n in w1 cp; do kubectl run hote-$n --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-np --labels=app=guichet --overrides="{\"spec\":{\"hostNetwork\":true,\"nodeName\":\"k8s-$n.lab\"}}" -- sleep 3600; done; kubectl wait --for=condition=Ready pod/hote-w1 pod/hote-cp -n essai-np --timeout=120s; kubectl get pods -n essai-np -o wide | awk '{print $1, $6, $7}'
```

```text
pod/hote-w1 created
pod/hote-cp created
pod/hote-w1 condition met
pod/hote-cp condition met
NAME IP NODE
coffre 10.244.38.110 k8s-w1.lab
curieux 10.244.38.105 k8s-w1.lab
guichet 10.244.38.119 k8s-w1.lab
hote-cp 10.10.50.11 k8s-cp.lab
hote-w1 10.10.50.12 k8s-w1.lab
migration 10.244.38.66 k8s-w1.lab
sauvegarde 10.244.38.118 k8s-w1.lab
```

Les deux nouveaux clients portent l'adresse de leur nœud. Essayez d'abord de
joindre le serveur par son nom depuis `hote-cp` :

```bash
kubectl exec hote-cp -n essai-np -- nc -z -w 3 coffre 7000; echo "code $?"; kubectl exec hote-cp -n essai-np -- cat /etc/resolv.conf
```

```text
nc: bad address 'coffre'
command terminated with exit code 1
code 1
search lab
nameserver 10.10.50.1
```

`bad address 'coffre'` : le nom ne se résout pas. Un Pod en `hostNetwork`
reçoit le `/etc/resolv.conf` du nœud, qui ne connaît pas les noms du cluster.
Sans le savoir, on croirait à un refus de la politique. Les essais qui suivent
utilisent donc l'adresse du Pod.

Remplacez le refus total par la politique qui ne laisse entrer que
`app=guichet` :

```bash
kubectl delete networkpolicy tout-fermer -n essai-np; cat <<'YAML' | kubectl apply -n essai-np -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coffre-guichet
spec:
  podSelector:
    matchLabels: {app: coffre}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {app: guichet}
YAML
sleep 5
```

```text
networkpolicy.networking.k8s.io "tout-fermer" deleted from essai-np namespace
networkpolicy.networking.k8s.io/coffre-guichet created
```

```bash
IP=$(kubectl get pod coffre -n essai-np -o jsonpath='{.status.podIP}'); for c in guichet hote-w1 hote-cp; do printf '%-11s -> ' $c; kubectl exec $c -n essai-np -- nc -z -w 3 $IP 7000 >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
guichet     -> ouvert
hote-w1     -> ouvert
hote-cp     -> ferme
```

Les trois clients portent la même étiquette, et pourtant `hote-cp` est
refusé. Pour Calico, un Pod en `hostNetwork` n'est pas un Pod : son trafic
vient de l'adresse du nœud, et `podSelector` ne le reconnaît pas. `hote-w1`
passe pour la raison vue à l'exercice 4 : il est sur le nœud qui héberge le
serveur.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Les Pods, le Service et les politiques
partent avec lui :

```bash
kubectl delete namespace essai-np
```

```text
namespace "essai-np" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-networkpolicy-isolate-db
dsoxlab check cka-networkpolicy-isolate-db
```

```text
╭─ Résultat : cka-networkpolicy-isolate-db ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/8 tests          │
╰───────────────────────────────────────────╯
```

0 sur 8 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une base de données que seul le backend doit
pouvoir joindre.

```bash
dsoxlab run cka-networkpolicy-isolate-db
dsoxlab challenge cka-networkpolicy-isolate-db
```
