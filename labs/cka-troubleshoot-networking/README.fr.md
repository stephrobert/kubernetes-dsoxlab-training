# Réparer le réseau des Pods d'un nœud et lire ce que dit le réseau

La leçon montre le réseau des Pods sur un cluster kind : les plages
d'adresses, un Pod qui en joint un autre, un nœud dont le réseau tombe. Ce
cours vous fait lire le même réseau sur le cluster kubeadm du lab, qui tourne
avec Calico, et ajoute des cas que la leçon ne montre pas : la route qui mène à
un Pod, un Pod qui partage le réseau du nœud, un refus qui vient d'un mauvais
port, un délai qui vient d'une règle réseau, et une adresse qui change quand
le Pod est recréé.

Vous travaillez dans un namespace d'essai, `essai-reseau`, avec un serveur
`web` (nginx) et un Pod `client` (busybox). Le challenge porte sur d'autres
objets : vous le ferez seul, à la fin.

Page associée : [Pod Networking](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/pod-networking/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-troubleshoot-networking
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Le lab a mis en panne le réseau des Pods du worker `k8s-w1.lab` : c'est le
challenge. Ce cours n'y touche pas. Tous ses Pods sont placés sur le control
plane, avec `nodeName` dans `--overrides`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et Calico.

## 🛣️ Exercice 1 : par quelle route joint-on un Pod ?

Créez le namespace, puis un serveur et un client sur le control plane :

```bash
kubectl create namespace essai-reseau
kubectl run web --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-reseau --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}'; kubectl run client --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-reseau --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/web pod/client -n essai-reseau --timeout=120s
```

```text
namespace/essai-reseau created
pod/web created
pod/client created
pod/web condition met
pod/client condition met
```

Relevez l'adresse de chaque Pod :

```bash
kubectl get pods -n essai-reseau -o custom-columns=NOM:.metadata.name,IP:.status.podIP,NOEUD:.spec.nodeName
```

```text
NOM      IP              NOEUD
client   10.244.163.39   k8s-cp.lab
web      10.244.163.40   k8s-cp.lab
```

Les deux adresses sont dans `10.244.0.0/16`, la plage des Pods du cluster.
Demandez maintenant au noyau du nœud par où il enverrait un paquet vers `web` :

```bash
IP=$(kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}'); ip route get $IP
```

```text
10.244.163.40 dev calid79caa05e8e src 10.10.50.11 uid 1001 
    cache 
```

Le paquet part par une interface `cali…`. Calico crée une interface de ce
type pour chaque Pod du nœud : c'est le bout côté nœud du câble virtuel qui
entre dans le Pod. Listez toutes les routes vers la plage des Pods :

```bash
ip route | grep 10.244 | head -5
```

```text
10.244.38.64/26 via 10.10.50.12 dev enp1s0 proto 80 onlink 
blackhole 10.244.163.0/26 proto 80 
10.244.163.2 dev cali101be86f1b7 scope link metric 1024 
10.244.163.4 dev califb592c426d0 scope link metric 1024 
10.244.163.5 dev cali3a96b53951b scope link metric 1024 
```

Chaque Pod du nœud a une route vers sa seule adresse, par son interface
`cali…`. Calico donne
à chaque nœud un bloc de 64 adresses (`/26`) : le bloc local finit en
`blackhole`, pour qu'une adresse sans Pod ne parte nulle part, et le bloc du
worker passe par l'adresse de ce nœud, `10.10.50.12`. Quand un Pod ne répond
pas, c'est la première question à poser : la route vers son adresse
existe-t-elle, et par où part-elle ?

Vérifiez que `client` joint `web` par son adresse :

```bash
IP=$(kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}'); kubectl exec client -n essai-reseau -- wget -qO- -T 3 "http://$IP" | grep -o '<title>.*</title>'
```

```text
<title>Welcome to nginx!</title>
```

## 🏠 Exercice 2 : un Pod qui partage le réseau du nœud

Avec `hostNetwork: true`, un Pod n'a pas sa propre adresse : il utilise celle
du nœud. Créez-en un :

```bash
kubectl run hote --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-reseau --overrides='{"spec":{"hostNetwork":true,"nodeName":"k8s-cp.lab"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/hote -n essai-reseau --timeout=120s
```

```text
pod/hote created
pod/hote condition met
```

Comparez son adresse à celle du nœud :

```bash
kubectl get pods -n essai-reseau -o custom-columns=NOM:.metadata.name,IP:.status.podIP,NOEUD:.spec.nodeName; kubectl get node k8s-cp.lab -o jsonpath='{.status.addresses[0].address}{"\n"}'
```

```text
NOM      IP              NOEUD
client   10.244.163.39   k8s-cp.lab
hote     10.10.50.11     k8s-cp.lab
web      10.244.163.40   k8s-cp.lab
10.10.50.11
```

`hote` porte l'adresse du nœud, `10.10.50.11`, hors de la plage des Pods.
Regardez les interfaces qu'il voit :

```bash
kubectl exec hote -n essai-reseau -- ip -4 addr show | grep inet
```

```text
    inet 127.0.0.1/8 scope host lo
    inet 10.10.50.11/24 brd 10.10.50.255 scope global dynamic enp1s0
    inet 10.244.163.0/32 scope global vxlan.calico
```

Il voit l'interface réelle du nœud (`enp1s0`) et le tunnel de Calico. Le CNI
ne s'occupe pas de ce Pod : c'est pour cela que les Pods `calico-node` et
`kube-proxy` tournent ainsi, et qu'ils démarrent même quand le réseau des Pods
d'un nœud est en panne. Quand vous voyez une adresse de nœud dans la colonne
IP d'un Pod, ce Pod est en `hostNetwork`.

## 🚫 Exercice 3 : un refus qui vient du Pod

Exposez `web` par un Service dont le `targetPort` est faux : nginx écoute sur
80, le Service envoie sur 8080.

```bash
kubectl expose pod web --name=porte --port=80 --target-port=8080 -n essai-reseau; kubectl get endpointslices -n essai-reseau -l kubernetes.io/service-name=porte
```

```text
service/porte exposed
NAME          ADDRESSTYPE   PORTS   ENDPOINTS       AGE
porte-z9fm4   IPv4          8080    10.244.163.40   0s
```

Le Service a bien un endpoint : l'adresse de `web`, sur le port 8080. Rien
n'indique encore l'erreur. Appelez-le en chronométrant :

```bash
kubectl exec client -n essai-reseau -- sh -c 'debut=$(date +%s); wget -qO- -T 5 "http://porte"; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
wget: can't connect to remote host (10.103.132.190): Connection refused
code 1 en 1 s
```

`Connection refused`, presque tout de suite. Le paquet est arrivé jusqu'au
Pod, et le noyau du Pod a répondu que personne n'écoute sur ce port. Un refus
immédiat dit donc : le réseau fonctionne, c'est le port qui est faux, ou
l'application qui n'écoute pas.

## ⏳ Exercice 4 : un délai qui vient d'une règle réseau

Créez un second Service, correct cette fois, et posez une étiquette sur `web` :

```bash
kubectl expose pod web --name=muet --port=80 -n essai-reseau; kubectl label pod web -n essai-reseau role=web
```

```text
service/muet exposed
pod/web labeled
```

Ajoutez une NetworkPolicy qui ferme toute entrée vers les Pods `role=web`. Les
NetworkPolicies ont leur propre leçon plus loin dans la formation. Ici, il
suffit de savoir que Calico jette alors les paquets en silence, sans répondre :

```bash
cat <<'YAML' | kubectl apply -n essai-reseau -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: fermer-web
spec:
  podSelector:
    matchLabels:
      role: web
  policyTypes: [Ingress]
YAML
```

```text
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: fermer-web
spec:
  podSelector:
    matchLabels:
      role: web
  policyTypes: [Ingress]
YAML
networkpolicy.networking.k8s.io/fermer-web created
```

Appelez `muet` :

```bash
kubectl exec client -n essai-reseau -- sh -c 'debut=$(date +%s); wget -qO- -T 5 "http://muet"; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
wget: download timed out
code 1 en 5 s
```

Cette fois, `wget` attend les 5 secondes de son délai, puis abandonne. Personne
n'a répondu. Rappelez `porte`, qui refusait tout de suite à l'exercice 3 :

```bash
kubectl exec client -n essai-reseau -- sh -c 'debut=$(date +%s); wget -qO- -T 5 "http://porte"; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
wget: download timed out
code 1 en 5 s
```

Le refus est devenu un délai : le paquet est jeté avant d'arriver au Pod, donc
le Pod ne peut plus dire que le port est fermé. Retenez la règle : un délai
veut dire que quelque chose sur le chemin jette les paquets (une règle réseau,
une route absente, un nœud dont le réseau est tombé). Un refus veut dire que
le chemin marche.

Retirez la règle et vérifiez que `muet` répond de nouveau :

```bash
kubectl delete networkpolicy fermer-web -n essai-reseau; kubectl exec client -n essai-reseau -- sh -c 'wget -qO- -T 5 http://muet | grep -o "<title>.*</title>"'
```

```text
networkpolicy.networking.k8s.io "fermer-web" deleted from essai-reseau namespace
<title>Welcome to nginx!</title>
```

## 🔁 Exercice 5 : l'adresse change, le nom reste

Supprimez `web` et recréez-le à l'identique, avec l'étiquette `run=web` que
le Service `muet` sélectionne :

```bash
kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}{"\n"}'; kubectl delete pod web -n essai-reseau; kubectl run web --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-reseau --labels=run=web --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}'; kubectl wait --for=condition=Ready pod/web -n essai-reseau --timeout=120s; kubectl get pod web -n essai-reseau -o jsonpath='{.status.podIP}{"\n"}'
```

```text
10.244.163.40
pod "web" deleted from essai-reseau namespace
pod/web created
pod/web condition met
10.244.163.43
```

Même nom, autre adresse. Regardez le Service :

```bash
kubectl get endpointslices -n essai-reseau -l kubernetes.io/service-name=muet; kubectl exec client -n essai-reseau -- sh -c 'wget -qO- -T 5 http://muet | grep -o "<title>.*</title>"'
```

```text
NAME         ADDRESSTYPE   PORTS   ENDPOINTS       AGE
muet-pg2cp   IPv4          80      10.244.163.43   12s
<title>Welcome to nginx!</title>
```

L'EndpointSlice porte déjà la nouvelle adresse, et l'appel par le nom `muet`
marche sans rien changer. Une adresse de Pod notée à la main ne vaut que tant
que le Pod vit : pour joindre une application, passez par son Service.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-reseau
```

```text
namespace "essai-reseau" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-networking
dsoxlab check cka-troubleshoot-networking
```

```text
╭─ Résultat : cka-troubleshoot-networking ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests         │
╰──────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un worker dont le réseau des Pods est tombé, à
réparer, puis un refus et un délai à reconnaître. Le reset a déjà préparé le
challenge : ne relancez pas `dsoxlab run`, qui attend que tous les nœuds
soient Ready et échoue tant que le worker est en panne. Affichez l'énoncé,
puis reconnectez-vous à la machine :

```bash
dsoxlab challenge cka-troubleshoot-networking
dsoxlab ssh k8s-cp.lab
```
