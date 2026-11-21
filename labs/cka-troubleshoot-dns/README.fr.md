# Rétablir la résolution DNS du cluster

La leçon montre comment les Pods trouvent les Services par leur nom : le
fichier `/etc/resolv.conf` du Pod, CoreDNS et sa configuration, le Corefile.
Ce cours vous fait monter votre propre CoreDNS d'essai, à côté de celui du
cluster, et vous fait voir des cas que la leçon ne montre pas : un Pod qui
choisit son serveur DNS, un nom réécrit par CoreDNS, une zone envoyée vers un
serveur qui ne répond jamais, un Service qui n'est qu'un alias, et un Pod qui
utilise le DNS du nœud au lieu de celui du cluster.

Vous travaillez dans un namespace d'essai, `essai-dns`, avec un serveur
`vitrine` (nginx) et des Pods clients (busybox). Le challenge porte sur
d'autres objets : vous le ferez seul, à la fin.

Page associée : [CoreDNS](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/coredns/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-troubleshoot-dns
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Le lab a mis en panne le DNS du cluster : c'est le challenge. Ce cours n'y
touche pas. Il monte son propre CoreDNS dans le namespace d'essai.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2, CoreDNS 1.14.6 et busybox 1.38.

## 🔍 Exercice 1 : constater que le DNS du cluster ne répond pas

Créez le namespace, un serveur exposé par un Service, et un Pod client :

```bash
kubectl create namespace essai-dns
kubectl run vitrine --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-dns --labels=app=vitrine; kubectl expose pod vitrine --port=80 -n essai-dns; kubectl wait --for=condition=Ready pod/vitrine -n essai-dns --timeout=120s
kubectl run poste --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dns -- sleep 3600; kubectl wait --for=condition=Ready pod/poste -n essai-dns --timeout=120s
```

```text
namespace/essai-dns created
pod/vitrine created
service/vitrine exposed
pod/vitrine condition met
pod/poste created
pod/poste condition met
```

Demandez au client le nom complet du Service :

```bash
kubectl exec poste -n essai-dns -- nslookup -timeout=3 vitrine.essai-dns.svc.cluster.local; echo "code $?"
```

```text
;; connection timed out; no servers could be reached

nslookup: write to '10.96.0.10': Connection refused
command terminated with exit code 1
code 1
```

Le client a envoyé sa question à `10.96.0.10`, l'adresse du Service DNS du
cluster, et elle a été refusée. Le Service `vitrine` existe pourtant : c'est
le DNS qui ne répond pas. Pourquoi il ne répond pas, c'est l'objet du
challenge. Pour la suite du cours, vous montez votre propre serveur DNS.

## 🧰 Exercice 2 : un CoreDNS d'essai, avec les droits du cluster

CoreDNS lit les Services et les Pods dans l'API pour répondre. Regardez
l'image utilisée par le cluster et les droits de son rôle :

```bash
kubectl -n kube-system get deployment coredns -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'; kubectl get clusterrole system:coredns -o jsonpath='{range .rules[*]}{.resources}{" "}{.verbs}{"\n"}{end}'
```

```text
registry.k8s.io/coredns/coredns:v1.14.6
["endpoints","services","pods","namespaces"] ["list","watch"]
["endpointslices"] ["list","watch"]
```

Le rôle `system:coredns` permet de lister et de surveiller (`list`, `watch`)
les Services, les Pods, les namespaces et les EndpointSlices. Rien d'autre :
CoreDNS ne modifie jamais l'API.

Montez maintenant votre CoreDNS d'essai. La commande crée un ServiceAccount
lié à ce rôle, écrit un Corefile, le range dans une ConfigMap, puis lance un
Deployment avec la même image que le cluster et l'expose en UDP sur le port
53 :

```bash
IMG=$(kubectl -n kube-system get deployment coredns -o jsonpath='{.spec.template.spec.containers[0].image}'); kubectl create serviceaccount dns-essai -n essai-dns; kubectl create clusterrolebinding essai-dns --clusterrole=system:coredns --serviceaccount=essai-dns:dns-essai; cat > ~/Corefile.essai <<'COREFILE'
.:53 {
    errors
    rewrite name exact catalogue.local vitrine.essai-dns.svc.cluster.local
    kubernetes cluster.local in-addr.arpa ip6.arpa {
       pods insecure
       fallthrough in-addr.arpa ip6.arpa
    }
    cache 30
}
essai.test:53 {
    errors
    forward . 192.0.2.53
}
COREFILE
kubectl create configmap dns-essai -n essai-dns --from-file=Corefile=$HOME/Corefile.essai
cat <<YAML | kubectl apply -n essai-dns -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dns-essai
spec:
  replicas: 1
  selector:
    matchLabels: {app: dns-essai}
  template:
    metadata:
      labels: {app: dns-essai}
    spec:
      serviceAccountName: dns-essai
      containers:
        - name: coredns
          image: $IMG
          args: ["-conf", "/etc/coredns/Corefile"]
          securityContext:
            capabilities:
              add: [NET_BIND_SERVICE]
              drop: [ALL]
          volumeMounts:
            - {name: conf, mountPath: /etc/coredns}
      volumes:
        - name: conf
          configMap: {name: dns-essai}
YAML
kubectl expose deployment dns-essai -n essai-dns --port=53 --protocol=UDP; kubectl rollout status deployment/dns-essai -n essai-dns --timeout=120s
```

```text
serviceaccount/dns-essai created
clusterrolebinding.rbac.authorization.k8s.io/essai-dns created
configmap/dns-essai created
deployment.apps/dns-essai created
service/dns-essai exposed
Waiting for deployment "dns-essai" rollout to finish: 0 of 1 updated replicas are available...
deployment "dns-essai" successfully rolled out
```

Le Corefile déclare deux blocs. Le premier (`.:53`) répond à tout : il sert la
zone `cluster.local` grâce au plugin `kubernetes`, et réécrit un nom avec
`rewrite`. Le second (`essai.test:53`) renvoie tout ce qui finit par
`essai.test` vers un autre serveur, avec `forward`. Les exercices 4 et 5 s'en
servent.

Lisez le début du journal :

```bash
sleep 3; kubectl logs deploy/dns-essai -n essai-dns | head -4
```

```text
maxprocs: Leaving GOMAXPROCS=2: CPU quota undefined
.:53
essai.test.:53
CoreDNS-1.14.6
```

CoreDNS annonce les deux blocs qu'il sert, puis sa version. C'est la première
chose à lire quand CoreDNS ne répond pas comme prévu : un bloc absent de cette
liste n'a pas été chargé.

## 🧭 Exercice 3 : un Pod qui choisit son serveur DNS

Par défaut, un Pod utilise le DNS du cluster. Avec `dnsPolicy: None`, c'est
vous qui écrivez son `/etc/resolv.conf` dans le champ `dnsConfig`. Créez un Pod
qui interroge votre CoreDNS d'essai :

```bash
IP=$(kubectl get service dns-essai -n essai-dns -o jsonpath='{.spec.clusterIP}'); cat <<YAML | kubectl apply -n essai-dns -f -
apiVersion: v1
kind: Pod
metadata:
  name: guichet
spec:
  dnsPolicy: None
  dnsConfig:
    nameservers: ["$IP"]
    searches: [essai-dns.svc.cluster.local, svc.cluster.local, cluster.local]
    options:
      - {name: ndots, value: "5"}
  containers:
    - name: guichet
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
YAML
kubectl wait --for=condition=Ready pod/guichet -n essai-dns --timeout=120s; kubectl exec guichet -n essai-dns -- cat /etc/resolv.conf
```

```text
pod/guichet created
pod/guichet condition met
search essai-dns.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.97.43.189
options ndots:5
```

Le fichier contient exactement ce que vous avez déclaré : le serveur, la liste
de recherche (`search`) et `ndots:5`. Avec `ndots:5`, un nom qui a moins de
cinq points est d'abord complété par chaque suffixe de la liste. Essayez un nom
court :

```bash
kubectl exec guichet -n essai-dns -- nslookup vitrine; kubectl exec guichet -n essai-dns -- wget -qO- -T 3 "http://vitrine" | grep -o '<title>.*</title>'
```

```text
Server:		10.97.43.189
Address:	10.97.43.189:53

** server can't find vitrine.cluster.local: NXDOMAIN

Name:	vitrine.essai-dns.svc.cluster.local
Address: 10.96.88.251

** server can't find vitrine.svc.cluster.local: NXDOMAIN

** server can't find vitrine.cluster.local: NXDOMAIN


** server can't find vitrine.svc.cluster.local: NXDOMAIN

command terminated with exit code 1
<title>Welcome to nginx!</title>
```

Lisez cette sortie avec soin. `nslookup` de busybox essaie chaque suffixe et
affiche un `NXDOMAIN` pour chaque essai raté. Au milieu, il trouve
`vitrine.essai-dns.svc.cluster.local`. Il rend pourtant le code 1 (`command
terminated with exit code 1`), parce qu'un des essais a échoué. Le `wget`
juste après prouve que le nom court fonctionne. Avec busybox, ne vous fiez
donc pas au code de retour de `nslookup` : lisez la ligne `Name`.

## ✏️ Exercice 4 : un nom réécrit par CoreDNS

Le Corefile contient `rewrite name exact catalogue.local
vitrine.essai-dns.svc.cluster.local`. Interrogez ce nom, qui n'existe dans
aucune zone :

```bash
kubectl exec guichet -n essai-dns -- nslookup catalogue.local; kubectl exec guichet -n essai-dns -- wget -qO- -T 3 "http://catalogue.local" | grep -o '<title>.*</title>'
```

```text
Server:		10.97.43.189
Address:	10.97.43.189:53

Name:	catalogue.local
Address: 10.96.88.251


<title>Welcome to nginx!</title>
```

CoreDNS a remplacé le nom avant de chercher, puis a rendu la réponse sous le
nom demandé. Le client ne voit pas la réécriture. C'est utile pour garder un
ancien nom pendant une migration. C'est aussi un piège en dépannage : un nom
qui répond n'est pas forcément un nom qui existe. Le Corefile est la seule
façon de le savoir.

## ⏳ Exercice 5 : une zone envoyée vers un serveur muet

Le bloc `essai.test` renvoie ses questions vers `192.0.2.53`, une adresse
réservée à la documentation, que rien ne sert. Interrogez un nom de cette zone
en chronométrant :

```bash
kubectl exec guichet -n essai-dns -- sh -c 'debut=$(date +%s); nslookup -timeout=3 intranet.essai.test; echo "code $? en $(( $(date +%s) - debut )) s"'
```

```text
;; connection timed out; no servers could be reached

code 1 en 3 s
```

Le client attend ses 3 secondes, puis abandonne. Ce n'est pas un `NXDOMAIN` :
personne n'a répondu. Le journal de CoreDNS dit pourquoi, quelques secondes
plus tard :

```bash
sleep 8; kubectl logs deploy/dns-essai -n essai-dns --tail=3
```

```text
[ERROR] plugin/errors: 2 intranet.essai.test. AAAA: read udp 10.244.38.127:49120->192.0.2.53:53: i/o timeout
[ERROR] plugin/errors: 2 intranet.essai.test. A: read udp 10.244.38.127:39073->192.0.2.53:53: i/o timeout
[ERROR] plugin/errors: 2 intranet.essai.test. AAAA: read udp 10.244.38.127:54346->192.0.2.53:53: i/o timeout
```

`i/o timeout` vers `192.0.2.53:53` : CoreDNS a bien reçu la question et l'a
transmise, mais le serveur suivant n'a jamais répondu. C'est le plugin `errors`
qui écrit ces lignes. Sans lui, la panne ne laisse aucune trace. Le reste du
DNS fonctionne toujours :

```bash
kubectl exec guichet -n essai-dns -- wget -qO- -T 3 "http://vitrine" | grep -o '<title>.*</title>'
```

```text
<title>Welcome to nginx!</title>
```

Retenez la différence : `NXDOMAIN` veut dire qu'un serveur a répondu que le
nom n'existe pas, un délai veut dire que personne n'a répondu.

## 🔗 Exercice 6 : un Service qui n'est qu'un alias

Un Service de type `ExternalName` n'a ni adresse ni endpoint : c'est un
alias DNS. Créez-en un qui pointe vers `vitrine` :

```bash
kubectl create service externalname annuaire --external-name=vitrine.essai-dns.svc.cluster.local -n essai-dns; kubectl get service annuaire -n essai-dns
```

```text
service/annuaire created
NAME       TYPE           CLUSTER-IP   EXTERNAL-IP                           PORT(S)   AGE
annuaire   ExternalName   <none>       vitrine.essai-dns.svc.cluster.local   <none>    0s
```

Pas de `CLUSTER-IP`, pas de port. Interrogez-le :

```bash
kubectl exec guichet -n essai-dns -- nslookup annuaire
```

```text
Server:		10.97.43.189
Address:	10.97.43.189:53

** server can't find annuaire.cluster.local: NXDOMAIN

annuaire.essai-dns.svc.cluster.local	canonical name = vitrine.essai-dns.svc.cluster.local
Name:	vitrine.essai-dns.svc.cluster.local
Address: 10.96.88.251

** server can't find annuaire.cluster.local: NXDOMAIN




command terminated with exit code 1
```

CoreDNS répond par un `canonical name` (un CNAME) vers
`vitrine.essai-dns.svc.cluster.local`, puis par l'adresse de ce nom. Le même
piège de busybox revient : code 1 alors que le nom est trouvé. Un Service
`ExternalName` dépend donc entièrement du DNS : si le nom cible ne se résout
pas, l'alias ne mène nulle part, et kube-proxy n'y peut rien.

## 🏠 Exercice 7 : dnsPolicy Default, le DNS du nœud

Le nom est trompeur : `dnsPolicy: Default` n'est pas la valeur par défaut. La
valeur par défaut est `ClusterFirst`. `Default` donne au Pod le DNS du nœud.
Créez un Pod avec cette politique et lisez son `/etc/resolv.conf` :

```bash
kubectl run noeud-dns --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-dns --overrides='{"spec":{"dnsPolicy":"Default"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/noeud-dns -n essai-dns --timeout=120s; kubectl exec noeud-dns -n essai-dns -- cat /etc/resolv.conf
```

```text
pod/noeud-dns created
pod/noeud-dns condition met
search lab
nameserver 10.10.50.1
```

Le Pod a reçu le fichier du nœud : la recherche `lab` et le serveur
`10.10.50.1`, celui du réseau des machines. Demandez-lui un nom du cluster :

```bash
kubectl exec noeud-dns -n essai-dns -- nslookup -timeout=3 vitrine.essai-dns.svc.cluster.local; echo "code $?"
```

```text
;; connection timed out; no servers could be reached

command terminated with exit code 1
code 1
```

Le serveur du nœud ne connaît pas `cluster.local`. Un Pod qui ne trouve aucun
Service alors que ses voisins y arrivent mérite donc un coup d'œil à son
champ `dnsPolicy`, avant de soupçonner CoreDNS.

## 🧹 Nettoyage

Supprimez le namespace d'essai, la liaison au rôle (elle n'appartient à
aucun namespace) et le Corefile :

```bash
kubectl delete namespace essai-dns; kubectl delete clusterrolebinding essai-dns; rm -f ~/Corefile.essai
```

```text
namespace "essai-dns" deleted
clusterrolebinding.rbac.authorization.k8s.io "essai-dns" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-dns
dsoxlab check cka-troubleshoot-dns
```

```text
╭─ Résultat : cka-troubleshoot-dns ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : le DNS du cluster ne répond plus, retrouvez
pourquoi et remettez-le en service.

```bash
dsoxlab run cka-troubleshoot-dns
dsoxlab challenge cka-troubleshoot-dns
```
