# Préparer une installation de Cilium sans kube-proxy

La leçon installe un cluster dont Cilium remplace kube-proxy : init sans la
phase kube-proxy, jonction des workers, `helm install`, puis trois preuves.
Monter ce cluster est le challenge du lab. Ce cours ne monte donc rien. Il
prépare les choix qui se font **avant** l'installation et ne se rattrapent
plus après : vérifier qu'un init saute vraiment kube-proxy, choisir un pool de
Pods qui ne recoupe rien, lire ce que le chart va écrire, et voir ce qui se
passe quand on oublie `k8sServiceHost`.

Vous travaillez dans un répertoire d'essai, `~/essai-cilium`, avec un cluster
fictif `essai-reseau` et un pool de Pods `10.250.0.0/16`. Le challenge porte
sur un autre pool et sur un vrai cluster : vous le ferez seul, à la fin.

Page associée : [Installer Cilium sans kube-proxy et choisir son IPAM](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cilium/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-installer-cilium-sans-kube-proxy
```

Vous êtes maintenant connecté à `net-cp.lab`, le futur plan de contrôle. Les
trois nœuds `net-*` sont prêts (kubeadm, kubelet et kubectl 1.37, Helm 4.3.2),
mais aucun cluster n'existe. Créez le répertoire d'essai :

```bash
mkdir -p ~/essai-cilium && cd ~/essai-cilium
```

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026 (kubeadm v1.37.2, Helm v4.3.2, noyau 6.8).

## 🧪 Exercice 1 : vérifier qu'un init saute kube-proxy, sans rien créer

`kubeadm init --dry-run` déroule toutes les phases d'un init, mais écrit ses
fichiers dans un répertoire temporaire et ne démarre rien. C'est le moyen de
vérifier une commande avant de la lancer pour de bon. Écrivez une
configuration d'essai, puis faites deux inits à blanc, avec et sans
`--skip-phases=addon/kube-proxy` :

```bash
cat > essai-init.yaml <<'YAML'
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
clusterName: essai-reseau
networking:
  podSubnet: 10.250.0.0/16
YAML
sudo kubeadm init --config essai-init.yaml --dry-run > avec.txt 2>&1
sudo kubeadm init --config essai-init.yaml --dry-run --skip-phases=addon/kube-proxy > sans.txt 2>&1
grep '\[addons\]' avec.txt sans.txt
grep -c kube-proxy avec.txt sans.txt
```

```text
avec.txt:[addons] Applied essential addon: CoreDNS
avec.txt:[addons] Applied essential addon: kube-proxy
sans.txt:[addons] Applied essential addon: CoreDNS
avec.txt:23
sans.txt:0
```

Sans l'option, l'init installerait l'addon `kube-proxy`, et son nom revient
23 fois dans la sortie, avec les objets que l'addon créerait (un compte de
service, un Role, un RoleBinding…). Avec l'option, il
n'apparaît plus une seule fois. Vous savez avant de lancer l'init que le
cluster naîtra sans kube-proxy.

## 🗺️ Exercice 2 : choisir un pool de Pods qui ne recoupe rien

La leçon dit de choisir un pool qui ne recoupe ni le réseau des nœuds ni celui
des Services. Encore faut-il connaître ces deux réseaux. Le réseau des
Services est celui que kubeadm pose par défaut, et le réseau des nœuds se lit
sur l'interface de la machine :

```bash
kubeadm config print init-defaults | grep serviceSubnet
ip -4 -o addr show enp1s0 | awk '{print $4}'
```

```text
  serviceSubnet: 10.96.0.0/12
10.10.50.14/24
```

Les Services prennent leurs adresses dans `10.96.0.0/12` (de `10.96.0.0` à
`10.111.255.255`), et les nœuds sont dans `10.10.50.0/24`. Testez trois pools
candidats avec le module `ipaddress` de Python, qui sait dire si deux réseaux
se recoupent :

```bash
python3 -c '
import ipaddress as ip
noeuds, services = ip.ip_network("10.10.50.0/24"), ip.ip_network("10.96.0.0/12")
for pool in ("10.0.0.0/8", "10.100.0.0/16", "10.250.0.0/16"):
    p = ip.ip_network(pool)
    print(pool, "noeuds:", p.overlaps(noeuds), "services:", p.overlaps(services))
'
```

```text
10.0.0.0/8 noeuds: True services: True
10.100.0.0/16 noeuds: False services: True
10.250.0.0/16 noeuds: False services: False
```

Le pool par défaut de Cilium, `10.0.0.0/8`, recoupe les deux. `10.100.0.0/16`
a l'air sûr, mais il tombe dans le réseau des Services : un Pod pourrait
recevoir l'adresse d'un Service. Seul `10.250.0.0/16` ne recoupe rien.

## 📄 Exercice 3 : lire ce que le chart va écrire

`helm template` produit les manifestes du chart sans rien envoyer au cluster.
Il n'a même pas besoin d'un cluster. Déclarez le dépôt de charts, puis rendez
le chart avec le pool d'essai et des blocs `/26` par nœud :

```bash
helm repo add cilium https://helm.cilium.io
helm template essai cilium/cilium --version 1.20.5 --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=10.10.50.14 --set k8sServicePort=6443 \
  --set ipam.mode=cluster-pool \
  --set 'ipam.operator.clusterPoolIPv4PodCIDRList={10.250.0.0/16}' \
  --set ipam.operator.clusterPoolIPv4MaskSize=26 > rendu.yaml
grep -E '^  (kube-proxy-replacement|ipam|cluster-pool-ipv4-cidr|cluster-pool-ipv4-mask-size):' rendu.yaml
```

```text
"cilium" has been added to your repositories
  kube-proxy-replacement: "true"
  ipam: "cluster-pool"
  cluster-pool-ipv4-cidr: "10.250.0.0/16"
  cluster-pool-ipv4-mask-size: "26"
```

Ces quatre lignes viennent du ConfigMap `cilium-config`, celui que l'agent et
l'opérateur lisent au démarrage. Les noms des valeurs Helm y deviennent des
clés en minuscules avec des tirets : c'est sous ces noms que vous les
retrouverez sur un cluster installé.

## 🔢 Exercice 4 : un bloc par nœud assez grand

Le masque par nœud ne se change plus après l'installation. Calculez ce que
donne le `/26` de l'exercice précédent, puis comparez avec le nombre de Pods
qu'un kubelet accepte par défaut :

```bash
python3 -c 'print("/16 en /26 :", 2**(26-16), "noeuds,", 2**(32-26)-2, "adresses par noeud")'
kubelet --help 2>/dev/null | grep -o -- '--max-pods int32 .*(default 110)' | tr -s ' '
```

```text
/16 en /26 : 1024 noeuds, 62 adresses par noeud
--max-pods int32 Number of Pods that can run on this Kubelet. (default 110)
```

Un `/26` donne 62 adresses par nœud, alors qu'un kubelet accepte 110 Pods par
défaut. Sur un nœud chargé, le 63e Pod ne recevrait pas d'adresse alors que le
kubelet l'accepte encore. Avec un `/24` (254 adresses), c'est le kubelet qui
pose la limite. Le `/26` ne convient que si vous abaissez aussi `maxPods`.

## 🔌 Exercice 5 : ce que change `k8sServiceHost`

Sans kube-proxy, l'agent Cilium ne peut pas joindre l'API server par le
Service `kubernetes`, puisque personne ne le sert encore. Rendez le chart une
seconde fois en oubliant `k8sServiceHost` et `k8sServicePort`, et comptez les
conteneurs qui reçoivent l'adresse de l'API server :

```bash
helm template essai cilium/cilium --version 1.20.5 --namespace kube-system \
  --set kubeProxyReplacement=true > oubli.yaml
grep -c 'name: KUBERNETES_SERVICE_HOST$' rendu.yaml oubli.yaml
grep -m1 -A1 'name: KUBERNETES_SERVICE_HOST$' rendu.yaml
```

```text
rendu.yaml:5
oubli.yaml:0
        - name: KUBERNETES_SERVICE_HOST
          value: "10.10.50.14"
```

Avec la valeur, cinq conteneurs (l'agent et deux de ses conteneurs
d'initialisation, l'opérateur, le proxy Envoy) reçoivent la variable `KUBERNETES_SERVICE_HOST`, qui remplace
l'adresse du Service `kubernetes`. Sans elle, Helm rend le chart sans erreur,
et la variable n'existe plus nulle part : rien ne vous prévient avant
l'installation. L'agent chercherait alors l'API server par une adresse de
Service que personne ne sert.

## 🧹 Nettoyage

Supprimez le répertoire d'essai, les fichiers temporaires des inits à blanc et
le dépôt de charts déclaré à l'exercice 3 :

```bash
cd ~ && rm -rf ~/essai-cilium && sudo rm -rf /etc/kubernetes/tmp
helm repo remove cilium
sudo ls /etc/kubernetes
```

```text
"cilium" has been removed from your repositories
manifests
pki
```

Il ne reste dans `/etc/kubernetes` que les deux répertoires vides de départ.
Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-installer-cilium-sans-kube-proxy
dsoxlab check k8s-installer-cilium-sans-kube-proxy
```

```text
╭─ Résultat : k8s-installer-cilium-sans-kube-proxy ─╮
│  0 / 100 pts                                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests                  │
╰───────────────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : monter le cluster sur les trois nœuds, sans
kube-proxy, avec Cilium à sa place et le pool d'adresses choisi par l'équipe,
puis prouver qu'un Service est servi par Cilium.

```bash
dsoxlab run k8s-installer-cilium-sans-kube-proxy
dsoxlab challenge k8s-installer-cilium-sans-kube-proxy
```
