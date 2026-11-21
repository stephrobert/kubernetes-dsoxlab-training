# Poser un Pod statique sur un worker, sans passer par l'API

La leçon montre les Pods statiques : le kubelet les lance à partir de fichiers
déposés sur le nœud, sans passer par l'API, et l'API n'en voit qu'un reflet,
le Pod miroir. Ce cours dépose ses Pods statiques sur le control plane, et
ajoute des cas que la leçon ne montre pas : un miroir supprimé qui revient,
un manifeste modifié qui recrée le Pod, un namespace qui n'existe pas, et un
Pod statique qui voudrait monter une ConfigMap.

Vous travaillez avec des manifestes d'essai : `sentinelle-statique`,
`essai-statique-absent` et `lecteur-config`. Le challenge porte sur le worker
et un autre Pod : vous le ferez seul, à la fin.

Page associée : [Dépanner un cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-static-pod
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le répertoire des
Pods statiques appartient à root : les écritures passent par `sudo`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🪞 Exercice 1 : un Pod statique, et son miroir

Le kubelet lit l'emplacement de ses Pods statiques dans sa configuration
(`staticPodPath`). Déposez-y un Pod, puis cherchez-le dans l'API :

```bash
echo "répertoire surveillé : /etc/kubernetes/manifests"; cat <<YAML | sudo tee /etc/kubernetes/manifests/sentinelle-statique.yaml >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: sentinelle-statique
  namespace: default
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo version 1; sleep 3600"]

YAML
sleep 15; kubectl get pods -A | grep sentinelle
```

```text
répertoire surveillé : /etc/kubernetes/manifests
default           sentinelle-statique-k8s-cp.lab             1/1     Running   0             15s
```

Le Pod apparaît dans l'API sous le nom `sentinelle-statique-k8s-cp.lab` : le
nom du manifeste suivi du nom du nœud. C'est le miroir. Supprimez-le :

```bash
kubectl delete pod sentinelle-statique-k8s-cp.lab -n default; sleep 10; kubectl get pods -A | grep sentinelle
```

```text
pod "sentinelle-statique-k8s-cp.lab" deleted from default namespace
default           sentinelle-statique-k8s-cp.lab             1/1     Running   0             10s
```

Il revient aussitôt (10 secondes d'âge). Le Pod réel tourne sur le nœud, et
le kubelet recrée son miroir dans l'API. Pour supprimer un Pod statique, il
faut retirer son fichier, pas son miroir.

## ✏️ Exercice 2 : modifier le manifeste recrée le Pod

Notez le conteneur du Pod, modifiez le manifeste sur le nœud, attendez qu'un
nouveau conteneur apparaisse, puis lisez les journaux :

```bash
C1=$(sudo crictl ps --name c -q --label io.kubernetes.pod.name=sentinelle-statique-k8s-cp.lab); echo "conteneur avant : ${C1:0:13}"; sudo sed -i 's/version 1/version 2/' /etc/kubernetes/manifests/sentinelle-statique.yaml; debut=$(date +%s); C2=; until [ -n "$C2" ] && [ "$C2" != "$C1" ]; do sleep 2; C2=$(sudo crictl ps --name c -q --label io.kubernetes.pod.name=sentinelle-statique-k8s-cp.lab); done; echo "recréé en $(( $(date +%s) - debut )) s"; sleep 3; echo "conteneur après : ${C2:0:13}"; kubectl logs sentinelle-statique-k8s-cp.lab -n default
```

```text
conteneur avant : 5f9f58bcda249
recréé en 39 s
conteneur après : 5a409db223569
version 2
```

Un nouveau conteneur, qui affiche `version 2`. Le kubelet a vu le fichier
changer, arrêté l'ancien Pod et lancé le nouveau. Les 41 secondes viennent de
l'arrêt : `sleep` ne réagit pas au signal d'arrêt, et le kubelet attend les
30 secondes du délai de grâce avant de le tuer.

## 🚫 Exercice 3 : un namespace qui n'existe pas

Déposez un Pod statique dans un namespace que personne n'a créé, puis
cherchez-le dans l'API et sur le nœud :

```bash
cat <<YAML | sudo tee /etc/kubernetes/manifests/essai-statique-absent.yaml >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: essai-statique-absent
  namespace: essai-inexistant
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]

YAML
sleep 20; kubectl get pods -A | grep essai-statique-absent; echo "API : code $?"; sudo crictl pods --name essai-statique-absent
```

```text
API : code 1
POD ID              CREATED             STATE               NAME                NAMESPACE           ATTEMPT             RUNTIME
```

Rien dans l'API, rien sur le nœud. Le journal du kubelet dit pourquoi :

```bash
sudo journalctl -u kubelet --since '-1 min' --no-pager | grep 'essai-statique-absent' | grep -m1 'failed to setup network' | cut -c1-200
```

```text
Nov 21 06:17:14 k8s-cp.lab kubelet[1147438]: E1121 06:17:14.716005 1147438 kuberuntime_sandbox.go:74] "Failed to create sandbox for pod" err="rpc error: code = Unknown desc = failed to setup network f
```

Le kubelet a bien essayé de créer le Pod, mais le CNI (Calico) n'a pas pu
monter son réseau, faute de namespace. Le Pod n'existe donc nulle part, et
seul le journal du kubelet le dit : pour un Pod statique absent de l'API,
c'est là qu'il faut regarder.

## 📄 Exercice 4 : un Pod statique ne peut pas lire une ConfigMap

Déposez un Pod statique qui monte une ConfigMap :

```bash
cat <<YAML | sudo tee /etc/kubernetes/manifests/lecteur-config.yaml >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: lecteur-config
  namespace: default
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts: [{name: v, mountPath: /conf}]
  volumes:
    - {name: v, configMap: {name: kube-root-ca.crt}}
YAML
sleep 20; kubectl get pods -A | grep lecteur-config; echo "API : code $?"; sudo journalctl -u kubelet --since '-1 min' --no-pager | grep -m1 -i 'lecteur-config' | grep -o 'static pods may not.*' | cut -c1-160
```

```text
API : code 1
static pods may not reference configmaps"
```

Absent de l'API, et le kubelet refuse le fichier : `static pods may not
reference configmaps`. Un Pod statique ne dépend pas de l'API, il ne peut
donc pas lire ce qui n'existe que dans l'API : ni ConfigMap, ni Secret, ni
ServiceAccount. Sa configuration vient du nœud, par un volume `hostPath`.

## 🧹 Nettoyage

Retirez les trois manifestes d'essai, attendez que le kubelet arrête les
Pods, et vérifiez qu'il n'en reste aucun dans l'API :

```bash
sudo rm -f /etc/kubernetes/manifests/sentinelle-statique.yaml /etc/kubernetes/manifests/essai-statique-absent.yaml /etc/kubernetes/manifests/lecteur-config.yaml; sleep 40; kubectl get pods -A | grep -c -E 'sentinelle|lecteur-config'
```

```text
0
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-static-pod
dsoxlab check cka-static-pod
```

```text
╭──── Résultat : cka-static-pod ────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Pod statique à poser sur le worker, dans le
répertoire que son kubelet surveille.

```bash
dsoxlab run cka-static-pod
dsoxlab challenge cka-static-pod
```
