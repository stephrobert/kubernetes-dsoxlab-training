# Initialiser un plan de contrôle avec kubeadm

La leçon montre `kubeadm init`, qui crée le plan de contrôle d'un cluster à
partir d'un fichier de configuration. Le lab a défait le cluster et la
préparation du nœud : c'est le challenge. Ce cours n'initialise donc rien. Il
se sert des commandes de kubeadm qui ne changent rien, et ajoute des cas que
la leçon ne montre pas : valider un fichier avant de s'en servir, une
configuration trop ancienne, la liste des images qu'un init tirera, et un
init à blanc.

Vous travaillez dans un répertoire d'essai, `~/essai-kubeadm`, avec un cluster
fictif `essai-atelier` et un réseau de Pods `10.250.0.0/16`. Le challenge
porte sur un autre fichier et un autre cluster : vous le ferez seul, à la fin.

Page associée : [Installer Kubernetes avec kubeadm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/kubeadm/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-initialiser-un-plan-de-controle
```

Vous êtes maintenant connecté à `k8s-cp.lab`. Il n'y a plus de cluster : votre
kubectl ne répond pas, et c'est normal.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec kubeadm v1.37.2.

## ✔️ Exercice 1 : valider une configuration avant de s'en servir

Écrivez une configuration avec une faute de frappe, `serviceSubnett`, et
faites-la valider par `kubeadm config validate`. La commande affiche aussi la
version de kubeadm :

```bash
mkdir -p ~/essai-kubeadm; kubeadm version -o short; cat > ~/essai-kubeadm/atelier.yaml <<'YAML'
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
clusterName: essai-atelier
kubernetesVersion: v1.37.2
networking:
  podSubnet: 10.250.0.0/16
  serviceSubnett: 10.96.0.0/12
YAML
kubeadm config validate --config ~/essai-kubeadm/atelier.yaml
```

```text
v1.37.2
error: error unmarshaling configuration schema.GroupVersionKind{Group:"kubeadm.k8s.io", Version:"v1beta4", Kind:"ClusterConfiguration"}: strict decoding error: unknown field "networking.serviceSubnett"
To see the stack trace of this error execute with --v=5 or higher
```

kubeadm refuse le champ inconnu et le nomme. Sans cette vérification, la faute
aurait été découverte au milieu d'un `kubeadm init`. Corrigez et validez de
nouveau :

```bash
sed -i 's/serviceSubnett/serviceSubnet/' ~/essai-kubeadm/atelier.yaml; kubeadm config validate --config ~/essai-kubeadm/atelier.yaml
```

```text
ok
```

## 🕰️ Exercice 2 : une configuration trop ancienne

Les fichiers de kubeadm ont une version d'API. Écrivez une configuration en
`v1beta3`, l'ancienne version, et validez-la :

```bash
cat > ~/essai-kubeadm/ancienne.yaml <<'YAML'
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
clusterName: essai-atelier
kubernetesVersion: v1.37.2
networking:
  podSubnet: 10.250.0.0/16
YAML
kubeadm config validate --config ~/essai-kubeadm/ancienne.yaml
```

```text
error: your configuration file uses an old API spec: "kubeadm.k8s.io/v1beta3" (kind: "ClusterConfiguration"). Please use kubeadm v1.36 instead and run 'kubeadm config migrate --old-config old-config-file --new-config new-config-file', which will write the new, similar spec using a newer API version.
To see the stack trace of this error execute with --v=5 or higher
```

kubeadm 1.37 ne lit plus `v1beta3`. Le message conseille de migrer le fichier,
mais avec kubeadm 1.36. Essayez quand même avec la version installée :

```bash
kubeadm config migrate --old-config ~/essai-kubeadm/ancienne.yaml --new-config ~/essai-kubeadm/migree.yaml; ls ~/essai-kubeadm
```

```text
error: your configuration file uses an old API spec: "kubeadm.k8s.io/v1beta3" (kind: "ClusterConfiguration"). Please use kubeadm v1.36 instead and run 'kubeadm config migrate --old-config old-config-file --new-config new-config-file', which will write the new, similar spec using a newer API version.
To see the stack trace of this error execute with --v=5 or higher
ancienne.yaml
atelier.yaml
```

Même refus, et aucun fichier `migree.yaml` n'a été écrit. Une configuration
gardée d'une ancienne installation se migre avec la version de kubeadm qui la
comprend encore, ou se réécrit en `v1beta4`.

## 📦 Exercice 3 : les images qu'un init tirera

Avant un init, surtout sur une machine qui a un accès limité à Internet,
listez les images nécessaires :

```bash
kubeadm config images list --config ~/essai-kubeadm/atelier.yaml
```

```text
registry.k8s.io/kube-apiserver:v1.37.2
registry.k8s.io/kube-controller-manager:v1.37.2
registry.k8s.io/kube-scheduler:v1.37.2
registry.k8s.io/kube-proxy:v1.37.2
registry.k8s.io/coredns/coredns:v1.14.6
registry.k8s.io/pause:3.10.2
registry.k8s.io/etcd:3.7.0-0
```

Sept images, toutes à la version demandée par le fichier pour les composants
de Kubernetes. `kubeadm config images pull` les télécharge à l'avance.

## 🧪 Exercice 4 : un init à blanc

`kubeadm init --dry-run` déroule toutes les étapes sans rien installer. Le
nœud n'étant pas préparé (c'est le challenge), les vérifications préalables
sont ignorées ici. La sortie, longue, est rangée dans un fichier, dont la
commande affiche le code et trois lignes :

```bash
sudo kubeadm init --dry-run --config ~/essai-kubeadm/atelier.yaml --ignore-preflight-errors=all > ~/essai-kubeadm/blanc.txt 2>&1; echo "init à blanc : code $?"; grep -m3 -E 'dry-run|Would|\[dryrun\]' ~/essai-kubeadm/blanc.txt
```

```text
init à blanc : code 0
W1121 03:44:44.121059 1129691 constants.go:627] Using dry-run directory /etc/kubernetes/tmp/kubeadm-init-dryrun2243946114. To override it, set the environment variable KUBEADM_INIT_DRYRUN_DIR
[preflight] Would pull the required images (like 'kubeadm config images pull')
[etcd] Would ensure that "/var/lib/etcd" directory is present
```

Chaque étape dit ce qu'elle ferait (`Would`). kubeadm écrit les fichiers qu'il
produirait dans un répertoire temporaire, sous `/etc/kubernetes/tmp`, au lieu
de leur place réelle. Cherchez-y ce que votre configuration a changé, puis
comptez les manifestes réellement posés :

```bash
grep -o -m1 -- '--cluster-cidr=[0-9./]*' ~/essai-kubeadm/blanc.txt; grep -o -m1 -- '--cluster-name=[a-z-]*' ~/essai-kubeadm/blanc.txt; sudo ls /etc/kubernetes/manifests 2>/dev/null | wc -l
```

```text
--cluster-cidr=10.250.0.0/16
--cluster-name=essai-atelier
0
```

Le réseau de Pods et le nom du cluster de votre fichier se retrouvent dans les
options des composants. Et `/etc/kubernetes/manifests` ne contient aucun
manifeste : rien n'a été installé. L'init à blanc est la façon de relire ce
qu'un fichier de configuration produira, avant de le lancer pour de bon.

## 🧹 Nettoyage

Supprimez le répertoire d'essai. Le répertoire temporaire de l'init à blanc
reste dans `/etc/kubernetes/tmp`, ce qui ne gêne pas un vrai `kubeadm init` :

```bash
rm -rf ~/essai-kubeadm
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-initialiser-un-plan-de-controle
dsoxlab check cka-initialiser-un-plan-de-controle
```

```text
╭─ Résultat : cka-initialiser-un-plan-de-controle ─╮
│  0 / 100 pts                                     │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests                 │
╰──────────────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : préparer le nœud, initialiser le cluster à partir de
votre fichier, et le rendre utilisable.

```bash
dsoxlab run cka-initialiser-un-plan-de-controle
dsoxlab challenge cka-initialiser-un-plan-de-controle
```
