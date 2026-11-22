# Donner une seconde interface à un Pod

La leçon installe Multus à côté de Cilium et attache un second réseau macvlan
à des Pods par une NetworkAttachmentDefinition. Ce cours regarde ce que
Multus fait à votre place : il appelle un **plugin CNI**, un simple
exécutable du nœud, avec une configuration JSON. Vous allez appeler ce plugin
vous-même, sans Multus et sans Pod, pour voir ce qu'il crée, ce qu'il répond
quand il échoue, et ce qui distingue macvlan d'ipvlan.

Vous travaillez dans des espaces réseau d'essai, `essai-a`, `essai-b` et
`essai-c`, sur le réseau `192.168.200.0/24`. Le challenge porte sur Multus,
sur d'autres Pods et un autre réseau : vous le ferez seul, à la fin.

Page associée : [Donner plusieurs interfaces à un Pod avec Multus](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/pods-multi-interfaces/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-attacher-une-seconde-interface
```

Vous êtes maintenant connecté à `net-cp.lab`, le plan de contrôle du cluster
Cilium. Les exercices se passent sur les deux workers, `net-w1.lab` et
`net-w2.lab`, où les plugins `macvlan`, `ipvlan` et `static` sont installés
dans `/opt/cni/bin`.

Les sorties montrées dans ce cours ont été relevées sur ces machines le
22 novembre 2026 (Kubernetes v1.37.2, Cilium 1.20.5, plugins CNI de
référence).

## 🔌 Exercice 1 : appeler un plugin CNI à la main

Un plugin CNI lit sa configuration sur son entrée standard et reçoit le reste
par des variables d'environnement : l'action (`CNI_COMMAND`), l'espace réseau
à équiper (`CNI_NETNS`) et le nom de l'interface à créer (`CNI_IFNAME`). C'est
exactement ce que fait Multus pour chaque réseau d'un Pod. Sur `net-w1.lab`,
créez un espace réseau d'essai, la configuration d'un réseau macvlan à adresse
fixe, puis appelez le plugin avec l'action `ADD` :

```bash
ssh net-w1.lab
sudo ip netns add essai-a; mkdir -p /tmp/essai-cni
cat > /tmp/essai-cni/essai-a.json <<'JSON'
{
  "cniVersion": "1.0.0",
  "name": "essai-stockage",
  "type": "macvlan",
  "master": "enp1s0",
  "mode": "bridge",
  "ipam": {"type": "static", "addresses": [{"address": "192.168.200.21/24"}]}
}
JSON
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-a CNI_NETNS=/var/run/netns/essai-a CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-a.json
```

```text
{
    "cniVersion": "1.0.0",
    "interfaces": [
        {
            "mac": "7e:18:cf:5e:be:0b",
            "name": "net1",
            "sandbox": "/var/run/netns/essai-a"
        }
    ],
    "ips": [
        {
            "address": "192.168.200.21/24",
            "interface": 0
        }
    ]
}
```

Le plugin répond en JSON : l'interface créée, l'espace réseau qui la porte et
son adresse. C'est cette réponse que Multus recopie dans l'annotation
`k8s.v1.cni.cncf.io/network-status` d'un Pod. Regardez l'interface créée, et
celle du nœud sur laquelle elle s'appuie :

```bash
sudo ip netns exec essai-a ip -br addr show net1
sudo ip netns exec essai-a ip -br link show net1
ip -br link show enp1s0
```

```text
net1@if2         UP             192.168.200.21/24 fe80::7c18:cfff:fe5e:be0b/64
net1@if2         UP             7e:18:cf:5e:be:0b <BROADCAST,MULTICAST,UP,LOWER_UP>
enp1s0           UP             52:54:8b:d2:00:14 <BROADCAST,MULTICAST,UP,LOWER_UP>
```

`net1` porte l'adresse demandée et une **adresse MAC à elle**,
`7e:18:cf:5e:be:0b`, différente de celle de `enp1s0`. C'est le principe de
macvlan : chaque interface ajoutée se présente sur le réseau comme une
machine de plus.

## 📡 Exercice 2 : un échange d'un nœud à l'autre

Faites la même chose sur `net-w2.lab`, dans l'espace `essai-b`, avec
l'adresse `192.168.200.22/24`. Quittez `net-w1` (`exit`), puis :

```bash
ssh net-w2.lab
sudo ip netns add essai-b; mkdir -p /tmp/essai-cni
cat > /tmp/essai-cni/essai-b.json <<'JSON'
{
  "cniVersion": "1.0.0",
  "name": "essai-stockage",
  "type": "macvlan",
  "master": "enp1s0",
  "mode": "bridge",
  "ipam": {"type": "static", "addresses": [{"address": "192.168.200.22/24"}]}
}
JSON
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-b CNI_NETNS=/var/run/netns/essai-b CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-b.json | grep -E '"(mac|address)"'
exit
```

```text
            "mac": "9e:1e:12:ed:3a:ef",
            "address": "192.168.200.22/24",
```

De retour sur `net-cp`, lancez un ping depuis `essai-a`, sur `net-w1`, vers
`essai-b`, sur `net-w2` :

```bash
ssh net-w1.lab 'sudo ip netns exec essai-a ping -c 3 192.168.200.22'
```

```text
PING 192.168.200.22 (192.168.200.22) 56(84) bytes of data.
64 bytes from 192.168.200.22: icmp_seq=1 ttl=64 time=0.359 ms
64 bytes from 192.168.200.22: icmp_seq=2 ttl=64 time=0.399 ms
64 bytes from 192.168.200.22: icmp_seq=3 ttl=64 time=0.636 ms

--- 192.168.200.22 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2037ms
rtt min/avg/max/mdev = 0.359/0.464/0.636/0.122 ms
```

Les deux interfaces se joignent directement, à moins d'une milliseconde, sans
passer par Cilium ni par un Service : le paquet sort par `enp1s0` comme celui
d'une machine ordinaire du réseau `10.10.50.0/24`. `ttl=64` le confirme :
aucun routeur ne s'est trouvé entre les deux.

## 🚫 Exercice 3 : la réponse d'un plugin qui échoue

Quand un Pod reste en `ContainerCreating` derrière Multus, l'erreur vient
souvent du plugin. Provoquez-en une : appelez macvlan avec une interface
maître qui n'existe pas, `enp9s0`. Sur `net-w1`, dans un espace jetable :

```bash
ssh net-w1.lab
sudo ip netns add essai-x
sed -e 's/enp1s0/enp9s0/' -e 's/200.21/200.29/' /tmp/essai-cni/essai-a.json > /tmp/essai-cni/essai-x.json
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-x CNI_NETNS=/var/run/netns/essai-x CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-x.json; echo "code=$?"
sudo ip netns del essai-x
```

```text
{
    "code": 999,
    "msg": "Link not found"
}code=1
```

Le plugin sort en 1 et rend une erreur en JSON, avec un message court : `Link
not found`. Il ne nomme pas l'interface fautive. Derrière Multus, c'est ce
message qui remonte dans les événements du Pod (`kubectl describe pod`) :
quand vous le lisez, comparez le champ `master` de la NetworkAttachmentDefinition
avec `ip -br link` sur le nœud qui porte le Pod.

## 🧱 Exercice 4 : macvlan et ipvlan sur la même interface

ipvlan est l'autre façon de partager une interface du nœud. Essayez de
l'ajouter sur `enp1s0`, dans un nouvel espace `essai-c`, alors que `essai-a`
y a déjà son macvlan. La configuration change de type, et le mode vaut `l2` :

```bash
sudo ip netns add essai-c
sed -e 's/"macvlan"/"ipvlan"/' -e 's/"bridge"/"l2"/' -e 's/200.21/200.23/' /tmp/essai-cni/essai-a.json > /tmp/essai-cni/essai-c.json
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-c CNI_NETNS=/var/run/netns/essai-c CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/ipvlan < /tmp/essai-cni/essai-c.json; echo "code=$?"
```

```text
{
    "code": 999,
    "msg": "failed to create ipvlan: device or resource busy"
}code=1
```

`device or resource busy` : le noyau refuse. Une interface qui porte déjà un
macvlan ne peut pas porter un ipvlan, et l'inverse non plus. Sur un cluster,
deux NetworkAttachmentDefinition, une macvlan et une ipvlan, sur le même
`master` donnent cette erreur au premier Pod qui demande la seconde.

## 🔁 Exercice 5 : rendre l'interface, puis comparer avec ipvlan

L'action `DEL` est celle que reçoit le plugin quand un Pod est supprimé.
Rendez l'interface de `essai-a` avec la même configuration, puis relancez
l'ipvlan :

```bash
sudo CNI_COMMAND=DEL CNI_CONTAINERID=essai-a CNI_NETNS=/var/run/netns/essai-a CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-a.json; echo "code=$?"
sudo ip netns exec essai-a ip -br link
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-c CNI_NETNS=/var/run/netns/essai-c CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/ipvlan < /tmp/essai-cni/essai-c.json > /dev/null; echo "code=$?"
sudo ip netns exec essai-c ip -br link show net1
ip -br link show enp1s0
```

```text
code=0
lo               DOWN           00:00:00:00:00:00 <LOOPBACK>
code=0
net1@if2         UNKNOWN        52:54:8b:d2:00:14 <BROADCAST,MULTICAST,UP,LOWER_UP>
enp1s0           UP             52:54:8b:d2:00:14 <BROADCAST,MULTICAST,UP,LOWER_UP>
```

Après `DEL`, il ne reste dans `essai-a` que l'interface `lo` : `net1` a
disparu, et l'ipvlan passe. Son `net1` porte **la même MAC** que `enp1s0`.
Vérifiez ce que voit `net-w2` après un ping :

```bash
sudo ip netns exec essai-c ping -c 2 192.168.200.22 | tail -2
exit
ssh net-w2.lab 'sudo ip netns exec essai-b ip neigh show 192.168.200.23; sudo ip netns exec essai-b ip neigh show 192.168.200.21'
```

```text
2 packets transmitted, 2 received, 0% packet loss, time 1023ms
rtt min/avg/max/mdev = 0.341/0.446/0.552/0.105 ms
192.168.200.23 dev net1 lladdr 52:54:8b:d2:00:14 DELAY
192.168.200.21 dev net1 lladdr 7e:18:cf:5e:be:0b DELAY
```

Pour `essai-b`, l'adresse ipvlan `.23` a la MAC de la carte de `net-w1`,
alors que l'adresse macvlan `.21` avait la sienne. C'est la différence qui
décide du choix : sur un réseau qui limite le nombre de MAC par port (un
commutateur filtré, un réseau de cloud), macvlan échoue là où ipvlan passe.

## 🧹 Nettoyage

Rendez les deux interfaces encore attachées, puis supprimez les espaces
d'essai et les fichiers de configuration, sur chaque worker :

```bash
ssh net-w1.lab 'sudo CNI_COMMAND=DEL CNI_CONTAINERID=essai-c CNI_NETNS=/var/run/netns/essai-c CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/ipvlan < /tmp/essai-cni/essai-c.json; sudo ip netns del essai-a; sudo ip netns del essai-c; rm -rf /tmp/essai-cni'
ssh net-w2.lab 'sudo CNI_COMMAND=DEL CNI_CONTAINERID=essai-b CNI_NETNS=/var/run/netns/essai-b CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-b.json; sudo ip netns del essai-b; rm -rf /tmp/essai-cni'
for n in net-w1.lab net-w2.lab; do ssh $n 'ip netns list | grep -c essai'; done
```

```text
0
0
```

Aucun espace d'essai ne reste sur les deux workers. Quittez ensuite la
machine et remettez le lab à zéro. `dsoxlab reset` rejoue le nettoyage puis
la préparation du lab : vous retrouvez exactement l'état de départ du
challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-attacher-une-seconde-interface
dsoxlab check k8s-attacher-une-seconde-interface
```

```text
╭─ Résultat : k8s-attacher-une-seconde-interface ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests                │
╰─────────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : laisser Cilium partager la configuration CNI,
installer Multus, et donner à deux Pods une seconde interface sur un réseau
de stockage, d'un nœud à l'autre.

```bash
dsoxlab run k8s-attacher-une-seconde-interface
dsoxlab challenge k8s-attacher-une-seconde-interface
```
