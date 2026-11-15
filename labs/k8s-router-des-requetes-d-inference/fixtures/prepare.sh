#!/usr/bin/env bash
# Pose la situation : trois replicas du simulateur vLLM dans le namespace
# inference, dont un SATURE, et le selecteur d'endpoints (EPP) qui attend son
# InferencePool. Ni pool, ni Gateway, ni route : c'est le travail.
#
# Le simulateur ghcr.io/llm-d/llm-d-inference-sim:v0.7.1 sert l'API OpenAI
# (/v1/completions) sans GPU et publie les metriques Prometheus d'un vLLM sur
# son port 8000. Avec POD_NAME defini, chaque reponse porte l'en-tete
# x-inference-pod : c'est lui que lit la validation (README du simulateur,
# v0.7.1). Le replica sature publie, par --fake-metrics, une file d'attente de
# 40 requetes et un cache KV plein a 97 % : le selecteur lit ces metriques
# exactement comme celles d'un vrai vLLM.
#
# Le selecteur est l'EPP v1.5.0, le meme que le chart officiel « inferencepool »
# v1.5.0, ecrit a la main pour deux raisons : le chart cree aussi le pool, que
# l'apprenant doit ecrire, et il demande 4 CPU et 8 Gio, ce qu'aucun noeud de
# ce cluster n'a. Pas de sonde de vivacite : sa sante n'est SERVING qu'une
# fois le pool trouve (health.go de la v1.5.0), une sonde de vivacite le
# tuerait en boucle tant que l'apprenant n'a pas ecrit le pool. La sonde de
# disponibilite, elle, dit justement cela.
# Rejouable : le namespace est recree a chaque passage.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que l'apprenant doit produire disparait avec le namespace.
kubectl delete namespace inference --ignore-not-found --wait=true --timeout=240s
kubectl create namespace inference

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: modele-libre
  namespace: inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: modele
      charge: libre
  template:
    metadata:
      labels:
        app: modele
        charge: libre
    spec:
      containers:
        - name: vllm-sim
          image: ghcr.io/llm-d/llm-d-inference-sim:v0.7.1@sha256:74211b5dbf27a867fcefae92067701e0a5fcee827f95156d89718bf3e1bfb845
          args:
            - --model
            - meta-llama/Llama-3.1-8B-Instruct
            - --port
            - "8000"
            - --max-loras
            - "2"
            - --lora-modules
            - '{"name": "reviews-1"}'
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          ports:
            - name: http
              containerPort: 8000
          resources:
            requests:
              cpu: 20m
              memory: 32Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: modele-sature
  namespace: inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: modele
      charge: saturee
  template:
    metadata:
      labels:
        app: modele
        charge: saturee
    spec:
      containers:
        - name: vllm-sim
          image: ghcr.io/llm-d/llm-d-inference-sim:v0.7.1@sha256:74211b5dbf27a867fcefae92067701e0a5fcee827f95156d89718bf3e1bfb845
          args:
            - --model
            - meta-llama/Llama-3.1-8B-Instruct
            - --port
            - "8000"
            - --max-loras
            - "2"
            - --lora-modules
            - '{"name": "reviews-1"}'
            - --fake-metrics
            - '{"running-requests":5,"waiting-requests":40,"kv-cache-usage":0.97,"loras":[{"running":"reviews-1","waiting":"reviews-1","timestamp":1767225600}]}'
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          ports:
            - name: http
              containerPort: 8000
          resources:
            requests:
              cpu: 20m
              memory: 32Mi
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: selecteur
  namespace: inference
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: selecteur
  namespace: inference
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "watch", "list"]
  - apiGroups: ["inference.networking.k8s.io"]
    resources: ["inferencepools"]
    verbs: ["get", "watch", "list"]
  - apiGroups: ["inference.networking.x-k8s.io"]
    resources: ["inferenceobjectives", "inferencemodelrewrites"]
    verbs: ["get", "watch", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: selecteur
  namespace: inference
subjects:
  - kind: ServiceAccount
    name: selecteur
    namespace: inference
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: selecteur
---
# La configuration par defaut du chart inferencepool v1.5.0, pour un vLLM en
# HTTP : la longueur de file, l'occupation du cache KV et le cache de prefixe
# notent chaque replica.
apiVersion: v1
kind: ConfigMap
metadata:
  name: selecteur
  namespace: inference
data:
  default-plugins.yaml: |
    apiVersion: inference.networking.x-k8s.io/v1alpha1
    kind: EndpointPickerConfig
    plugins:
    - type: queue-scorer
    - type: kv-cache-utilization-scorer
    - type: prefix-cache-scorer
    - type: metrics-data-source
      parameters:
        scheme: "http"
        path: "/metrics"
        insecureSkipVerify: true
    - type: core-metrics-extractor
    schedulingProfiles:
    - name: default
      plugins:
      - pluginRef: queue-scorer
        weight: 2
      - pluginRef: kv-cache-utilization-scorer
        weight: 2
      - pluginRef: prefix-cache-scorer
        weight: 3
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: selecteur
  namespace: inference
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: selecteur
  template:
    metadata:
      labels:
        app: selecteur
    spec:
      serviceAccountName: selecteur
      terminationGracePeriodSeconds: 10
      containers:
        - name: epp
          image: registry.k8s.io/gateway-api-inference-extension/epp:v1.5.0@sha256:86c679b057298e68c6e65ff5603e92066d432e77b11f1f81f0a06399694810bc
          args:
            - --pool-name
            - pool-modele
            - --pool-namespace
            - inference
            - --pool-group
            - inference.networking.k8s.io
            - --zap-encoder
            - json
            - --config-file
            - /config/default-plugins.yaml
            - --v
            - "1"
            - --tracing=false
            - --metrics-endpoint-auth=false
          env:
            - name: NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          ports:
            - name: grpc
              containerPort: 9002
            - name: grpc-health
              containerPort: 9003
            - name: metrics
              containerPort: 9090
          readinessProbe:
            grpc:
              port: 9003
              service: inference-extension
            periodSeconds: 2
          volumeMounts:
            - name: config
              mountPath: /config
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 512Mi
      volumes:
        - name: config
          configMap:
            name: selecteur
---
apiVersion: v1
kind: Service
metadata:
  name: selecteur
  namespace: inference
spec:
  selector:
    app: selecteur
  ports:
    - name: grpc-ext-proc
      port: 9002
      targetPort: 9002
      appProtocol: http2
    - name: http-metrics
      port: 9090
      targetPort: 9090
---
# Le selecteur sert son gRPC en TLS (certificat auto-signe, --secure-serving
# vrai par defaut) : la passerelle d'Istio doit donc lui parler en TLS, sans
# verifier ce certificat. C'est la DestinationRule que pose le chart officiel
# pour le fournisseur istio.
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: selecteur
  namespace: inference
spec:
  host: selecteur.inference.svc.cluster.local
  trafficPolicy:
    tls:
      mode: SIMPLE
      insecureSkipVerify: true
YAML

kubectl -n inference rollout status deployment/modele-libre --timeout=300s
kubectl -n inference rollout status deployment/modele-sature --timeout=300s
# Le selecteur n'est PAS attendu pret : il ne le sera qu'une fois le pool
# ecrit. On attend seulement que son conteneur tourne.
kubectl -n inference wait --for=jsonpath='{.status.phase}'=Running pod -l app=selecteur --timeout=300s

# Controle de la situation : le replica sature publie bien sa file d'attente.
sature=$(kubectl -n inference get pod -l charge=saturee -o jsonpath='{.items[0].status.podIP}')
curl -s --max-time 5 "http://${sature}:8000/metrics" | grep -E '^vllm:num_requests_waiting' || true

kubectl -n inference get pods -o wide
echo "Situation posee : trois replicas, dont un sature, et un selecteur sans pool."
