# Tracer une requête lente

La leçon branche Istio sur un collecteur OpenTelemetry et Jaeger, pose un
waypoint, fait suivre le contexte de trace, et retrouve le saut lent dans une
trace. C'est le challenge du lab : ce cours ne configure aucun traçage. Il
travaille ce qui se mesure sans traces et ce que les traces supposent : où
part le temps d'une requête, ce qu'un délai côté client fait d'une requête
lente, ce qu'est réellement le contexte de trace, et comment interroger
Jaeger sans interface graphique.

Vous travaillez dans le namespace `essai-trace`, hors du maillage, avec une
application podinfo, `info`, qui sait répondre en retard sur demande, et un
client `sonde`. Le challenge porte sur d'autres services, dans le maillage :
vous le ferez seul, à la fin.

Page associée : [Tracer une requête lente à travers le maillage Istio](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/tracer-requetes-istio/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-tracer-une-requete-lente
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le control plane du cluster
kubeadm. Posez les objets d'essai : podinfo et son Service, et un client
`curl` :

```bash
kubectl create namespace essai-trace
kubectl -n essai-trace create deployment info --image=ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
kubectl -n essai-trace expose deployment info --port 9898
kubectl -n essai-trace run sonde --image=curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40 --command -- sleep 3600
kubectl -n essai-trace rollout status deployment info --timeout=120s
kubectl -n essai-trace wait --for=condition=Ready pod/sonde --timeout=120s; sleep 5
```

```text
namespace/essai-trace created
deployment.apps/info created
service/info exposed
pod/sonde created
Waiting for deployment "info" rollout to finish: 0 of 1 updated replicas are available...
deployment "info" successfully rolled out
pod/sonde condition met
```

Le `sleep 5` compte : lors d'un premier essai, les appels lancés aussitôt
ont été refusés (code 7 de `curl`, connexion refusée) : laissez quelques
secondes à l'application après le déploiement. Les sorties montrées dans ce cours ont été relevées sur
cette machine le 23 novembre 2026 (Kubernetes v1.37.2, podinfo 6.17.0,
Jaeger 2.23.0).

## ⏱️ Exercice 1 : où part le temps d'une requête

`curl -w` affiche des mesures prises pendant la requête. Trois suffisent pour
savoir où part le temps : la connexion établie (`time_connect`), le premier
octet de la réponse reçu (`time_starttransfer`) et la fin (`time_total`).
podinfo répond tout de suite sur `/`, et une seconde plus tard sur
`/delay/1` :

```bash
for chemin in / /delay/1; do kubectl -n essai-trace exec sonde -- curl -s -o /dev/null -w "$chemin : connexion %{time_connect}s, premier octet %{time_starttransfer}s, total %{time_total}s\n" "http://info:9898$chemin"; done
```

```text
/ : connexion 0.000789s, premier octet 0.001583s, total 0.001603s
/delay/1 : connexion 0.000834s, premier octet 1.002589s, total 1.002773s
```

Sur `/delay/1`, la connexion prend moins d'une milliseconde, comme sur `/`.
La seconde se perd **entre la connexion et le premier octet** : le serveur a
reçu la requête et a mis une seconde à répondre. Si le temps se perdait avant
la connexion, il faudrait chercher du côté du réseau ou du DNS. Une trace dit
la même chose saut par saut, quand la requête traverse plusieurs services.

## ⌛ Exercice 2 : un délai client fait d'une lenteur une erreur

Appelez la même route lente avec un délai maximal de 0,5 seconde, comme le
ferait un client pressé :

```bash
kubectl -n essai-trace exec sonde -- curl -s -m 0.5 -o /dev/null -w '%{http_code}\n' 'http://info:9898/delay/1'; echo "code=$?"
```

```text
000
command terminated with exit code 28
code=28
```

Aucun code HTTP (`000`) et le code 28 de `curl`, délai dépassé : le client a
abandonné. Le serveur, lui, a fini sa seconde de travail sans le savoir. Vu
du client, une dépendance lente ressemble alors à une panne, et le journal du
client dit « timeout », jamais « lent ». C'est pour retrouver la vraie cause
qu'on trace.

## 🧵 Exercice 3 : le contexte de trace n'est qu'un en-tête

Une trace relie des sauts grâce à un en-tête HTTP, `traceparent` (norme W3C
Trace Context). Il porte l'identifiant de la trace, celui du saut appelant,
et un indicateur d'échantillonnage. Envoyez-en un à podinfo, dont la route
`/headers` renvoie les en-têtes reçus :

```bash
kubectl -n essai-trace exec sonde -- curl -s -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' 'http://info:9898/headers' | grep -i -A1 traceparent
```

```text
  "Traceparent": [
    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
```

L'en-tête arrive tel quel. Il se découpe en quatre champs séparés par des
tirets : la version (`00`), l'identifiant de la trace sur 32 caractères,
celui du saut appelant sur 16, et `01`, qui demande l'enregistrement. Rien
dans le réseau ne le recopie à votre place : si une application appelle un
autre service sans renvoyer cet en-tête, le saut suivant commence une
nouvelle trace.

## 🔎 Exercice 4 : interroger Jaeger sans interface

Jaeger tourne dans le namespace `observabilite`, sans adresse exposée hors du
cluster. L'API server sait relayer une requête vers un Service : c'est ainsi
qu'on lit l'API de Jaeger depuis `kubectl`, sans `port-forward`. Demandez la
liste des services connus de Jaeger :

```bash
kubectl get --raw '/api/v1/namespaces/observabilite/services/http:jaeger:16686/proxy/api/v3/services'
```

```text
{"services":["jaeger"]}
```

Jaeger ne connaît qu'un service, lui-même : rien n'envoie encore de traces.
Le chemin se lit ainsi : `services/http:jaeger:16686/proxy` désigne le
Service `jaeger`, son port `16686`, en HTTP, et tout ce qui suit est transmis
à Jaeger (`/api/v3/services`). Quand le traçage sera branché, les services du
maillage apparaîtront dans cette liste.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-trace --wait=true --timeout=120s
```

```text
namespace "essai-trace" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge, avec un nouveau service lent tiré au hasard. Il vous
demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-tracer-une-requete-lente
dsoxlab check k8s-tracer-une-requete-lente
```

```text
╭─ Résultat : k8s-tracer-une-requete-lente ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests          │
╰───────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : brancher le traçage d'Istio sur le collecteur,
faire arriver les spans dans Jaeger, et trouver, dans une seule trace, quel
service ralentit les requêtes.

```bash
dsoxlab run k8s-tracer-une-requete-lente
dsoxlab challenge k8s-tracer-une-requete-lente
```
