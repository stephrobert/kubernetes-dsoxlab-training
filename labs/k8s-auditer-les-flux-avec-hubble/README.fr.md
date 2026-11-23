# Observer les flux avec Hubble

La leçon se sert de Hubble pour retrouver un flux refusé, le compter et le
consigner. Ce cours se sert de Hubble sur des flux **acceptés**, pour ce que
la leçon ne montre pas : suivre une connexion vue par deux agents, interroger
tout le cluster d'un coup par le relais, rendre visibles les noms DNS qu'un
Pod demande, lire les métriques DNS, et traduire des options de
`hubble observe` en filtre JSON.

Vous travaillez dans le namespace `essai-hubble`, avec un serveur web et une
sonde qui l'appelle toutes les 5 secondes. Le challenge porte sur un autre
namespace, d'autres Pods et des flux refusés : vous le ferez seul, à la fin.

Page associée : [Observer, mesurer et auditer les flux avec Hubble](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/hubble/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-auditer-les-flux-avec-hubble
```

Vous êtes maintenant connecté à `net-cp.lab`, le plan de contrôle du cluster
Cilium. Posez les objets d'essai : un serveur nginx sur `net-w1`, son
Service, et une sonde sur `net-w2` qui l'appelle en boucle.

```bash
kubectl create namespace essai-hubble; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: serveur
  namespace: essai-hubble
  labels:
    app: serveur
spec:
  nodeName: net-w1.lab
  containers:
    - name: web
      image: nginx:1.30.6
---
apiVersion: v1
kind: Service
metadata:
  name: serveur
  namespace: essai-hubble
spec:
  selector:
    app: serveur
  ports:
    - port: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: sonde
  namespace: essai-hubble
spec:
  nodeName: net-w2.lab
  containers:
    - name: client
      image: busybox:1.38.0
      command: ["sh", "-c", "while true; do wget -q -O /dev/null 'http://serveur'; sleep 5; done"]
YAML
kubectl -n essai-hubble wait --for=condition=Ready pod/serveur pod/sonde --timeout=120s
```

```text
namespace/essai-hubble created
pod/serveur created
service/serveur created
pod/sonde created
pod/serveur condition met
pod/sonde condition met
```

Les sorties montrées dans ce cours ont été relevées sur ces machines le
22 novembre 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🔭 Exercice 1 : une connexion, vue par deux agents

Chaque agent Cilium ne voit que les flux des Pods de son nœud. Une connexion
entre deux nœuds est donc vue deux fois. Trouvez l'agent de chaque worker,
puis demandez aux deux la même connexion, de la sonde vers le serveur :

```bash
w1=$(kubectl -n kube-system get pods -l k8s-app=cilium --field-selector spec.nodeName=net-w1.lab -o name)
w2=$(kubectl -n kube-system get pods -l k8s-app=cilium --field-selector spec.nodeName=net-w2.lab -o name)
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --from-pod essai-hubble/sonde --to-pod essai-hubble/serveur --last 4
kubectl -n kube-system exec $w1 -c cilium-agent -- hubble observe --from-pod essai-hubble/sonde --to-pod essai-hubble/serveur --last 4
```

```text
Nov 22 22:11:47.896: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: SYN)
Nov 22 22:11:47.897: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK)
Nov 22 22:11:47.897: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, PSH)
Nov 22 22:11:47.898: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, FIN)
Nov 22 22:11:47.903: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: SYN)
Nov 22 22:11:47.904: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK)
Nov 22 22:11:47.904: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, PSH)
Nov 22 22:11:47.905: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, FIN)
```

Les quatre premières lignes viennent de l'agent de `net-w2`, les quatre
suivantes de celui de `net-w1`. Le port source, `44604`, est le même : c'est
la même connexion, du `SYN` au `FIN`. Ce qui change, c'est le **point
d'observation**. Sur `net-w2`, le paquet part `to-overlay`, vers le tunnel qui
relie les nœuds. Sur `net-w1`, il arrive `to-endpoint`, livré au Pod serveur.
Le Service n'apparaît nulle part : Cilium a déjà remplacé son adresse par
celle du Pod.

## 🛰️ Exercice 2 : tout le cluster d'un coup, par le relais

Le relais Hubble rassemble les flux de tous les agents. Le binaire `hubble`
de l'agent sait l'interroger avec `--server`. Le relais a une adresse de
Service, que vous lisez avant de l'appeler :

```bash
relais=$(kubectl -n kube-system get svc hubble-relay -o jsonpath='{.spec.clusterIP}')
kubectl -n kube-system exec $w1 -c cilium-agent -- hubble observe --server $relais:80 --namespace essai-hubble --last 2
```

```text
Nov 22 22:11:47.898: essai-hubble/sonde:44604 (ID:15653) <- essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, FIN, PSH)
Nov 22 22:11:47.898: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, FIN)
Nov 22 22:11:47.901: essai-hubble/sonde:37889 (ID:15653) -> kube-system/coredns-559f6c778d-hzktv:53 (ID:19510) to-endpoint FORWARDED (UDP)
Nov 22 22:11:47.902: essai-hubble/sonde:37889 (ID:15653) <- kube-system/coredns-559f6c778d-hzktv:53 (ID:19510) to-overlay FORWARDED (UDP)
Nov 22 22:11:47.905: essai-hubble/sonde:44604 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-endpoint FORWARDED (TCP Flags: ACK, FIN)
Nov 22 22:11:47.905: essai-hubble/sonde:44604 (ID:15653) <- essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK)
```

Vous avez demandé 2 flux, et vous en recevez 6 : le relais applique `--last`
**à chaque nœud**, puis trie les réponses par heure. Les deux lignes DNS
viennent du nœud qui porte ce Pod CoreDNS. Le relais montre aussi le sens du
retour (`<-`) que l'exercice 1 avait filtré. Il est le bon outil quand vous
ne savez pas encore sur quel nœud regarder. Comptez avec ce `--last` par nœud
quand vous limitez une sortie.

## 🏷️ Exercice 3 : voir les noms DNS qu'un Pod demande

Demandez à l'agent de `net-w2` les flux DNS de la sonde, puis ses flux UDP
vers le port 53 :

```bash
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol dns --last 2
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol udp --to-port 53 --last 1
```

```text
Nov 22 22:11:47.895: essai-hubble/sonde:37889 (ID:15653) -> kube-system/coredns-559f6c778d-hzktv:53 (ID:19510) to-overlay FORWARDED (UDP)
```

Le filtre `--protocol dns` ne rend rien, alors que la sonde interroge CoreDNS
toutes les 5 secondes : la seconde commande le prouve. Hubble voit des
paquets UDP, pas des questions DNS. Pour lire les noms, Cilium doit faire
passer le DNS du Pod par son proxy, et c'est une règle DNS dans une
CiliumNetworkPolicy qui le déclenche. Posez une politique qui autorise tout
nom (`matchPattern: "*"`) vers CoreDNS, et tout trafic vers les Pods du
namespace :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: voir-le-dns
  namespace: essai-hubble
spec:
  endpointSelector:
    matchLabels: {}
  egress:
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: ANY
          rules:
            dns:
              - matchPattern: "*"
    - toEndpoints:
        - {}
YAML
sleep 15
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol dns --last 4
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --from-pod essai-hubble/sonde --to-pod essai-hubble/serveur --last 1
```

