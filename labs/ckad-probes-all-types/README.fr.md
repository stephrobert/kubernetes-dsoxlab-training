# Trois sondes sur un Pod : startup, liveness, readiness

Kubernetes ne sait pas, de lui-même, si une application fonctionne. Il le
demande à des **sondes** : des vérifications qu'il répète, et dont le résultat
décide de ce qu'il fait.

- La sonde de **disponibilité** (readiness) dit si le Pod peut recevoir du
  trafic.
- La sonde de **vivacité** (liveness) dit si le conteneur doit être relancé.
- La sonde de **démarrage** (startup) laisse le temps à une application lente
  de démarrer, avant que les deux autres commencent.

Dans ce cours, vous voyez chacune échouer, puis réussir.

Vous travaillez dans un namespace d'essai, `essai-sondes`, avec les Pods
`vitrine`, `gardien`, `lent-court` et `lent-patient`. Le challenge vous
demandera les trois sondes sur une autre application, dans un autre
namespace : vous le ferez seul, à la fin.

Page associée : [Les sondes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/probes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-probes-all-types
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : une sonde de disponibilité qui échoue

Créez le namespace d'essai et un Pod nginx `vitrine`. Sa sonde de
disponibilité demande la page `/pret.html` toutes les 3 secondes. Cette page
n'existe pas encore. `kubectl expose` crée un Service devant le Pod :

```bash
kubectl create namespace essai-sondes
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: vitrine
  labels:
    app: vitrine
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      ports:
        - containerPort: 80
      readinessProbe:
        httpGet:
          path: /pret.html
          port: 80
        periodSeconds: 3
YAML
kubectl expose pod vitrine --port=80 -n essai-sondes
```

```text
namespace/essai-sondes created
pod/vitrine created
service/vitrine exposed
```

15 secondes plus tard :

```bash
sleep 15; kubectl get pod vitrine -n essai-sondes
```

```text
NAME      READY   STATUS    RESTARTS   AGE
vitrine   0/1     Running   0          15s
```

`Running`, mais `0/1` : le conteneur tourne, et il n'est pas prêt. Les
événements disent pourquoi (`Unhealthy` est le motif d'un échec de sonde) :

```bash
kubectl get events -n essai-sondes --field-selector involvedObject.name=vitrine,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2
```

```text
Readiness probe failed: Get "http://10.244.38.69:80/pret.html": dial tcp 10.244.38.69:80: connect: connection refused
Readiness probe failed: HTTP probe failed with statuscode: 404
```

D'abord `connection refused` (nginx démarrait), puis `404` : la page n'existe
pas. Conséquence pour le trafic : le Service connaît l'adresse du Pod, mais la
marque comme non prête.

```bash
kubectl get endpointslices -n essai-sondes -l kubernetes.io/service-name=vitrine -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]} ready={.conditions.ready}{"\n"}{end}'
```

```text
10.244.38.69 ready=false
```

Le Service n'enverra rien à ce Pod tant qu'il n'est pas prêt.

## 📚 Exercice 2 : la disponibilité suit l'application

Créez la page que la sonde attend, puis regardez le Pod 6 secondes plus tard :

```bash
kubectl exec vitrine -n essai-sondes -- sh -c 'echo pret > /usr/share/nginx/html/pret.html'; sleep 6; kubectl get pod vitrine -n essai-sondes
kubectl get endpointslices -n essai-sondes -l kubernetes.io/service-name=vitrine -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]} ready={.conditions.ready}{"\n"}{end}'
```

```text
NAME      READY   STATUS    RESTARTS   AGE
vitrine   1/1     Running   0          21s
10.244.38.69 ready=true
```

Le Pod est prêt, et le Service peut lui envoyer du trafic. Retirez la page :

```bash
kubectl exec vitrine -n essai-sondes -- rm /usr/share/nginx/html/pret.html; sleep 12; kubectl get pod vitrine -n essai-sondes
```

```text
NAME      READY   STATUS    RESTARTS   AGE
vitrine   0/1     Running   0          34s
```

De nouveau `0/1`, mais `RESTARTS 0` : la sonde de disponibilité ne relance
jamais le conteneur. Elle le retire seulement du trafic, et l'y remet dès
qu'il répond.

## 📚 Exercice 3 : une sonde de vivacité qui relance le conteneur

Une sonde n'est pas forcément HTTP. Le type `exec` lance une commande dans le
conteneur : la sonde réussit si la commande sort avec le code 0. Le Pod
`gardien` crée un fichier `/tmp/vivant` au démarrage, et sa sonde de vivacité
vérifie qu'il existe. Après 2 échecs à 3 secondes d'écart, le conteneur est
relancé. `terminationGracePeriodSeconds: 2` raccourcit le délai d'arrêt : sans
lui, Kubernetes attendrait 30 secondes, car `sleep` lancé par `sh` ignore la
demande d'arrêt.

```bash
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: gardien
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: veille
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "touch /tmp/vivant; sleep 3600"]
      livenessProbe:
        exec:
          command: ["cat", "/tmp/vivant"]
        periodSeconds: 3
        failureThreshold: 2
YAML
kubectl wait --for=condition=Ready pod/gardien -n essai-sondes --timeout=60s; kubectl get pod gardien -n essai-sondes
```

```text
pod/gardien created
pod/gardien condition met
NAME      READY   STATUS    RESTARTS   AGE
gardien   1/1     Running   0          0s
```

Supprimez le fichier, comme si l'application s'était figée, puis attendez
20 secondes :

```bash
kubectl exec gardien -n essai-sondes -- rm /tmp/vivant; sleep 20; kubectl get pod gardien -n essai-sondes
```

```text
NAME      READY   STATUS    RESTARTS      AGE
gardien   1/1     Running   1 (12s ago)   20s
```

`RESTARTS 1` : le conteneur a été relancé. Au redémarrage, sa commande a
recréé le fichier, et il est de nouveau en bonne santé. Les événements
racontent l'échec puis la relance :

```bash
kubectl get events -n essai-sondes --field-selector involvedObject.name=gardien,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2; kubectl get events -n essai-sondes --field-selector involvedObject.name=gardien,reason=Killing -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2
```

```text

Liveness probe failed: cat: can't open '/tmp/vivant': No such file or directory
Container veille failed liveness probe, will be restarted
```

## 📚 Exercice 4 : une application lente, une sonde de démarrage trop courte

Le Pod `lent-court` simule une application qui met 20 secondes à démarrer :
il attend, puis lance un petit serveur web sur le port 8080. Sa sonde de
démarrage essaie toutes les 2 secondes, et abandonne après 3 échecs. Elle
tolère donc 2 × 3 = **6 secondes** :

```bash
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent-court
spec:
  containers:
    - name: web
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo demarrage lent; sleep 20; mkdir -p /www; echo ok > /www/index.html; httpd -f -p 8080 -h /www"]
      startupProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 2
        failureThreshold: 3
      livenessProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 10
YAML
```

```text
pod/lent-court created
```

45 secondes plus tard :

```bash
sleep 45; kubectl get pod lent-court -n essai-sondes
kubectl get events -n essai-sondes --field-selector involvedObject.name=lent-court,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2; kubectl get events -n essai-sondes --field-selector involvedObject.name=lent-court,reason=Killing -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -2
```

```text
NAME         READY   STATUS    RESTARTS     AGE
lent-court   0/1     Running   1 (9s ago)   45s
Startup probe failed: Get "http://10.244.38.127:8080/": dial tcp 10.244.38.127:8080: connect: connection refused
Container web failed startup probe, will be restarted
```

Après 6 secondes sans réponse, la sonde de démarrage a abandonné, et
Kubernetes a relancé le conteneur. Au redémarrage, l'application recommence
ses 20 secondes d'attente, et sera relancée de nouveau : elle ne démarrera
jamais. Tant que la sonde de démarrage n'a pas réussi, la sonde de vivacité ne
s'exécute pas.

## 📚 Exercice 5 : la même application, une sonde de démarrage patiente

Même application, mais 20 échecs permis : 2 × 20 = **40 secondes** de
tolérance, de quoi couvrir les 20 secondes de démarrage :

```bash
cat <<'YAML' | kubectl apply -n essai-sondes -f -
apiVersion: v1
kind: Pod
metadata:
  name: lent-patient
spec:
  containers:
    - name: web
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo demarrage lent; sleep 20; mkdir -p /www; echo ok > /www/index.html; httpd -f -p 8080 -h /www"]
      startupProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 2
        failureThreshold: 20
      livenessProbe:
        httpGet:
          path: /
          port: 8080
        periodSeconds: 10
YAML
```

```text
pod/lent-patient created
```

```bash
kubectl wait --for=condition=Ready pod/lent-patient -n essai-sondes --timeout=90s; kubectl get pod lent-patient -n essai-sondes
kubectl get pod lent-patient -n essai-sondes -o jsonpath='demarre={.status.containerStatuses[0].started} pret={.status.containerStatuses[0].ready} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'
```

```text
pod/lent-patient condition met
NAME           READY   STATUS    RESTARTS   AGE
lent-patient   1/1     Running   0          22s
demarre=true pret=true redemarrages=0
```

Prêt au bout de 22 secondes, sans aucun redémarrage. `started=true` dit que la
sonde de démarrage a réussi : la sonde de vivacité a pris le relais.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses Pods et son Service :

```bash
kubectl delete namespace essai-sondes
```

```text
namespace "essai-sondes" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-probes-all-types
dsoxlab check ckad-probes-all-types
```

```text
╭─ Résultat : ckad-probes-all-types ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests   │
╰────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : les trois sondes sur une autre application, avec
assez de patience pour un démarrage lent.

```bash
dsoxlab run ckad-probes-all-types
dsoxlab challenge ckad-probes-all-types
```
