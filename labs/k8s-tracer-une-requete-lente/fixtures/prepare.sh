#!/usr/bin/env bash
# Pose la situation du lab k8s-tracer-une-requete-lente, sur un Istio ambient
# que le setup vient de ramener au profil du lab (sans fournisseur de traces) :
#
# - namespace observabilite, HORS du maillage : un collecteur OpenTelemetry
#   contrib 0.165.0 qui exporte vers Jaeger 2.23.0 ;
# - namespace boutique, DANS le maillage ambient mais sans waypoint : client
#   appelle web, qui appelle api ET stock (podinfo 6.17.0). UN SEUL des deux
#   répond en 1 à 1,5 s. Lequel est tiré au hasard à chaque passage : aucune
#   réponse ne se recopie d'une session à l'autre. web ne fait pas suivre le
#   contexte de trace (podinfo sans --otel-service-name) : sans geste de
#   l'apprenant, chaque saut forme une trace à part.
#
# Rien de ce que l'apprenant doit produire n'existe : ni fournisseur de traces
# dans meshConfig (le setup a rejoué istioctl install), ni Telemetry, ni
# waypoint, ni ConfigMap diagnostic. Rejouable : les deux namespaces sont
# recréés à chaque passage.
#
# Versions et digests relevés le 2026-11-17 (captures CKNE 17-09).
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

PODINFO="ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0"
OTEL="otel/opentelemetry-collector-contrib:0.165.0@sha256:e40d61f10c9a617cca1ffd1be4d7e2b3a4b0f0001798ff07e58cabe82e618cea"
JAEGER="jaegertracing/jaeger:2.23.0@sha256:3823829974ccfc2485d2e48b165579091f32295022ae80ca49704e2f4834116e"
CURL="curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40"

# Ce que l'apprenant a produit disparaît avec les namespaces et la Telemetry.
# Le waypoint est un Gateway de boutique : il part avec le namespace.
kubectl delete telemetry.telemetry.istio.io --all -A --ignore-not-found --wait=true
kubectl delete namespace boutique observabilite --ignore-not-found --wait=true --timeout=240s

# Le service lent, tiré au hasard. Il ne se lit que dans les arguments de son
# conteneur, comme dans une vraie panne : le test le retrouve de la même façon.
if (( RANDOM % 2 )); then LENT=api; else LENT=stock; fi
RETARD=(--random-delay=true --random-delay-unit=ms --random-delay-min=1000 --random-delay-max=1500)
args_de() {  # $1 = service ; rend la liste YAML des arguments de podinfo
  local svc=$1 a=(./podinfo --port=9898)
  [[ $svc == web ]] && a+=(--backend-url=http://api.boutique:9898/echo --backend-url=http://stock.boutique:9898/echo)
  [[ $svc == "$LENT" ]] && a+=("${RETARD[@]}")
  local IFS=,
  echo "[${a[*]}]"
}

kubectl apply -f - <<YAML
apiVersion: v1
kind: Namespace
metadata:
  name: observabilite
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: observabilite
spec:
  selector:
    matchLabels: {app: jaeger}
  template:
    metadata:
      labels: {app: jaeger}
    spec:
      containers:
        - name: jaeger
          image: "$JAEGER"
          ports:
            - containerPort: 4317
            - containerPort: 16686
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
  namespace: observabilite
spec:
  selector: {app: jaeger}
  ports:
    - {name: otlp-grpc, port: 4317, appProtocol: grpc}
    - {name: ui, port: 16686}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector
  namespace: observabilite
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc: {endpoint: 0.0.0.0:4317}
          http: {endpoint: 0.0.0.0:4318}
    processors:
      batch: {}
    exporters:
      otlp_grpc/jaeger:
        endpoint: jaeger.observabilite:4317
        tls: {insecure: true}
      debug: {verbosity: basic}
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [otlp_grpc/jaeger, debug]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observabilite
spec:
  selector:
    matchLabels: {app: otel-collector}
  template:
    metadata:
      labels: {app: otel-collector}
    spec:
      containers:
        - name: collecteur
          image: "$OTEL"
          args: ["--config=/conf/config.yaml"]
          volumeMounts:
            - {name: conf, mountPath: /conf}
      volumes:
        - name: conf
          configMap: {name: otel-collector}
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observabilite
spec:
  selector: {app: otel-collector}
  ports:
    # Le port gRPC du collecteur SANS appProtocol, nommé comme dans bien des
    # manifestes : Istio ne reconnaît pas gRPC dans « otlp-grpc » (préfixe
    # attendu : grpc ou grpc-), et chaque export du waypoint échoue en
    # « protocol error », visible seulement en journal debug. C'est l'une des
    # pannes que le lab fait trouver (mesuré le 2026-11-17, Istio 1.32.0).
    - {name: otlp-grpc, port: 4317}
    - {name: otlp-http, port: 4318}
---
apiVersion: v1
kind: Namespace
metadata:
  name: boutique
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: boutique
spec:
  containers:
    - name: client
      image: "$CURL"
      command: [sleep, "36000"]
YAML

for svc in web api stock; do
  kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $svc
  namespace: boutique
spec:
  selector:
    matchLabels: {app: $svc}
  template:
    metadata:
      labels: {app: $svc}
    spec:
      containers:
        - name: podinfo
          image: "$PODINFO"
          command: $(args_de "$svc")
---
apiVersion: v1
kind: Service
metadata:
  name: $svc
  namespace: boutique
spec:
  selector: {app: $svc}
  ports:
    - {name: http, port: 9898}
YAML
done

kubectl -n observabilite rollout status deployment/jaeger --timeout=240s
kubectl -n observabilite rollout status deployment/otel-collector --timeout=240s
for svc in web api stock; do kubectl -n boutique rollout status deployment/$svc --timeout=240s; done
kubectl -n boutique wait --for=condition=Ready pod/client --timeout=180s

# La chaîne répond de bout en bout, lentement : c'est la situation de départ.
kubectl -n boutique exec client -- curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' \
  -X POST -d bonjour http://web.boutique:9898/echo
kubectl -n boutique get deploy,svc,pod
kubectl -n observabilite get deploy,svc
echo "Situation posée : client -> web -> (api, stock) répond lentement, aucun fournisseur de traces, aucun waypoint."