```text
ciliumnetworkpolicy.cilium.io/voir-le-dns created
Nov 22 22:12:02.915: essai-hubble/sonde:44697 (ID:15653) -> kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-request proxy FORWARDED (DNS Query serveur.essai-hubble.svc.cluster.local. AAAA)
Nov 22 22:12:02.915: essai-hubble/sonde:44697 (ID:15653) -> kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-request proxy FORWARDED (DNS Query serveur.essai-hubble.svc.cluster.local. A)
Nov 22 22:12:02.916: essai-hubble/sonde:44697 (ID:15653) <- kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-response proxy FORWARDED (DNS Answer  TTL: 4294967295 (Proxy serveur.essai-hubble.svc.cluster.local. AAAA))
Nov 22 22:12:02.916: essai-hubble/sonde:44697 (ID:15653) <- kube-system/coredns-559f6c778d-mql8q:53 (ID:19510) dns-response proxy FORWARDED (DNS Answer "10.110.210.236" TTL: 30 (Proxy serveur.essai-hubble.svc.cluster.local. A))
Nov 22 22:12:02.918: essai-hubble/sonde:41190 (ID:15653) -> essai-hubble/serveur:80 (ID:14478) to-overlay FORWARDED (TCP Flags: ACK, FIN)
```

Les flux portent maintenant `dns-request proxy` et `dns-response proxy` : le
nom demandé, `serveur.essai-hubble.svc.cluster.local.`, le type (`A` pour
IPv4, `AAAA` pour IPv6) et la réponse, l'adresse du Service. La question
`AAAA` revient sans adresse : le Service n'a pas d'adresse IPv6. La dernière
ligne montre que la sonde joint toujours son serveur. C'est le rôle de la
seconde règle : une politique d'egress refuse tout ce qu'elle ne cite pas, et
sans cette règle le trafic vers le serveur ne serait plus autorisé.

