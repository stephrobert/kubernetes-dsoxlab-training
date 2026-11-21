# Router avec la Gateway API, et réparer une route que le cluster refuse

La leçon montre une Gateway et une HTTPRoute qui envoient chaque chemin vers
son application. Ce cours vous fait lire l'état que le contrôleur écrit sur
ces objets, et ajoute des cas que la leçon ne montre pas : une Gateway dont le
port ne correspond à rien chez le contrôleur, un choix par méthode HTTP et par
paramètre d'URL, un chemin réécrit, un en-tête ajouté en passant, et une
route rattachée à un seul listener.

Vous travaillez dans un namespace d'essai, `essai-gateway`, avec une Gateway
`guichet`, deux applications (`salle` et `annexe`) et des hôtes en
`essai.local`. Le challenge porte sur d'autres objets : vous le ferez seul, à
la fin.

Page associée : [Gateway API](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/gateway-api/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-gateway-api-httproute
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Le contrôleur est Traefik, avec la GatewayClass `traefik`. Il écoute en HTTP
sur le port 30080 de chaque nœud. Pour appeler un hôte comme
`comptoir.essai.local` sans toucher au DNS, ce cours utilise l'option
`--resolve` de curl : elle dit à curl quelle adresse utiliser pour ce nom.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et Traefik v3.7.

Créez le namespace et deux applications. L'image agnhost lancée avec
`netexec` répond à plusieurs adresses : `/hostname` rend le nom du Pod, et
`/header?key=X` rend la valeur de l'en-tête X reçu :

```bash
kubectl create namespace essai-gateway
for a in salle annexe; do kubectl run $a --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-gateway --labels=app=$a -- netexec --http-port=8080 >/dev/null; kubectl expose pod $a --port=80 --target-port=8080 -n essai-gateway >/dev/null; done; kubectl wait --for=condition=Ready pod --all -n essai-gateway --timeout=120s
```

```text
namespace/essai-gateway created
pod/annexe condition met
pod/salle condition met
```

## 🚪 Exercice 1 : un listener sur un port que le contrôleur n'écoute pas

Créez une Gateway avec un listener HTTP sur le port 8000, pour tous les
hôtes en `essai.local` :

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: guichet
spec:
  gatewayClassName: traefik
  listeners:
    - name: public
      protocol: HTTP
      port: 8000
      hostname: "*.essai.local"
YAML
sleep 5; kubectl get gateway guichet -n essai-gateway
```

```text
gateway.gateway.networking.k8s.io/guichet created
NAME      CLASS     ADDRESS   PROGRAMMED   AGE
guichet   traefik             False        5s
```

`PROGRAMMED` vaut `False` : le contrôleur n'a pas pu mettre la Gateway en
service. La raison est écrite dans l'état du listener :

```bash
kubectl get gateway guichet -n essai-gateway -o jsonpath='{range .status.listeners[0].conditions[*]}{.type}={.status} ({.reason}) {.message}{"\n"}{end}'
```

```text
Accepted=False (PortUnavailable) Cannot find entryPoint for Gateway: no matching entryPoint for port 8000 and protocol "HTTP"
```

Traefik associe chaque listener à l'un de ses points d'entrée (ses
entrypoints), par le numéro de port. Regardez sur quel port écoute son point
d'entrée HTTP, et comment le Service l'expose :

```bash
kubectl -n traefik get deployment traefik -o jsonpath='{range .spec.template.spec.containers[0].args[*]}{@}{"\n"}{end}' | grep 'entryPoints.web.address'; kubectl -n traefik get service traefik -o jsonpath='{range .spec.ports[*]}{.name} {.port} nodePort={.nodePort}{"\n"}{end}'
```

```text
--entryPoints.web.address=:80/tcp
web 80 nodePort=30080
websecure 443 nodePort=30443
```

Le point d'entrée `web` écoute sur le port 80 du conteneur. Le Service
l'expose ensuite sur le port 30080 des nœuds. Le listener doit porter le port
du point d'entrée, 80, et non 30080 ni un autre. Corrigez :

```bash
kubectl patch gateway guichet -n essai-gateway --type json -p '[{"op":"replace","path":"/spec/listeners/0/port","value":80}]'; kubectl wait --for=condition=Programmed gateway/guichet -n essai-gateway --timeout=60s; kubectl get gateway guichet -n essai-gateway
```

```text
gateway.gateway.networking.k8s.io/guichet patched
gateway.gateway.networking.k8s.io/guichet condition met
NAME      CLASS     ADDRESS   PROGRAMMED   AGE
guichet   traefik             True         5s
```

Retenez le geste : quand une Gateway n'est pas `Programmed`, lisez
`status.listeners`, pas seulement `status.conditions`.

## 🔀 Exercice 2 : choisir par méthode et par paramètre

Une HTTPRoute ne choisit pas seulement par chemin. Créez une route qui envoie
les `POST` et les requêtes avec `?version=2` vers `annexe`, et tout le reste
vers `salle` :

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: comptoir
spec:
  parentRefs:
    - name: guichet
  hostnames: [comptoir.essai.local]
  rules:
    - matches:
        - method: POST
      backendRefs:
        - name: annexe
          port: 80
    - matches:
        - queryParams:
            - name: version
              value: "2"
      backendRefs:
        - name: annexe
          port: 80
    - backendRefs:
        - name: salle
          port: 80
YAML
sleep 3
```

```text
httproute.gateway.networking.k8s.io/comptoir created
```

Envoyez quatre requêtes, et lisez le nom de l'application qui répond :

```bash
R='--resolve comptoir.essai.local:30080:127.0.0.1 http://comptoir.essai.local:30080'; for essai in 'GET /hostname' 'POST /hostname' 'GET /hostname?version=2' 'GET /hostname?version=3'; do set -- $essai; printf '%-26s -> ' "$essai"; curl -s -X $1 $R$2; echo; done
```

```text
GET /hostname              -> salle
POST /hostname             -> annexe
GET /hostname?version=2    -> annexe
GET /hostname?version=3    -> salle
```

`POST` et `version=2` vont à `annexe`. `version=3` ne correspond à aucune
condition et tombe sur la dernière règle, qui n'en a pas. Une règle sans
`matches` prend tout ce que les autres laissent : c'est le défaut de la
route.

## ✏️ Exercice 3 : réécrire le chemin avant de transmettre

Les clients appellent encore un ancien chemin, `/qui-repond`, que
l'application ne connaît pas. Le filtre `URLRewrite` le remplace par
`/hostname` avant de transmettre la requête :

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ancien-chemin
spec:
  parentRefs:
    - name: guichet
  hostnames: [ancien.essai.local]
  rules:
    - matches:
        - path: {type: PathPrefix, value: /qui-repond}
      filters:
        - type: URLRewrite
          urlRewrite:
            path:
              type: ReplacePrefixMatch
              replacePrefixMatch: /hostname
      backendRefs:
        - name: salle
          port: 80
YAML
sleep 3; curl -s -w '  [%{http_code}]\n' --resolve ancien.essai.local:30080:127.0.0.1 http://ancien.essai.local:30080/qui-repond
```

```text
httproute.gateway.networking.k8s.io/ancien-chemin created
salle  [200]
```

Le client a demandé `/qui-repond`, l'application a reçu `/hostname`, et le
client ne voit pas le changement. Avec `ReplacePrefixMatch`, seul le début qui
correspond est remplacé : `/qui-repond/x` deviendrait `/hostname/x`.

## 🏷️ Exercice 4 : ajouter un en-tête en passant

Ajoutez à la route une règle pour `/header`, avec le filtre
`RequestHeaderModifier` qui pose l'en-tête `X-Equipe: accueil` sur chaque
requête. L'appel demande ensuite à l'application la valeur reçue :

```bash
kubectl patch httproute ancien-chemin -n essai-gateway --type json -p '[{"op":"add","path":"/spec/rules/-","value":{"matches":[{"path":{"type":"PathPrefix","value":"/header"}}],"filters":[{"type":"RequestHeaderModifier","requestHeaderModifier":{"set":[{"name":"X-Equipe","value":"accueil"}]}}],"backendRefs":[{"name":"salle","port":80}]}}]'; sleep 3; curl -s --resolve ancien.essai.local:30080:127.0.0.1 'http://ancien.essai.local:30080/header?key=X-Equipe'; echo
```

```text
httproute.gateway.networking.k8s.io/ancien-chemin patched
accueil
```

L'application a reçu l'en-tête ajouté par le contrôleur. C'est utile pour
dire au backend d'où vient la requête, sans toucher au client.

## 🎚️ Exercice 5 : s'attacher à un seul listener

Ajoutez à la Gateway un second listener, `interne`, pour les hôtes en
`interne.local` :

```bash
kubectl patch gateway guichet -n essai-gateway --type json -p '[{"op":"add","path":"/spec/listeners/-","value":{"name":"interne","protocol":"HTTP","port":80,"hostname":"*.interne.local"}}]'; kubectl wait --for=condition=Programmed gateway/guichet -n essai-gateway --timeout=60s
```

```text
gateway.gateway.networking.k8s.io/guichet patched
gateway.gateway.networking.k8s.io/guichet condition met
```

Créez une route pour `bureau.interne.local`, mais rattachez-la par erreur au
listener `public` avec `sectionName`, puis lisez son état :

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: bureau
spec:
  parentRefs:
    - name: guichet
      sectionName: public
  hostnames: [bureau.interne.local]
  rules:
    - backendRefs:
        - name: salle
          port: 80
YAML
sleep 3; kubectl get httproute bureau -n essai-gateway -o jsonpath='{range .status.parents[0].conditions[*]}{.type}={.status} ({.reason}){"\n"}{end}'
```

```text
httproute.gateway.networking.k8s.io/bureau created
Accepted=False (NoMatchingListenerHostname)
ResolvedRefs=True (ResolvedRefs)
```

`Accepted=False`, raison `NoMatchingListenerHostname` : le listener `public`
n'accepte que `*.essai.local`, et le nom de la route n'y entre pas. Une route
refusée ne casse rien d'autre, elle n'est simplement pas servie. Rattachez-la
au bon listener :

```bash
kubectl patch httproute bureau -n essai-gateway --type json -p '[{"op":"replace","path":"/spec/parentRefs/0/sectionName","value":"interne"}]'; sleep 3; kubectl get httproute bureau -n essai-gateway -o jsonpath='{range .status.parents[0].conditions[*]}{.type}={.status} ({.reason}){"\n"}{end}'; curl -s --resolve bureau.interne.local:30080:127.0.0.1 "http://bureau.interne.local:30080/hostname"; echo
```

```text
httproute.gateway.networking.k8s.io/bureau patched
Accepted=True (Accepted)
ResolvedRefs=True (ResolvedRefs)
salle
```

La route est acceptée et `salle` répond. Sans `sectionName`, une route
s'attache à tous les listeners de la Gateway qui l'acceptent. Avec lui, vous
choisissez la porte d'entrée.

## 🧹 Nettoyage

Supprimez le namespace d'essai. La Gateway, les routes et les applications
partent avec lui :

```bash
kubectl delete namespace essai-gateway
```

```text
namespace "essai-gateway" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-gateway-api-httproute
dsoxlab check cka-gateway-api-httproute
```

```text
╭─ Résultat : cka-gateway-api-httproute ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests       │
╰────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une Gateway à mettre en service, deux applications à
router par chemin, et une route refusée à faire accepter.

```bash
dsoxlab run cka-gateway-api-httproute
dsoxlab challenge cka-gateway-api-httproute
```
