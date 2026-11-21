# Router deux applications sur un seul hôte, et vérifier que chacune reçoit la sienne

La leçon montre un Ingress qui envoie chaque chemin vers son application. Ce
cours vous fait voir ce que le contrôleur fait vraiment des règles, avec
Traefik, le contrôleur installé sur le cluster du lab : `Exact` contre
`Prefix`, un préfixe qui couvre plus qu'on ne croit, le chemin le plus long
qui l'emporte, un backend par défaut que Traefik ignore dans un cas précis, et
un Ingress sans classe.

Vous travaillez dans un namespace d'essai, `essai-ingress`, avec trois
applications (`boutique`, `promo`, `secours`) et l'hôte `magasin.local`. Le
challenge porte sur d'autres objets : vous le ferez seul, à la fin.

Page associée : [Ingress](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-ingress-path-routing
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Traefik écoute en HTTP sur le port 30080 de chaque nœud. Pour appeler un hôte
comme `magasin.local` sans toucher au DNS, ce cours utilise l'option
`--resolve` de curl : elle dit à curl quelle adresse utiliser pour ce nom.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et Traefik v3.7.

Créez le namespace et trois applications. Chacune répond par son propre nom
(`serve-hostname` de l'image agnhost), ce qui permet de voir qui a répondu :

```bash
kubectl create namespace essai-ingress
for a in boutique promo secours; do kubectl run $a --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-ingress --labels=app=$a -- serve-hostname --port=8080 >/dev/null; kubectl expose pod $a --port=80 --target-port=8080 -n essai-ingress >/dev/null; done; kubectl wait --for=condition=Ready pod --all -n essai-ingress --timeout=120s; kubectl get services -n essai-ingress
```

```text
namespace/essai-ingress created
pod/boutique condition met
pod/promo condition met
pod/secours condition met
NAME       TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
boutique   ClusterIP   10.103.246.157   <none>        80/TCP    1s
promo      ClusterIP   10.98.110.214    <none>        80/TCP    1s
secours    ClusterIP   10.106.202.191   <none>        80/TCP    1s
```

Vérifiez la classe d'Ingress disponible :

```bash
kubectl get ingressclass
```

```text
NAME      CONTROLLER                      PARAMETERS   AGE
traefik   traefik.io/ingress-controller   <none>       5m58s
```

## 🎯 Exercice 1 : Exact ou Prefix

Créez un Ingress qui envoie exactement `/boutique` vers l'application
`boutique` :

```bash
cat <<'YAML' | kubectl apply -n essai-ingress -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: magasin
spec:
  ingressClassName: traefik
  rules:
    - host: magasin.local
      http:
        paths:
          - path: /boutique
            pathType: Exact
            backend:
              service: {name: boutique, port: {number: 80}}
YAML
```

```text
ingress.networking.k8s.io/magasin created
```

Appelez trois chemins. La commande affiche le code HTTP de chacun :

```bash
sleep 3; for p in /boutique /boutique/ /boutique/panier; do curl -s -o /dev/null -w '%{http_code} ' --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p";  echo " <- $p"; done
```

```text
200  <- /boutique
404  <- /boutique/
404  <- /boutique/panier
```

Avec `pathType: Exact`, seul `/boutique` passe. `/boutique/` (avec la barre
finale) et `/boutique/panier` rendent 404. Un client ou un navigateur qui
ajoute une barre finale tombe donc sur une erreur.

## 🧩 Exercice 2 : un préfixe couvre plus qu'on ne croit

Passez la règle en `Prefix` et appelez quatre chemins, dont `/boutiques` :

```bash
kubectl patch ingress magasin -n essai-ingress --type json -p '[{"op":"replace","path":"/spec/rules/0/http/paths/0/pathType","value":"Prefix"}]'; sleep 3; for p in /boutique /boutique/ /boutique/panier /boutiques; do curl -s -o /dev/null -w '%{http_code} ' --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p";  echo " <- $p"; done
```

```text
ingress.networking.k8s.io/magasin patched
200  <- /boutique
200  <- /boutique/
200  <- /boutique/panier
200  <- /boutiques
```

Les trois premiers passent, c'est le rôle de `Prefix`. Le quatrième aussi.
Or la spécification Kubernetes compare un préfixe segment par segment
(les morceaux entre deux `/`) : `/boutique` ne devrait pas couvrir
`/boutiques`. Traefik, lui, compare ici les caractères. Le résultat dépend
donc du contrôleur. Si une autre application doit répondre sur
`/boutiques`, déclarez son chemin explicitement plutôt que de compter sur la
spécification.

## 📏 Exercice 3 : le chemin le plus long l'emporte

Ajoutez un second chemin, plus long, qui commence comme le premier :

```bash
kubectl patch ingress magasin -n essai-ingress --type json -p '[{"op":"add","path":"/spec/rules/0/http/paths/-","value":{"path":"/boutique/promo","pathType":"Prefix","backend":{"service":{"name":"promo","port":{"number":80}}}}}]'; sleep 3
```

```text
ingress.networking.k8s.io/magasin patched
```

Appelez trois chemins. Cette fois, la commande affiche le nom de
l'application qui répond :

```bash
for p in /boutique/panier /boutique/promo /boutique/promo/noel; do printf '%s -> ' $p; curl -s --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p"; echo; done
```

```text
/boutique/panier -> boutique
/boutique/promo -> promo
/boutique/promo/noel -> promo
```

`/boutique/promo` et tout ce qui suit vont à `promo`. Le reste de
`/boutique` va toujours à `boutique`. Quand deux préfixes conviennent, le plus
long gagne, même s'il est déclaré après l'autre dans l'Ingress.

## 🛟 Exercice 4 : un défaut pour tout le reste

Pour l'instant, un chemin qui ne correspond à aucune règle rend 404 :

```bash
for p in /inconnu /; do curl -s -o /dev/null -w '%{http_code} ' --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p";  echo " <- $p"; done
```

```text
404  <- /inconnu
404  <- /
```

Le champ `spec.defaultBackend` d'un Ingress désigne l'application qui reçoit
tout ce qu'aucune règle ne prend. Ajoutez-le à `magasin` :

```bash
kubectl patch ingress magasin -n essai-ingress --type merge -p '{"spec":{"defaultBackend":{"service":{"name":"secours","port":{"number":80}}}}}'; sleep 3; for p in /inconnu /; do printf '%s -> ' $p; curl -s --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p"; echo; done
```

```text
ingress.networking.k8s.io/magasin patched
/inconnu -> 404 page not found

/ -> 404 page not found
```

Rien ne change : `404 page not found` est la page de Traefik. Sur ce cluster,
Traefik ignore le `defaultBackend` d'un Ingress qui a aussi des règles. Il ne
le prend en compte que dans un Ingress qui n'a que ce champ. Retirez-le de
`magasin` et créez un Ingress `secours` qui ne déclare que lui :

```bash
kubectl patch ingress magasin -n essai-ingress --type json -p '[{"op":"remove","path":"/spec/defaultBackend"}]'
cat <<'YAML' | kubectl apply -n essai-ingress -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secours
spec:
  ingressClassName: traefik
  defaultBackend:
    service: {name: secours, port: {number: 80}}
YAML
```

```text
ingress.networking.k8s.io/magasin patched
ingress.networking.k8s.io/secours created
```

Appelez de nouveau, y compris un autre hôte :

```bash
sleep 5; for p in /boutique/panier /inconnu /; do printf '%s -> ' $p; curl -s --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p"; echo; done; printf 'autre.local/ -> '; curl -s --resolve autre.local:30080:127.0.0.1 "http://autre.local:30080/"; echo
```

```text
/boutique/panier -> boutique
/inconnu -> secours
/ -> secours
autre.local/ -> secours
```

Les règles de `magasin` gardent la priorité (`/boutique/panier` va à
`boutique`), et `secours` prend tout le reste, même pour un hôte qui n'est
déclaré nulle part. Un Ingress accepté par l'API n'est donc pas une preuve :
seul un appel montre ce que le contrôleur en a fait.

## 🏷️ Exercice 5 : un Ingress sans classe

Une classe d'Ingress peut être marquée comme classe par défaut, par une
annotation. Lisez celles de `traefik` :

```bash
kubectl get ingressclass traefik -o jsonpath='{.metadata.annotations}{"\n"}'
```

```text
{"ingressclass.kubernetes.io/is-default-class":"false","meta.helm.sh/release-name":"traefik","meta.helm.sh/release-namespace":"traefik"}
```

`is-default-class` vaut `false` : Traefik n'est pas la classe par défaut.
Créez un Ingress sans `ingressClassName`, puis lisez sa classe et appelez-le :

```bash
cat <<'YAML' | kubectl apply -n essai-ingress -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sans-classe
spec:
  rules:
    - host: sans-classe.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: {name: promo, port: {number: 80}}
YAML
sleep 3; kubectl get ingress sans-classe -n essai-ingress -o jsonpath='{.spec.ingressClassName}{"\n"}'; curl -s -o /dev/null -w '%{http_code}\n' --resolve sans-classe.local:30080:127.0.0.1 http://sans-classe.local:30080/
```

```text
ingress.networking.k8s.io/sans-classe created

200
```

La ligne vide est la classe de l'Ingress : il n'en a pas. Traefik le sert
pourtant (200). Ne comptez donc pas sur l'absence de classe pour qu'un
Ingress reste ignoré. Sur un cluster qui a plusieurs contrôleurs, écrivez
toujours `ingressClassName`.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Les Ingress, les Services et les Pods
partent avec lui :

```bash
kubectl delete namespace essai-ingress
```

```text
namespace "essai-ingress" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-ingress-path-routing
dsoxlab check cka-ingress-path-routing
```

```text
╭─ Résultat : cka-ingress-path-routing ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : deux applications à router sur un seul hôte, et la
preuve que chacune reçoit ses propres requêtes.

```bash
dsoxlab run cka-ingress-path-routing
dsoxlab challenge cka-ingress-path-routing
```
