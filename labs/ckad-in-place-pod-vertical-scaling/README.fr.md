# Redimensionner un Pod en place, sans le redémarrer

Changer le budget d'un Pod voulait longtemps dire le recréer, et couper ce
qu'il faisait. Kubernetes sait maintenant **redimensionner un Pod en place** :
changer ses requests et ses limits pendant qu'il tourne. Dans ce cours, vous
préparez un Pod au redimensionnement, vous voyez la voie ordinaire refusée,
vous passez par la bonne porte, vous choisissez quelle ressource redémarre le
conteneur, et vous demandez un redimensionnement impossible.

Vous travaillez dans un namespace d'essai, `essai-resize`, avec les Pods
`souple` et `strict`. Le challenge vous demandera de redimensionner un autre
Pod, dans un autre namespace : vous le ferez seul, à la fin.

Page associée : [Requests et limits](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/requests-limits/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-in-place-pod-vertical-scaling
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : un Pod prêt à être redimensionné

Créez le namespace d'essai et un Pod nginx `souple`. Son bloc `resizePolicy`
dit, ressource par ressource, si un changement doit redémarrer le conteneur :
ici `NotRequired`, donc non, ni pour le CPU ni pour la mémoire.

```bash
kubectl create namespace essai-resize
cat <<'YAML' | kubectl apply -n essai-resize -f -
apiVersion: v1
kind: Pod
metadata:
  name: souple
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 50m
          memory: 32Mi
        limits:
          cpu: 100m
          memory: 64Mi
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: NotRequired
YAML
kubectl wait --for=condition=Ready pod/souple -n essai-resize --timeout=120s
```

```text
namespace/essai-resize created
pod/souple created
pod/souple condition met
```

```bash
kubectl get pod souple -n essai-resize -o jsonpath='{range .spec.containers[0].resizePolicy[*]}{.resourceName}: {.restartPolicy}{"\n"}{end}'
```

```text
cpu: NotRequired
memory: NotRequired
```

Notez la date de création du Pod, son nombre de redémarrages et les limites
que le noyau applique (dans le cgroup du conteneur) :

```bash
kubectl get pod souple -n essai-resize -o jsonpath='creation={.metadata.creationTimestamp} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'; kubectl exec souple -n essai-resize -- cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max
```

```text
creation=2026-11-20T05:56:18Z redemarrages=0
10000 100000
67108864
```

`10000 100000` : 10 % d'un cœur, soit `100m`. `67108864` octets, soit `64Mi`.

## 📚 Exercice 2 : la voie ordinaire est refusée

Essayez de changer la limite de CPU par un `kubectl patch` ordinaire :

```bash
kubectl patch pod souple -n essai-resize -p '{"spec":{"containers":[{"name":"web","resources":{"limits":{"cpu":"300m"}}}]}}' 2>&1 | head -1 | cut -c1-150
```

```text
The Pod "souple" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`,`spec.initContainers[*].image`,`
```

Refusé : les ressources d'un Pod ne se changent pas par la voie ordinaire, pas
plus avec `kubectl edit` ou `kubectl apply`. (`head` et `cut` raccourcissent
un message très long.)

## 📚 Exercice 3 : redimensionner par la sous-ressource resize

Le redimensionnement passe par une **sous-ressource** dédiée, `resize`.
`kubectl patch --subresource resize` la vise. Le patch nomme le conteneur
(`web`) et ses nouvelles ressources :

```bash
kubectl patch pod souple -n essai-resize --subresource resize -p '{"spec":{"containers":[{"name":"web","resources":{"requests":{"cpu":"150m","memory":"48Mi"},"limits":{"cpu":"300m","memory":"96Mi"}}}]}}'
```

```text
pod/souple patched
```

Le Pod porte deux informations : ce qui est **demandé** (dans `spec`), et ce
que le kubelet a vraiment **appliqué** (dans `status`). Elles peuvent différer
un instant :

```bash
sleep 5; kubectl get pod souple -n essai-resize -o jsonpath='demande={.spec.containers[0].resources.limits} applique={.status.containerStatuses[0].resources.limits}{"\n"}'
```

```text
demande={"cpu":"300m","memory":"96Mi"} applique={"cpu":"300m","memory":"96Mi"}
```

Les deux sont égales : le redimensionnement est fait. Relisez la date de
création, les redémarrages et le cgroup :

```bash
kubectl get pod souple -n essai-resize -o jsonpath='creation={.metadata.creationTimestamp} redemarrages={.status.containerStatuses[0].restartCount}{"\n"}'; kubectl exec souple -n essai-resize -- cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max
```

```text
creation=2026-11-20T05:56:18Z redemarrages=0
30000 100000
100663296
```

Même date de création, aucun redémarrage : c'est le même Pod, et son
conteneur n'a pas été interrompu. Le noyau applique déjà les nouvelles
limites : 30 % d'un cœur (`300m`) et `100663296` octets (`96Mi`).

## 📚 Exercice 4 : une politique qui redémarre le conteneur

Certaines applications ne voient pas un changement de mémoire tant qu'elles
ne redémarrent pas. Le Pod `strict` demande donc un redémarrage pour la
mémoire (`RestartContainer`), mais pas pour le CPU :

```bash
cat <<'YAML' | kubectl apply -n essai-resize -f -
apiVersion: v1
kind: Pod
metadata:
  name: strict
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      resources:
        requests:
          cpu: 50m
          memory: 32Mi
        limits:
          cpu: 100m
          memory: 64Mi
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: RestartContainer
YAML
kubectl wait --for=condition=Ready pod/strict -n essai-resize --timeout=120s
```

```text
pod/strict created
pod/strict condition met
```

Changez sa limite de mémoire, puis regardez le Pod 10 secondes plus tard :

```bash
kubectl patch pod strict -n essai-resize --subresource resize -p '{"spec":{"containers":[{"name":"web","resources":{"limits":{"memory":"128Mi"}}}]}}' && sleep 10; kubectl get pod strict -n essai-resize; kubectl exec strict -n essai-resize -- cat /sys/fs/cgroup/memory.max
```

```text
pod/strict patched
NAME     READY   STATUS    RESTARTS     AGE
strict   1/1     Running   1 (9s ago)   11s
134217728
```

`RESTARTS 1` : cette fois, le conteneur a redémarré, comme la politique le
demandait. Le Pod, lui, est toujours le même (`AGE 11s`), et la nouvelle
limite (`134217728` octets, soit `128Mi`) est appliquée.

## 📚 Exercice 5 : un redimensionnement impossible

Demandez pour `souple` 64 cœurs de CPU, plus que le nœud n'en a :

```bash
kubectl patch pod souple -n essai-resize --subresource resize -p '{"spec":{"containers":[{"name":"web","resources":{"requests":{"cpu":"64"},"limits":{"cpu":"64"}}}]}}'
```

```text
Error from server (Forbidden): pods "souple" is forbidden: node didn't have enough allocatable resources: cpu, requested: 64000, allocatable: 2000
```

Refusé tout de suite : le nœud n'a que 2 cœurs à donner (`2000` millièmes).
Le Pod garde son budget précédent :

```bash
kubectl get pod souple -n essai-resize -o jsonpath='demande={.spec.containers[0].resources.requests.cpu} applique={.status.containerStatuses[0].resources.requests.cpu}{"\n"}'
```

```text
demande=150m applique=150m
```

Un Pod redimensionné en place reste sur son nœud. Il ne peut grandir que dans
la place que ce nœud a encore.

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec ses Pods :

```bash
kubectl delete namespace essai-resize
```

```text
namespace "essai-resize" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-in-place-pod-vertical-scaling
dsoxlab check ckad-in-place-pod-vertical-scaling
```

```text
╭─ Résultat : ckad-in-place-pod-vertical-scaling ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                │
╰─────────────────────────────────────────────────╯
```

0 sur 3 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un autre Pod, qui tient une session à ne pas
interrompre, à redimensionner sans le recréer.

```bash
dsoxlab run ckad-in-place-pod-vertical-scaling
dsoxlab challenge ckad-in-place-pod-vertical-scaling
```
