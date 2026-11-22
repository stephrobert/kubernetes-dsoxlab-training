# Filtrer en L7 avec Cilium

La leçon sert une application par un Gateway de Cilium, puis pose une
politique qui filtre les requêtes HTTP par leur méthode. Ce cours ne touche
ni au Gateway ni à la méthode : c'est le challenge du lab. Il pratique les
politiques HTTP de Cilium sur d'autres critères, le chemin et un en-tête, et
apprend à reconnaître leurs refus : la réponse que reçoit le client, la
ligne que montre Hubble, et la différence avec un refus au niveau du port.

Vous travaillez dans le namespace `essai-l7`, avec un serveur nginx `doc` et
un client `visiteur`. Le challenge porte sur d'autres Pods, dans
`catalogue` : vous le ferez seul, à la fin.

Page associée : [Servir un Gateway et filtrer en L7 avec Cilium](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/cilium-gateway-l7/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-filtrer-en-l7-avec-cilium
```

Vous êtes maintenant connecté à `net-cp.lab`, le plan de contrôle du cluster
Cilium. Posez les objets d'essai : le serveur `doc` sur `net-w1`, son
Service, et le client `visiteur` sur `net-w2` :

```bash
kubectl create namespace essai-l7; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: doc
  namespace: essai-l7
  labels:
    app: doc
spec:
  nodeName: net-w1.lab
  containers:
    - name: web
      image: nginx:1.30.6
---
apiVersion: v1
kind: Service
metadata:
  name: doc
  namespace: essai-l7
spec:
  selector:
    app: doc
  ports:
    - port: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: visiteur
  namespace: essai-l7
  labels:
    app: visiteur
spec:
  nodeName: net-w2.lab
  containers:
    - name: c
      image: curlimages/curl:8.22.0
      command: ["sleep", "3600"]
YAML
kubectl -n essai-l7 wait --for=condition=Ready pod --all --timeout=120s
```

```text
namespace/essai-l7 created
pod/doc created
service/doc created
pod/visiteur created
pod/doc condition met
pod/visiteur condition met
```

Les sorties montrées dans ce cours ont été relevées sur ces machines le
22 novembre 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🚪 Exercice 1 : un Gateway sans ses définitions

Un Gateway est une ressource de la Gateway API, que Kubernetes ne connaît pas
tant que ses CRD (les définitions des nouveaux types d'objets) ne sont pas
installées. Le cluster du lab ne les a pas. Faites valider un Gateway
d'essai par l'API server, sans rien créer (`--dry-run=server`), puis listez
les types que connaît le groupe `gateway.networking.k8s.io` :

```bash
cat > /tmp/essai-gateway.yaml <<'YAML'
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: essai
  namespace: essai-l7
spec:
  gatewayClassName: cilium
  listeners:
    - name: web
      protocol: HTTP
      port: 80
YAML
kubectl apply --dry-run=server -f /tmp/essai-gateway.yaml; echo "code=$?"
kubectl api-resources --api-group=gateway.networking.k8s.io
rm /tmp/essai-gateway.yaml
```

```text
error: resource mapping not found for name: "essai" namespace: "essai-l7" from "/tmp/essai-gateway.yaml": no matches for kind "Gateway" in version "gateway.networking.k8s.io/v1"
ensure CRDs are installed first
code=1
NAME   SHORTNAMES   APIVERSION   NAMESPACED   KIND
```

`no matches for kind "Gateway"` : l'API server ne connaît pas ce type, et
`kubectl` le dit lui-même, `ensure CRDs are installed first`. La liste des
types du groupe est vide. Ce message ne parle ni de Cilium ni de la classe
`cilium` : tant qu'il apparaît, le problème se trouve avant Cilium.

## 🛣️ Exercice 2 : filtrer par chemin

Sans politique, le client lit toutes les pages du serveur. nginx sert
`/index.html` et une page d'erreur, `/50x.html` :

```bash
for p in /index.html /50x.html; do echo "$p -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' "http://doc$p")"; done
```

```text
/index.html -> 200
/50x.html -> 200
```

Posez une CiliumNetworkPolicy qui n'autorise au client que le chemin
`/index.html`. La section `rules.http` fait passer le trafic du port 80 par le
proxy de Cilium, qui lit chaque requête :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: doc-chemins
  namespace: essai-l7
spec:
  endpointSelector:
    matchLabels:
      app: doc
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: visiteur
      toPorts:
        - ports:
            - port: "80"
              protocol: TCP
          rules:
            http:
              - path: "/index.html"
YAML
sleep 10
for p in /index.html /50x.html; do echo "$p -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' "http://doc$p")"; done
kubectl -n essai-l7 exec visiteur -- curl -s http://doc/50x.html
```

```text
ciliumnetworkpolicy.cilium.io/doc-chemins created
/index.html -> 200
/50x.html -> 403
Access denied
```

`/50x.html` est maintenant refusé en **403**, avec le corps `Access denied`.
Ce n'est pas nginx qui répond : c'est le proxy de Cilium, qui a lu le chemin
et refusé la requête avant qu'elle atteigne le serveur. Un refus L7 se voit
donc tout de suite, avec une réponse HTTP.

## 🔭 Exercice 3 : le refus vu par Hubble

Le refus se lit aussi dans Hubble, sur l'agent du nœud du serveur, qui porte
la politique d'entrée. Le filtre `--protocol http` ne garde que les flux que
le proxy a lus :

```bash
w1=$(kubectl -n kube-system get pods -l k8s-app=cilium --field-selector spec.nodeName=net-w1.lab -o name)
kubectl -n kube-system exec $w1 -c cilium-agent -- hubble observe --namespace essai-l7 --protocol http --last 4
```

```text
Nov 22 22:47:34.827: essai-l7/visiteur:35854 (ID:7450) -> essai-l7/doc:80 (ID:31715) http-request DROPPED (HTTP/1.1 GET http://doc/50x.html)
Nov 22 22:47:34.827: essai-l7/visiteur:35854 (ID:7450) <- essai-l7/doc:80 (ID:31715) http-response FORWARDED (HTTP/1.1 403 0ms (GET http://doc/50x.html))
Nov 22 22:47:34.894: essai-l7/visiteur:35862 (ID:7450) -> essai-l7/doc:80 (ID:31715) http-request DROPPED (HTTP/1.1 GET http://doc/50x.html)
Nov 22 22:47:34.894: essai-l7/visiteur:35862 (ID:7450) <- essai-l7/doc:80 (ID:31715) http-response FORWARDED (HTTP/1.1 403 0ms (GET http://doc/50x.html))
```

Chaque requête refusée donne deux lignes. La requête, avec sa méthode et son
URL complète, est `DROPPED`. La réponse, `403` produite en moins d'une
milliseconde (`0ms`), est `FORWARDED` : c'est le proxy qui la renvoie au
client. Hubble nomme la requête exacte, ce qu'un refus de port ne peut pas
faire.

## 🏷️ Exercice 4 : exiger un en-tête

Une règle HTTP peut aussi exiger un en-tête. Modifiez la politique pour
qu'elle demande `X-Essai: oui` en plus du chemin, puis testez avec et sans
l'en-tête :

```bash
kubectl -n essai-l7 patch cnp doc-chemins --type=json -p='[{"op":"replace","path":"/spec/ingress/0/toPorts/0/rules/http/0","value":{"path":"/index.html","headers":["X-Essai: oui"]}}]'
sleep 10
echo "sans en-tete -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' 'http://doc/index.html')"
echo "avec en-tete -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' -H 'X-Essai: oui' 'http://doc/index.html')"
```

```text
ciliumnetworkpolicy.cilium.io/doc-chemins patched
sans en-tete -> 403
avec en-tete -> 200
```

Les champs d'une même règle se combinent : le chemin **et** l'en-tête doivent
correspondre. Sans l'en-tête, la page autorisée à l'exercice 2 devient
refusée. Une règle HTTP ne remplace pas une authentification : n'importe quel
client qui connaît l'en-tête peut l'envoyer.

## 🔌 Exercice 5 : un refus au niveau du port

Changez maintenant le port de la règle, 8080 au lieu de 80, comme une faute
de frappe. Le port 80 n'est plus autorisé du tout :

```bash
kubectl -n essai-l7 patch cnp doc-chemins --type=json -p='[{"op":"replace","path":"/spec/ingress/0/toPorts/0/ports/0/port","value":"8080"}]'
sleep 10
time kubectl -n essai-l7 exec visiteur -- curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://doc/index.html
echo "code=$?"
```

```text
ciliumnetworkpolicy.cilium.io/doc-chemins patched
000
command terminated with exit code 28

real	0m5.076s
user	0m0.033s
sys	0m0.013s
code=28
```

Plus de 403 : `curl` attend les 5 secondes de `-m 5`, puis abandonne (code 28,
délai dépassé), sans aucun code HTTP (`000`). Le paquet est jeté avant le
proxy, et personne ne répond. Retenez la différence : **un 403 immédiat vient
d'une règle L7, un délai dépassé d'une règle L3 ou L4**. C'est le premier
indice pour savoir quelle partie de la politique corriger.

## 🧹 Nettoyage

Supprimez le namespace d'essai, qui emporte la politique, et vérifiez que les
Pods du challenge sont toujours là :

```bash
kubectl delete namespace essai-l7 --wait=true --timeout=120s
kubectl -n catalogue get pods
```

```text
namespace "essai-l7" deleted
NAME                      READY   STATUS    RESTARTS   AGE
fiches-65686f97d9-gsqtk   1/1     Running   0          91s
lecteur                   1/1     Running   0          91s
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-filtrer-en-l7-avec-cilium
dsoxlab check k8s-filtrer-en-l7-avec-cilium
```

```text
╭─ Résultat : k8s-filtrer-en-l7-avec-cilium ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests           │
╰────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : servir une application par un Gateway de Cilium,
puis la protéger par une politique L7 qui laisse lire et refuse d'écrire,
par le Gateway comme depuis un Pod.

```bash
dsoxlab run k8s-filtrer-en-l7-avec-cilium
dsoxlab challenge k8s-filtrer-en-l7-avec-cilium
```
