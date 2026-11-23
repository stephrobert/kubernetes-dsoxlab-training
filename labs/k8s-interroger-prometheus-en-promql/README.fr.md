# Interroger Prometheus en PromQL

La leçon présente PromQL : les sélecteurs de labels, les compteurs lus par
`rate()` et `increase()`, les agrégations par label, les percentiles calculés
par `histogram_quantile()` et le classement par `topk()`. Ce cours vous fait
écrire chacune de ces requêtes sur le Prometheus du lab, et regarder ce
qu'elle rend.

Les questions du cours portent sur d'autres métriques que celles du
challenge : vous le ferez seul, à la fin.

Page associée : [PromQL](https://www.stephane-robert.info/docs/outils/observabilite/metriques/prometheus/promql/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-interroger-prometheus-en-promql
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm. Le lab a installé Prometheus dans le namespace `supervision` : depuis
ce nœud, il répond sur `http://localhost:30090`. Il collecte kube-state-metrics,
le kubelet et cAdvisor sur les trois nœuds.

Pour interroger Prometheus sans navigateur, définissez une petite fonction
`q`. Elle envoie une requête PromQL à l'API et affiche chaque série sur une
ligne, avec ses labels et sa valeur (quelques labels techniques sont masqués
pour garder les lignes courtes) :

```bash
q() { curl -fsS http://localhost:30090/api/v1/query --data-urlencode "query=$1" | jq -r '.data.result[] | "\(.metric | del(.__name__, .instance, .uid, .id, .name, .image) | to_entries | map("\(.key)=\(.value)") | join(",")) => \(.value[1])"'; }
```

Gardez le même terminal jusqu'à la fin : la fonction n'existe que dans lui.
Les sorties montrées dans ce cours ont été relevées sur cette machine le
23 novembre 2026, avec Kubernetes v1.37.2 et Prometheus v3.16.0. Les valeurs
changent d'une minute à l'autre : regardez leur forme et leurs rapports, pas
les chiffres exacts.

## 🔎 Exercice 1 : filtrer par labels

Le nom d'une métrique seul rend toutes ses séries. `up` vaut 1 pour chaque
cible que Prometheus a pu lire. Filtrez-la ensuite par son label `job`, avec
une expression régulière, puis avec une différence :

```bash
q 'up'
echo '--- job=~"kube"'; q 'up{job=~"kube"}'
echo '--- job=~"kube.*"'; q 'up{job=~"kube.*"}'
echo '--- job!="cadvisor"'; q 'count(up{job!="cadvisor"})'
```

```text
job=cadvisor,node=k8s-cp.lab => 1
job=cadvisor,node=k8s-w2.lab => 1
job=cadvisor,node=k8s-w1.lab => 1
job=kubelet,node=k8s-w1.lab => 1
job=kubelet,node=k8s-w2.lab => 1
job=kubelet,node=k8s-cp.lab => 1
job=prometheus => 1
job=kube-state-metrics => 1
--- job=~"kube"
--- job=~"kube.*"
job=kubelet,node=k8s-w1.lab => 1
job=kubelet,node=k8s-w2.lab => 1
job=kubelet,node=k8s-cp.lab => 1
job=kube-state-metrics => 1
--- job!="cadvisor"
 => 5
```

Huit cibles : Prometheus lui-même, kube-state-metrics, et le kubelet et
cAdvisor sur chacun des trois nœuds. `job=~"kube"` ne rend **rien** : les
expressions régulières de PromQL sont ancrées, elles doivent couvrir toute la
valeur. Il faut `kube.*` pour trouver `kubelet` et `kube-state-metrics`.
`count()` compte les séries qui restent après le filtre.

## 📈 Exercice 2 : lire un compteur avec rate() et increase()

`prometheus_http_requests_total` compte les requêtes que Prometheus a servies,
depuis son démarrage. Envoyez-lui 60 requêtes, une par seconde, puis lisez le
compteur brut, son taux par seconde sur 5 minutes, et son augmentation sur la
même durée :

```bash
for i in $(seq 60); do curl -s -o /dev/null http://localhost:30090/api/v1/query --data-urlencode 'query=up'; sleep 1; done
sleep 30
q 'prometheus_http_requests_total{handler="/api/v1/query"}'
q 'rate(prometheus_http_requests_total{handler="/api/v1/query"}[5m])'
q 'increase(prometheus_http_requests_total{handler="/api/v1/query"}[5m])'
q 'rate(prometheus_http_requests_total{handler="/api/v1/query"}[5m]) * 300'
```

```text
code=200,handler=/api/v1/query,job=prometheus => 127
code=200,handler=/api/v1/query,job=prometheus => 0.2245614035087719
code=200,handler=/api/v1/query,job=prometheus => 67.36842105263158
code=200,handler=/api/v1/query,job=prometheus => 67.36842105263158
```

Le compteur brut ne fait que monter : il ne dit rien du rythme. `rate()` donne
un nombre de requêtes par seconde, en moyenne sur 5 minutes. `increase()`
donne un nombre de requêtes sur ces 5 minutes, et c'est `rate()` multiplié
par 300 secondes, ici au chiffre près : les deux fonctions lisent les mêmes
points. Les deux résultats ne sont pas des entiers, parce que Prometheus
extrapole entre ses mesures, prises toutes les 15 secondes.

## ➕ Exercice 3 : agréger par label

`container_memory_working_set_bytes` donne la mémoire de chaque conteneur.
Additionnez-la pour tout le cluster, puis par nœud. Comptez ensuite les Pods
de chaque nœud avec `kube_pod_info`, qui publie une série par Pod :

```bash
q 'sum(container_memory_working_set_bytes{container!=""})'
q 'sum by (node) (container_memory_working_set_bytes{container!=""})'
q 'count by (node) (kube_pod_info)'
```

```text
 => 2518261760
node=k8s-cp.lab => 1849020416
node=k8s-w2.lab => 183332864
node=k8s-w1.lab => 485908480
node=k8s-w1.lab => 20
node=k8s-w2.lab => 16
node=k8s-cp.lab => 24
```

Sans `by`, `sum()` efface tous les labels et rend un seul nombre. Avec
`by (node)`, il garde le label `node` et rend une valeur par nœud. Le filtre
`container!=""` écarte les séries que cAdvisor publie pour le Pod entier :
sans lui, chaque conteneur serait compté deux fois.

## 📊 Exercice 4 : un percentile avec histogram_quantile()

`prometheus_http_response_size_bytes` est un histogramme : la taille de chaque
réponse tombe dans des tranches (buckets) bornées par le label `le`. Regardez
les tranches d'un handler, calculez le 95e percentile de la taille des
réponses par handler, puis refaites le calcul en oubliant le label `le` :

```bash
q 'prometheus_http_response_size_bytes_bucket{handler="/api/v1/query"}'
q 'histogram_quantile(0.95, sum by (handler, le) (rate(prometheus_http_response_size_bytes_bucket[5m]))) > 0'
q 'histogram_quantile(0.95, sum by (handler) (rate(prometheus_http_response_size_bytes_bucket[5m])))' | wc -l
```

```text
handler=/api/v1/query,job=prometheus,le=100.0 => 1
handler=/api/v1/query,job=prometheus,le=1000.0 => 6
handler=/api/v1/query,job=prometheus,le=10000.0 => 127
handler=/api/v1/query,job=prometheus,le=100000.0 => 127
handler=/api/v1/query,job=prometheus,le=1e+06 => 127
handler=/api/v1/query,job=prometheus,le=1e+07 => 127
handler=/api/v1/query,job=prometheus,le=1e+08 => 127
handler=/api/v1/query,job=prometheus,le=1e+09 => 127
handler=/api/v1/query,job=prometheus,le=+Inf => 127
handler=/-/ready => 95
handler=/api/v1/targets => 95500
handler=/metrics => 95499.99999999999
handler=/api/v1/query => 9527.868852459016
0
```

Chaque tranche compte les réponses inférieures ou égales à sa borne : les
nombres ne font que croître jusqu'à `+Inf`, qui les compte toutes.
`histogram_quantile()` rend, par handler, la taille sous laquelle tombent 95 %
des réponses. Le `> 0` écarte les handlers qui n'ont servi aucune réponse sur
la fenêtre. Sans `le` dans le `by`, la fonction n'a plus de tranches à lire et
ne rend aucune série : la dernière commande en compte 0.

## 🏆 Exercice 5 : classer avec topk() et filtrer par une comparaison

Classez les trois Pods qui utilisent le plus de mémoire, puis gardez ceux qui
dépassent 100 Mo. Enfin, ajoutez `bool` à la comparaison, sur les seuls Pods de
`kube-system` :

```bash
q 'topk(3, sum by (namespace, pod) (container_memory_working_set_bytes{container!=""}))'
q 'sum by (namespace, pod) (container_memory_working_set_bytes{container!=""}) > 100e6'
q 'sum by (namespace, pod) (container_memory_working_set_bytes{container!="",namespace="kube-system"}) > bool 100e6'
```

```text
namespace=kube-system,pod=kube-apiserver-k8s-cp.lab => 998899712
namespace=tigera-operator,pod=tigera-operator-d78bcd95d-cvjvv => 117825536
namespace=kube-system,pod=kube-controller-manager-k8s-cp.lab => 107343872
namespace=kube-system,pod=kube-apiserver-k8s-cp.lab => 998899712
namespace=kube-system,pod=kube-controller-manager-k8s-cp.lab => 107343872
namespace=supervision,pod=prometheus-db77b7f4b-tsgq8 => 103297024
namespace=tigera-operator,pod=tigera-operator-d78bcd95d-cvjvv => 117825536
namespace=kube-system,pod=etcd-k8s-cp.lab => 0
namespace=kube-system,pod=kube-apiserver-k8s-cp.lab => 1
namespace=kube-system,pod=kube-controller-manager-k8s-cp.lab => 1
namespace=kube-system,pod=kube-proxy-m2nm7 => 0
namespace=kube-system,pod=kube-scheduler-k8s-cp.lab => 0
namespace=kube-system,pod=kube-proxy-75bqj => 0
namespace=kube-system,pod=kube-state-metrics-54cc45d487-c6rtj => 0
namespace=kube-system,pod=coredns-559f6c778d-gnlpc => 0
namespace=kube-system,pod=coredns-559f6c778d-ls5cx => 0
namespace=kube-system,pod=kube-proxy-pcbrz => 0
```

`topk(3, ...)` garde les trois plus grandes valeurs. Une comparaison seule
**filtre** : elle ne garde que les séries qui la respectent, avec leur valeur
d'origine. C'est ce qui fait qu'une alerte se déclenche dès que son résultat
n'est pas vide. Avec `bool`, la comparaison garde toutes les séries et les
remplace par 1 ou 0.

## 🧹 Nettoyage

Ce cours n'a créé aucun objet dans le cluster : les requêtes n'écrivent rien.
Quittez la machine et remettez le lab à zéro. `dsoxlab reset` rejoue le
nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-interroger-prometheus-en-promql
dsoxlab check k8s-interroger-prometheus-en-promql
```

```text
╭─ Résultat : k8s-interroger-prometheus-en-promql ─╮
│  0 / 100 pts                                     │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                 │
╰──────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : écrire les quatre requêtes que l'équipe
d'exploitation demande, et les ranger dans un ConfigMap.

```bash
dsoxlab run k8s-interroger-prometheus-en-promql
dsoxlab challenge k8s-interroger-prometheus-en-promql
```
