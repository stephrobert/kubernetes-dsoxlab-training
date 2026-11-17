# Tracer une requête lente à travers le maillage Istio

## La situation

Le cluster kubeadm compte **trois nœuds** : le control plane et deux workers.
Istio 1.32 y tourne en **mode ambient**, **sans fournisseur de traces**. Le
fichier d'installation du maillage est sur le control plane :
`/root/istio-ambient.yaml`.

Dans le namespace **`observabilite`**, hors du maillage, un **collecteur
OpenTelemetry** (contrib 0.165.0) écoute l'OTLP sur le Service
`otel-collector` (port 4317 pour gRPC) et exporte tout vers **Jaeger** 2.23.0
(Service `jaeger`, API de requête et interface sur le port 16686).

Dans le namespace **`boutique`**, dans le maillage mais **sans waypoint**, le
Pod `client` appelle le Service `web`, et `web` appelle **à la fois** `api` et
`stock`. Chaque requête dure plus d'une seconde, et l'équipe ne sait pas
pourquoi : **un** des deux services, `api` ou `stock`, est lent. Lequel change
à chaque démarrage du lab.

Vous êtes sur le control plane, avec `kubectl`, `istioctl` et `jq`, en root.

## Ce que vous devez obtenir

1. La configuration du maillage déclare un **fournisseur opentelemetry** qui
   vise `otel-collector.observabilite.svc.cluster.local`, port **4317**.
2. Une **Telemetry** de niveau maillage, dans `istio-system`, trace **100 %**
   des requêtes avec ce fournisseur.
3. Un **waypoint** sert le namespace `boutique`, et son Pod est **Ready**.
4. Les spans du waypoint **arrivent dans Jaeger**.
5. Une **seule trace** relie une span de `web` à la span du waypoint pour le
   saut vers le service lent.
6. La ConfigMap **`diagnostic`** de `boutique` nomme le service lent, clé
   **`service-lent`**, valeur `api` ou `stock`.

## La méthode, pas à pas

**Déclarer le fournisseur.** Un fournisseur vit dans `meshConfig`, que seul
`istioctl install` réécrit. Copiez `/root/istio-ambient.yaml` dans un nouveau
fichier, ajoutez `spec.meshConfig.extensionProviders` avec une entrée de type
`opentelemetry` (service et port du collecteur), puis `istioctl install -y -f`
ce fichier. `kubectl -n istio-system get configmap istio -o yaml` montre le
résultat.

**Tracer chaque requête.** Une `Telemetry` dans `istio-system`, sans
sélecteur, s'applique à tout le maillage. Sous `tracing`, nommez le
fournisseur et posez `randomSamplingPercentage: 100` : par défaut, seule 1 %
des requêtes est tracée.

**Ajouter un waypoint.** ztunnel travaille en L4 : il voit des connexions,
pas des requêtes HTTP, et n'écrit aucune span. `istioctl waypoint apply -n
boutique --enroll-namespace --wait` crée un waypoint et étiquette le
namespace. istioctl affiche « is ready! » avant que le Pod le soit : attendez
le Pod lui-même avec `kubectl wait`.

**Regarder dans Jaeger.** Envoyez quelques requêtes depuis le client
(`kubectl -n boutique exec client -- curl -s -X POST -d bonjour
http://web.boutique:9898/echo`), puis ouvrez l'API de requête : `kubectl -n
observabilite port-forward svc/jaeger 16686:16686 &` et `curl -s
localhost:16686/api/v3/services`. Si Jaeger ne connaît que lui-même, les
spans se perdent en route. Le waypoint ne dit pourquoi que dans son journal
debug : `istioctl proxy-config log deploy/waypoint -n boutique --level
tracing:debug,grpc:debug`, puis `kubectl -n boutique logs deploy/waypoint`.
Regardez comment le port du collecteur est déclaré : Istio déduit le
protocole du préfixe du nom du port, ou d'`appProtocol`.

**Obtenir une trace, pas une par saut.** Le waypoint écrit une span par saut,
mais les sauts ne tombent dans la même trace que si `web` fait suivre le
contexte de trace (l'en-tête `traceparent`) sur ses propres appels. podinfo
ne le fait qu'avec `--otel-service-name`. Ajoutez-le à la commande de `web`.

**Lire la trace.** `curl -s
"localhost:16686/api/v3/traces?query.serviceName=web&query.startTimeMin=<RFC3339>&query.startTimeMax=<RFC3339>&query.searchDepth=20"`
rend les traces en JSON OTLP. Un filtre `jq` qui affiche, pour chaque span, le
nom du service, le nom de la span et `endTimeUnixNano - startTimeUnixNano` en
millisecondes montre quelle span fille de `web` dure plus d'une seconde.
L'interface, par le même port-forward, montre la même chose.

**Écrire le diagnostic.** `kubectl -n boutique create configmap diagnostic
--from-literal=service-lent=<service>`. Ne réparez pas le service lent : la
vérification lit son délai pour comparer.

## Comment savoir que ça marche

Les tests lisent `meshConfig`, les Telemetry, le waypoint et son Pod. Puis ils
envoient leurs propres requêtes et lisent l'API de Jaeger : les spans du
waypoint doivent arriver, et une trace doit contenir à la fois une span de
`web` et le saut vers le service lent. Enfin, ils comparent votre diagnostic
au service qui porte le délai.

```bash
dsoxlab check k8s-tracer-une-requete-lente
```
