# Retirer d'un worker ce qui écoute sans servir Kubernetes

La leçon montre comment durcir les nœuds d'un cluster. Ce cours ajoute des
cas qu'elle ne montre pas : remonter d'un port ouvert à son processus, à son
paquet et à son service systemd, reconnaître un service lancé à la main qui
ne reviendrait pas au redémarrage, et la différence entre désactiver et
masquer un service.

Vous travaillez sur `k8s-w1.lab`, par `ssh` depuis le control plane. Le
challenge porte sur un autre nœud : vous le ferez seul, à la fin.

Page associée : [Durcir les nœuds d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-reduire-la-surface-du-noeud
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà, et `ssh` atteint les
workers.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 👂 Exercice 1 : qui écoute, et pour quel paquet

`ss -tlnp` liste les ports TCP ouverts en écoute, avec le processus derrière
chacun. Sur `k8s-w1.lab` :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo ss -tlnpH | awk "{print \$4, \$6}" | sort -u' | head -8
```

```text
*:10250 users:(("kubelet",pid=23439,fd=26))
*:10256 users:(("kube-proxy",pid=22343,fd=11))
0.0.0.0:179 users:(("bird",pid=20160,fd=7))
0.0.0.0:22 users:(("sshd",pid=751,fd=3),("systemd",pid=1,fd=176))
127.0.0.1:10248 users:(("kubelet",pid=23439,fd=17))
127.0.0.1:10249 users:(("kube-proxy",pid=22343,fd=13))
127.0.0.1:38785 users:(("containerd",pid=62124,fd=78))
127.0.0.1:9099 users:(("calico-node",pid=19964,fd=4))
```

Chaque ligne a son explication : le kubelet (10250, 10248), kube-proxy (10256,
10249), `bird` de Calico (179), sshd (22), containerd et calico-node en local.
Un port qui ne s'explique pas ainsi est suspect. Pour remonter d'un port à
son origine, partez de son processus :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'P=$(sudo ss -tlnpH "sport = :22" | grep -o "pid=[0-9]*" | head -1 | cut -d= -f2); B=$(sudo readlink /proc/$P/exe); echo "pid $P -> $B"; dpkg -S $B; systemctl status $P --no-pager | head -1'
```

```text
pid 751 -> /usr/sbin/sshd
openssh-server: /usr/sbin/sshd
● ssh.service - OpenBSD Secure Shell server
```

Le processus du port 22 est `/usr/sbin/sshd`, fourni par le paquet
`openssh-server`, et lancé par le service `ssh.service`. Pour retirer un
service pour de bon, il faut savoir lequel de ces trois niveaux agir.

## 🪤 Exercice 2 : un service lancé à la main

Lancez un petit serveur web comme service temporaire :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemd-run --unit essai-ecoute python3 -m http.server 8099 >/dev/null 2>&1; sleep 2; sudo ss -tlnp "sport = :8099" | tail -1; systemctl is-enabled essai-ecoute 2>&1'
```

```text
LISTEN 0      5            0.0.0.0:8099      0.0.0.0:*    users:(("python3",pid=63228,fd=3))
transient
```

Le port 8099 écoute, mais le service est `transient` : il a été lancé à la
main et aucun fichier ne le décrit. Il ne reviendra pas au redémarrage, et
`systemctl disable` n'a rien à désactiver. Il suffit de l'arrêter :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemctl stop essai-ecoute; sudo ss -tln "sport = :8099" | tail -n +2 | wc -l'
```

```text
0
```

Plus rien n'écoute sur 8099.

## 🚫 Exercice 3 : désactiver ou masquer

Désactivez le timer `apt-daily.timer`, puis essayez de le démarrer :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'systemctl is-enabled apt-daily.timer; sudo systemctl disable apt-daily.timer 2>&1 | tail -1; systemctl is-enabled apt-daily.timer; sudo systemctl start apt-daily.timer; systemctl is-active apt-daily.timer'
```

```text
enabled
Removed "/etc/systemd/system/timers.target.wants/apt-daily.timer".
disabled
active
```

Désactivé, il ne démarre plus **tout seul** au démarrage du nœud, mais il
démarre encore à la demande. Masquez-le maintenant :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemctl mask apt-daily.timer >/dev/null 2>&1; ls -l /etc/systemd/system/apt-daily.timer; sudo systemctl start apt-daily.timer; echo "start : code $?"; systemctl is-enabled apt-daily.timer'
```

```text
lrwxrwxrwx 1 root root 9 Nov 21 11:32 /etc/systemd/system/apt-daily.timer -> /dev/null
Failed to start apt-daily.timer: Unit apt-daily.timer is masked.
start : code 1
masked
```

Masqué, il est lié à `/dev/null` : plus personne ne peut le démarrer, ni le
nœud ni un autre service qui en dépendrait. Masquer est le moyen sûr de
garder éteint un service qu'on ne peut pas désinstaller.

## 🧹 Nettoyage

Démasquez et réactivez le timer, puis vérifiez que le service temporaire a
disparu :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemctl unmask apt-daily.timer >/dev/null 2>&1; sudo systemctl enable --now apt-daily.timer >/dev/null 2>&1; systemctl is-enabled apt-daily.timer; systemctl is-active essai-ecoute 2>&1'
```

```text
enabled
inactive
```

Le timer est de nouveau `enabled`. `essai-ecoute` est `inactive` : arrêté, un
service temporaire n'existe plus.

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-reduire-la-surface-du-noeud
dsoxlab check cks-reduire-la-surface-du-noeud
```

```text
╭─ Résultat : cks-reduire-la-surface-du-noeud ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un worker où écoutent des services qui ne servent
pas Kubernetes, à retirer durablement sans casser le nœud.

```bash
dsoxlab run cks-reduire-la-surface-du-noeud
dsoxlab challenge cks-reduire-la-surface-du-noeud
```