## 📈 Exercice 4 : les métriques DNS du nœud

Le cluster active la famille de métriques `dns` de Hubble. Ses compteurs ne
bougent que pour le DNS qui passe par le proxy, donc depuis l'exercice 3.
Lisez-les sur le port 9965 de `net-w2` (`10.10.50.16`, donné par
`kubectl get node net-w2.lab -o wide`) :

```bash
curl -s http://10.10.50.16:9965/metrics | grep -E '^hubble_dns_(queries|responses)_total'
```

```text
hubble_dns_queries_total{ips_returned="0",qtypes="A",rcode=""} 16
hubble_dns_queries_total{ips_returned="0",qtypes="AAAA",rcode=""} 16
hubble_dns_responses_total{ips_returned="0",qtypes="AAAA",rcode="No Error"} 16
hubble_dns_responses_total{ips_returned="1",qtypes="A",rcode="No Error"} 16
```

Les questions et les réponses sont comptées à part. Les réponses portent le
code de retour (`rcode`) et le nombre d'adresses rendues : une réponse `A`
rend une adresse, une réponse `AAAA` aucune, et les deux disent `No Error`.
Une étiquette `rcode` différente de `No Error` signale des noms qui ne se
résolvent pas. Ce compteur appartient à l'agent, pas au namespace : il cumule tout le DNS
passé par le proxy de ce nœud depuis le démarrage de l'agent. Comparez deux
lectures plutôt qu'une valeur seule.

## 🧩 Exercice 5 : traduire des options en filtre JSON

L'export de Hubble et ses réglages se décrivent par des filtres JSON, pas par
des options de ligne de commande. `--print-raw-filters` donne la traduction
d'une commande sans rien lire :

```bash
kubectl -n kube-system exec $w2 -c cilium-agent -- hubble observe --pod essai-hubble/sonde --protocol dns --print-raw-filters
```

```text
allowlist:
    - '{"source_pod":["essai-hubble/sonde"],"protocol":["dns"]}'
    - '{"destination_pod":["essai-hubble/sonde"],"protocol":["dns"]}'
```

L'option `--pod` devient **deux** filtres, un pour chaque sens : la sonde
comme source, puis comme destination. Dans chaque filtre, les deux champs se
combinent (ET), et les deux filtres s'additionnent (OU). C'est la façon la
plus sûre d'écrire un filtre JSON : partir de la commande qui affiche déjà
les bons flux, et recopier sa traduction.

## 🧹 Nettoyage

Supprimez le namespace d'essai. La CiliumNetworkPolicy, rattachée au
namespace, part avec lui :

```bash
kubectl delete namespace essai-hubble --wait=true --timeout=120s
```

```text
namespace "essai-hubble" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-auditer-les-flux-avec-hubble
dsoxlab check k8s-auditer-les-flux-avec-hubble
```

```text
╭─ Résultat : k8s-auditer-les-flux-avec-hubble ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests              │
╰───────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un client d'une API ne reçoit plus de réponse.
Retrouvez-le avec Hubble sans lever la politique, comptez ses refus et
gardez-en une trace sur le nœud.

```bash
dsoxlab run k8s-auditer-les-flux-avec-hubble
dsoxlab challenge k8s-auditer-les-flux-avec-hubble
```
