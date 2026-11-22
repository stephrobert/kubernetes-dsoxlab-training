# Router des requêtes d'inférence

La leçon place une Gateway d'Istio devant un groupe de serveurs de modèle,
un InferencePool, pour que chaque requête aille au réplica le moins chargé.
C'est le challenge du lab : ce cours ne crée ni pool, ni Gateway, ni route.
Il travaille ce que le pool suppose : parler à un serveur de modèle par son
API, reconnaître ses erreurs, recevoir une réponse en flux, et lire les
métriques que le sélecteur d'endpoints consulte pour choisir un réplica.

Vous travaillez dans le namespace `essai-inference`, avec deux simulateurs
d'un serveur vLLM d'essai, `sim-libre` et `sim-charge`, qui servent un modèle
fictif, `essai/petit-modele`, et un client `curl`. Le challenge porte sur
d'autres réplicas, dans `inference` : vous le ferez seul, à la fin.

Page associée : [Router du trafic d'inférence](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/trafic-llm/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-router-des-requetes-d-inference
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le control plane du cluster
kubeadm. Posez les objets d'essai. Le simulateur, `llm-d-inference-sim`,
imite l'API d'un serveur vLLM sans GPU. `sim-charge` reçoit l'option
`--fake-metrics`, qui lui fait publier une charge inventée : 2 requêtes en
cours, 12 en attente, un cache rempli à 60 %.

```bash
kubectl create namespace essai-inference; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sim-libre
  namespace: essai-inference
spec:
  containers:
    - name: vllm-sim
      image: ghcr.io/llm-d/llm-d-inference-sim:v0.7.1@sha256:74211b5dbf27a867fcefae92067701e0a5fcee827f95156d89718bf3e1bfb845
      args: ["--model", "essai/petit-modele", "--port", "8000"]
      env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
---
apiVersion: v1
kind: Pod
metadata:
  name: sim-charge
  namespace: essai-inference
spec:
  containers:
    - name: vllm-sim
      image: ghcr.io/llm-d/llm-d-inference-sim:v0.7.1@sha256:74211b5dbf27a867fcefae92067701e0a5fcee827f95156d89718bf3e1bfb845
      args: ["--model", "essai/petit-modele", "--port", "8000", "--fake-metrics", '{"running-requests":2,"waiting-requests":12,"kv-cache-usage":0.6}']
      env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: essai-inference
spec:
  containers:
    - name: curl
      image: curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40
      command: ["sleep", "3600"]
YAML
kubectl -n essai-inference wait --for=condition=Ready pod --all --timeout=180s; sleep 5
libre=$(kubectl -n essai-inference get pod sim-libre -o jsonpath='{.status.podIP}')
charge=$(kubectl -n essai-inference get pod sim-charge -o jsonpath='{.status.podIP}')
echo "libre=$libre charge=$charge"
```

```text
namespace/essai-inference created
pod/sim-libre created
pod/sim-charge created
pod/client created
pod/client condition met
pod/sim-charge condition met
pod/sim-libre condition met
libre=10.244.223.14 charge=10.244.38.125
```

Les sorties montrées dans ce cours ont été relevées sur cette machine le
23 novembre 2026 (Kubernetes v1.37.2, llm-d-inference-sim v0.7.1).

## 📚 Exercice 1 : demander quels modèles sont servis

Un serveur vLLM parle l'API d'OpenAI. La route `/v1/models` liste les modèles
qu'il sert. C'est la première question à poser à un serveur inconnu :

```bash
kubectl -n essai-inference exec client -- curl -s "http://$libre:8000/v1/models"
```

```text
{"object":"list","data":[{"id":"essai/petit-modele","object":"model","created":1795390878,"owned_by":"vllm","root":"essai/petit-modele","parent":null}]}
```

Le serveur sert un modèle, `essai/petit-modele`. C'est ce nom exact, champ
`id`, qu'une requête de complétion doit porter.

## 💬 Exercice 2 : une complétion, et un modèle inconnu

Envoyez une requête de complétion, en gardant les en-têtes de la réponse
(`-D -`) à part du corps :

```bash
kubectl -n essai-inference exec client -- curl -s -D - -o /tmp/r.json "http://$libre:8000/v1/completions" -H 'Content-Type: application/json' -d '{"model":"essai/petit-modele","prompt":"Bonjour","max_tokens":5}' | grep -i -E '^HTTP|x-inference'
kubectl -n essai-inference exec client -- cat /tmp/r.json
```

```text
HTTP/1.1 200 OK
X-Inference-Pod: sim-libre
X-Inference-Port: 8000
{"id":"cmpl-e4cc7ef2-811e-53d1-b407-386353a4059e","created":1795390878,"model":"essai/petit-modele","usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2},"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":"stop","text":"I "}]}
```

Le corps donne le texte produit (`choices[0].text`) et le décompte des
jetons (`usage`), l'unité dans laquelle on mesure le travail d'un modèle. Le
simulateur invente le texte, sans aucun sens. Les en-têtes, eux, comptent :
`X-Inference-Pod` nomme le réplica qui a répondu. Derrière un groupe de
réplicas, c'est par lui qu'on sait qui a servi la requête. Demandez
maintenant un modèle que le serveur n'a pas :

```bash
kubectl -n essai-inference exec client -- curl -s -w '\n%{http_code}\n' "http://$libre:8000/v1/completions" -H 'Content-Type: application/json' -d '{"model":"autre-modele","prompt":"Bonjour","max_tokens":5}'
```

```text
{"error":{"message":"The model `autre-modele` does not exist.","type":"NotFoundError","param":null,"code":404}}
404
```

Un code **404** et une erreur en JSON qui nomme le modèle demandé. Une
faute de frappe dans le nom du modèle ressemble donc à une route absente :
lisez le corps de l'erreur avant de chercher du côté du réseau.

## 🌊 Exercice 3 : une réponse en flux

Un modèle produit son texte jeton par jeton. Avec `"stream": true`, le
serveur envoie chaque morceau dès qu'il est prêt. L'option `-N` de `curl`
affiche les morceaux à leur arrivée :

```bash
kubectl -n essai-inference exec client -- curl -s -N "http://$libre:8000/v1/completions" -H 'Content-Type: application/json' -d '{"model":"essai/petit-modele","prompt":"Bonjour","max_tokens":3,"stream":true}'
```

```text
data: {"id":"cmpl-311386e2-0629-50f2-96c5-5f7cb5405335","created":1795390878,"model":"essai/petit-modele","usage":null,"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":null,"text":"Today "}]}

data: {"id":"cmpl-311386e2-0629-50f2-96c5-5f7cb5405335","created":1795390878,"model":"essai/petit-modele","usage":null,"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":null,"text":"is "}]}

data: {"id":"cmpl-311386e2-0629-50f2-96c5-5f7cb5405335","created":1795390878,"model":"essai/petit-modele","usage":null,"object":"text_completion","kv_transfer_params":null,"choices":[{"index":0,"finish_reason":"length","text":"a "}]}

data: [DONE]
```

La réponse arrive en trois événements `data:`, un par jeton, puis
`data: [DONE]`. Le dernier morceau porte `finish_reason: "length"` : le
modèle s'est arrêté parce qu'il a atteint `max_tokens`. Une requête en flux
garde la connexion ouverte jusqu'au dernier morceau : c'est une des raisons
pour lesquelles une requête d'inférence occupe un réplica bien plus
longtemps qu'une requête web ordinaire.

## 📈 Exercice 4 : ce que le sélecteur lit pour choisir

Le sélecteur d'endpoints d'un InferencePool ne répartit pas au hasard : il
lit les métriques de chaque réplica. Lisez les trois qui décrivent la charge,
sur vos deux simulateurs :

```bash
for p in libre charge; do ip=$(kubectl -n essai-inference get pod sim-$p -o jsonpath='{.status.podIP}'); echo "--- sim-$p"; kubectl -n essai-inference exec client -- curl -s "http://$ip:8000/metrics" | grep -E '^vllm:(num_requests_(running|waiting)|kv_cache_usage_perc|gpu_cache_usage_perc)'; done
```

```text
--- sim-libre
vllm:kv_cache_usage_perc{model_name="essai/petit-modele"} 0
vllm:num_requests_running{model_name="essai/petit-modele"} 0
vllm:num_requests_waiting{model_name="essai/petit-modele"} 0
--- sim-charge
vllm:kv_cache_usage_perc{model_name="essai/petit-modele"} 0.6000000238418579
vllm:num_requests_running{model_name="essai/petit-modele"} 2
vllm:num_requests_waiting{model_name="essai/petit-modele"} 12
```

`sim-charge` publie 2 requêtes en cours, 12 en attente et un cache KV (la
mémoire où le modèle garde le contexte des requêtes) rempli à 60 %.
`sim-libre` publie zéro partout. Un Service ordinaire enverrait autant de
requêtes à l'un qu'à l'autre, parce qu'il ne lit rien de tout cela. Le
sélecteur, lui, s'appuie sur ces valeurs pour écarter `sim-charge`. La
métrique `vllm:gpu_cache_usage_perc` du filtre n'apparaît pas : cette version
du simulateur publie le nom `vllm:kv_cache_usage_perc`.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-inference --wait=true --timeout=120s
```

```text
namespace "essai-inference" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-router-des-requetes-d-inference
dsoxlab check k8s-router-des-requetes-d-inference
```

```text
╭─ Résultat : k8s-router-des-requetes-d-inference ─╮
│  0 / 100 pts                                     │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests                 │
╰──────────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : regrouper les réplicas d'un modèle dans un
InferencePool, le servir par une Gateway d'Istio, et prouver que les
requêtes évitent le réplica saturé.

```bash
dsoxlab run k8s-router-des-requetes-d-inference
dsoxlab challenge k8s-router-des-requetes-d-inference
```
