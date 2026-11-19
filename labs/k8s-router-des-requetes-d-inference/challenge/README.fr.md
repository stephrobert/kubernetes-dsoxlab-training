# Challenge : Router des requêtes d'inférence selon la charge des réplicas avec la Gateway API Inference Extension

## La situation

Le cluster kubeadm compte **trois nœuds**, et Istio 1.32 y tourne en mode
ambient, avec la **Gateway API Inference Extension** activée : ses CRD sont
installées et le plan de contrôle d'Istio sait envoyer du trafic vers un
`InferencePool`.

Dans le namespace **`inference`**, un serveur de modèle répond à l'API OpenAI
(`/v1/completions`) sur le port **8000**. C'est un simulateur de vLLM, sans
GPU, qui sert le modèle `meta-llama/Llama-3.1-8B-Instruct`, en **trois
réplicas** répartis sur deux Deployments : `modele-libre` (deux réplicas) et
`modele-sature` (un réplica). Le dernier est **saturé** : ses métriques
affichent une file de 40 requêtes et un cache KV plein à 97 %. Chaque réponse
porte l'en-tête **`x-inference-pod`**, le nom du Pod qui l'a servie.

Un **sélecteur d'endpoints** tourne déjà : le Deployment et le Service
**`selecteur`** (port 9002). Il lit les métriques des réplicas et dit à la
Gateway lequel doit prendre chaque requête. Il n'est **pas prêt** : il attend
un `InferencePool` nommé **`pool-modele`** dans `inference`.

Le cluster n'a aucun répartiteur de charge. Vous êtes sur le control plane,
avec `kubectl` configuré, en root.

## Ce que vous devez obtenir

1. Un **InferencePool** (`inference.networking.k8s.io/v1`) d'`inference`
   regroupe les **trois réplicas** du modèle sur le port 8000 et désigne le
   sélecteur d'endpoints `selecteur`, qui devient prêt.
2. Une **Gateway** de classe `istio` dans `inference` porte un listener HTTP,
   et le cluster la déclare **Programmed**.
3. Une **HTTPRoute** attachée à la Gateway a l'**InferencePool pour
   backend**, et elle est Accepted avec ses références résolues.
4. Des requêtes de complétion envoyées à la Gateway reçoivent **la réponse des
   réplicas**.
5. Les requêtes **évitent le réplica saturé** : sur 30 requêtes, il en reçoit
   10 % au plus.

## La méthode, pas à pas

**Regrouper les réplicas dans un pool.** Un `InferencePool` est le pendant,
pour l'inférence, d'un Service : `spec.selector.matchLabels` choisit les Pods,
`spec.targetPorts` donne leur port, et `spec.endpointPickerRef` désigne le
Service du sélecteur (`name`, `port.number`). Le sélecteur doit prendre **les
trois** réplicas, le saturé compris : le sélecteur d'endpoints ne peut éviter
qu'un réplica qu'il voit. Lisez les étiquettes avec `kubectl get pods -n
inference --show-labels`. Une fois le pool créé, `kubectl get deploy selecteur
-n inference` passe prêt : ses journaux (`kubectl logs deploy/selecteur`)
disent ce qu'il a trouvé.

**Déclarer la Gateway.** `gatewayClassName: istio` et un listener HTTP sur le
port 80. Comme le cluster n'a pas de répartiteur de charge, ajoutez
l'annotation `networking.istio.io/service-type: ClusterIP`, sans quoi la
Gateway reste non Programmed.

**Router vers le pool, pas vers un Service.** Dans l'`HTTPRoute`, le
`backendRef` porte `group: inference.networking.k8s.io`, `kind: InferencePool`
et le nom du pool. La Gateway interroge alors le sélecteur pour chaque requête.
Un `backendRef` vers un Service ordinaire répartirait les requêtes à
l'aveugle : un tiers d'entre elles tomberait sur le réplica saturé.

**Mesurer la répartition.** Prenez l'adresse ClusterIP du Service qu'Istio a
créé pour la Gateway (`kubectl get svc -n inference -l
gateway.networking.k8s.io/gateway-name=<nom>`), puis envoyez des requêtes et
lisez l'en-tête :

```bash
curl -s -o /dev/null -D - -H 'Content-Type: application/json' \
  -d '{"model":"meta-llama/Llama-3.1-8B-Instruct","prompt":"Question 1","max_tokens":8}' \
  http://<ip>/v1/completions | grep -i x-inference-pod
```

Changez de prompt à chaque requête : le sélecteur favorise aussi le réplica qui
a déjà vu le même prompt.

## Comment vous saurez que ça marche

Les tests lisent le pool et vérifient que son sélecteur prend exactement les
trois réplicas, que le sélecteur d'endpoints est prêt, que la Gateway est
Programmed et que la route vers le pool est acceptée. Puis ils envoient de
vraies requêtes de complétion par la Gateway et comptent, en-tête par en-tête,
quel réplica a répondu.

```bash
dsoxlab check k8s-router-des-requetes-d-inference
```
