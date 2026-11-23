# Repérer les signaux clés d'un cluster

La leçon présente les trois sources de métriques d'un cluster
(kube-state-metrics, cAdvisor et le kubelet), les cinq signaux à surveiller,
et les alertes PromQL qui les repèrent. Ce cours vous fait lire chaque source,
provoquer deux signaux sur des Pods d'essai, les retrouver dans Prometheus,
puis écrire une alerte et la voir se déclencher.

Vous travaillez dans le namespace `essai-obs`. Le challenge porte sur d'autres
Pods et d'autres signaux : vous le ferez seul, à la fin.

Page associée : [Observabilité Kubernetes](https://www.stephane-robert.info/docs/observabilite/pratiques/observabilite-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-reperer-les-signaux-d-un-cluster
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le lab a installé
Prometheus dans le namespace `supervision` : depuis ce nœud, il répond sur
`http://localhost:30090`.

Pour interroger Prometheus sans navigateur, définissez une petite fonction
`q`. Elle envoie une requête PromQL à son API et affiche chaque série sur une
ligne, avec sa valeur :

```bash
q() { curl -fsS http://localhost:30090/api/v1/query --data-urlencode "query=$1" | jq -r '.data.result[] | "\(.metric | del(.__name__, .instance, .job, .uid, .id, .name, .image) | to_entries | map("\(.key)=\(.value)") | join(",")) => \(.value[1])"'; }
```

Gardez le même terminal jusqu'au nettoyage : la fonction n'existe que dans
lui. Les sorties montrées dans ce cours ont été relevées sur cette machine le
23 novembre 2026, avec Kubernetes v1.37.2, Prometheus v3.16.0 et
kube-state-metrics v2.20.0.

## 🔍 Exercice 1 : lire les trois sources à la main

Prometheus ne fabrique aucune métrique : il les lit chez trois sources. Lisez
chacune directement, par le proxy de l'API server, et cherchez ce qu'elle sait
d'un même sujet, le namespace `supervision` :

```bash
kubectl get --raw /api/v1/namespaces/kube-system/services/kube-state-metrics:http-metrics/proxy/metrics | grep -c '^kube_'
kubectl get --raw /api/v1/namespaces/kube-system/services/kube-state-metrics:http-metrics/proxy/metrics | grep '^kube_pod_status_phase{namespace="supervision"' | grep ' 1$'
kubectl get --raw /api/v1/nodes/k8s-cp.lab/proxy/metrics | grep '^kubelet_running_pods'
kubectl get --raw /api/v1/nodes/k8s-cp.lab/proxy/metrics/cadvisor | grep '^container_memory_working_set_bytes{' | grep 'namespace="supervision"' | grep 'container="prometheus"' | grep -o 'pod="[^"]*"} [0-9.e+]*'
```

```text
4138
kube_pod_status_phase{namespace="supervision",pod="prometheus-db77b7f4b-tsgq8",uid="98568c05-c952-4c60-9ca2-ec27b90beab7",phase="Running"} 1
kubelet_running_pods 24
pod="prometheus-db77b7f4b-tsgq8"} 9.1938816e+07
```

kube-state-metrics connaît l'**état** des objets : le Pod de Prometheus est en
phase `Running`. Le kubelet connaît son **nœud** : 24 Pods y tournent.
cAdvisor connaît la **consommation** : le conteneur de Prometheus utilise
environ 92 Mo de mémoire. Aucune des trois ne sait ce que savent les deux
autres.

## ⏳ Exercice 2 : un Pod qui ne trouve pas de place

Créez un Pod qui demande 64 CPU, plus qu'aucun nœud n'en a, puis demandez à
Prometheus quels Pods d'`essai-obs` sont en attente. Regardez aussi l'état
`Ready` des nœuds, le quatrième signal de la leçon :

```bash
kubectl create namespace essai-obs
kubectl -n essai-obs run essai-trop-gros --image=busybox:1.37 --restart=Never --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.37","command":["sleep","3600"],"resources":{"requests":{"cpu":"64"}}}]}}'
sleep 40; kubectl -n essai-obs get pods
q 'kube_pod_status_phase{namespace="essai-obs",phase="Pending"} == 1'
q 'sum by (node) (kube_node_status_condition{condition="Ready",status="true"})'
```

```text
namespace/essai-obs created
pod/essai-trop-gros created
NAME              READY   STATUS    RESTARTS   AGE
essai-trop-gros   0/1     Pending   0          40s
namespace=essai-obs,phase=Pending,pod=essai-trop-gros => 1
node=k8s-cp.lab => 1
node=k8s-w1.lab => 1
node=k8s-w2.lab => 1
```

kube-state-metrics publie une série par phase et par Pod, qui vaut 1 pour la
phase en cours : `== 1` ne garde que les Pods vraiment en attente. Les trois
nœuds valent 1 : tous sont `Ready`. Un nœud défaillant vaudrait 0, et c'est
`== 0` qui le repérerait.

## 🔁 Exercice 3 : un conteneur qui redémarre en boucle

Créez un Deployment dont le conteneur s'arrête en erreur au bout de 5
secondes, attendez deux minutes, puis comptez ses redémarrages récents :

```bash
kubectl -n essai-obs create deployment essai-plante --image=busybox:1.37 -- sh -c 'sleep 5; exit 1'
sleep 120; kubectl -n essai-obs get pods -l app=essai-plante
q 'increase(kube_pod_container_status_restarts_total{namespace="essai-obs"}[5m])'
q 'kube_pod_container_status_last_terminated_reason{namespace="essai-obs"}'
```

```text
deployment.apps/essai-plante created
NAME                          READY   STATUS   RESTARTS      AGE
essai-plante-757448f7-tj4v2   0/1     Error    3 (87s ago)   2m
container=busybox,namespace=essai-obs,pod=essai-plante-757448f7-tj4v2 => 2.1748000000000003
container=busybox,namespace=essai-obs,pod=essai-plante-757448f7-tj4v2,reason=Error => 1
```

`increase()` estime le nombre de redémarrages sur les 5 dernières minutes, à
partir d'un compteur. L'estimation n'est pas un entier : Prometheus extrapole
entre ses mesures. La raison du dernier arrêt est `Error`, un code de sortie
non nul. Un conteneur tué par manque de mémoire porterait `OOMKilled`.

## 🚨 Exercice 4 : écrire une alerte et la voir se déclencher

Prometheus lit ses règles dans le ConfigMap `prometheus-regles` du namespace
`supervision`. Écrivez une règle qui alerte sur un Pod d'`essai-obs` en
attente depuis plus d'une minute, rangez-la dans le ConfigMap, puis attendez
que le fichier apparaisse dans le Pod de Prometheus :

```bash
cat > essai-regles.yaml <<'YAML'
groups:
  - name: essai-obs
    rules:
      - alert: EssaiPodEnAttente
        expr: sum by (namespace, pod) (kube_pod_status_phase{namespace="essai-obs",phase="Pending"}) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Le Pod {{ $labels.pod }} attend depuis plus d'une minute"
YAML
kubectl -n supervision create configmap prometheus-regles --from-file=essai.yaml=essai-regles.yaml --dry-run=client -o yaml | kubectl apply -f -
until kubectl -n supervision exec deploy/prometheus -- ls /etc/prometheus/regles/ | grep -q essai.yaml; do sleep 5; done; echo "fichier présent"
```

```text
configmap/prometheus-regles configured
fichier présent
```

Le fichier a mis environ 70 secondes à atteindre le Pod : c'est le délai de
mise à jour d'un ConfigMap monté. Demandez maintenant à Prometheus de relire
ses règles, puis suivez l'alerte :

```bash
curl -s -X POST http://localhost:30090/-/reload -o /dev/null -w '%{http_code}\n'
sleep 20; curl -s http://localhost:30090/api/v1/alerts | jq -r '.data.alerts[] | "\(.labels.alertname) \(.labels.pod) \(.state)"'
sleep 60; curl -s http://localhost:30090/api/v1/alerts | jq -r '.data.alerts[] | "\(.labels.alertname) \(.labels.pod) \(.state) \(.annotations.summary)"'
```

```text
200
EssaiPodEnAttente essai-trop-gros pending
EssaiPodEnAttente essai-trop-gros firing Le Pod essai-trop-gros attend depuis plus d'une minute
```

L'alerte passe d'abord par `pending` : la condition est vraie, mais pas encore
depuis la durée de son `for:`. Une minute plus tard, elle est `firing`, et son
résumé nomme le Pod. Sans le `for:`, un Pod qui attend quelques secondes
pendant un déploiement normal réveillerait l'astreinte.

## 🧹 Nettoyage

Videz le ConfigMap des règles, puis redémarrez Prometheus : il repart sans
aucune règle, comme au début du lab. Supprimez enfin le namespace d'essai et
le fichier de règles :

```bash
kubectl -n supervision create configmap prometheus-regles --dry-run=client -o yaml | kubectl apply -f -
kubectl -n supervision rollout restart deployment/prometheus
kubectl -n supervision rollout status deployment/prometheus --timeout=300s
kubectl delete namespace essai-obs --wait=true --timeout=120s
rm -f essai-regles.yaml
curl -s http://localhost:30090/api/v1/rules | jq '.data.groups | length'
```

```text
configmap/prometheus-regles configured
deployment.apps/prometheus restarted
Waiting for deployment "prometheus" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "prometheus" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "prometheus" rollout to finish: 1 old replicas are pending termination...
deployment "prometheus" successfully rolled out
namespace "essai-obs" deleted
0
```

Prometheus ne porte plus aucun groupe de règles. Quittez ensuite la machine et
remettez le lab à zéro. `dsoxlab reset` rejoue le nettoyage puis la
préparation du lab : vous retrouvez exactement l'état de départ du challenge.
Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-reperer-les-signaux-d-un-cluster
dsoxlab check k8s-reperer-les-signaux-d-un-cluster
```

```text
╭─ Résultat : k8s-reperer-les-signaux-d-un-cluster ─╮
│  0 / 100 pts                                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests                  │
╰───────────────────────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : écrire les deux alertes qui repèrent un conteneur
tué par manque de mémoire et un conteneur bridé par sa limite CPU, sans
alerter sur le Pod témoin.

```bash
dsoxlab run k8s-reperer-les-signaux-d-un-cluster
dsoxlab challenge k8s-reperer-les-signaux-d-un-cluster
```
