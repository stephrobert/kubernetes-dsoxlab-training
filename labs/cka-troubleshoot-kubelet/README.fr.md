# Réparer un kubelet qui refuse de démarrer

La leçon montre comment dépanner un kubelet qui ne démarre plus. Dans ce lab,
celui du worker est en panne : c'est le challenge. Ce cours travaille sur le
kubelet du control plane, et ajoute des cas que la leçon ne montre pas : les
trois sources de sa configuration, la configuration qu'il applique
vraiment, lue par l'API, un réglage changé puis rendu, et son journal filtré
par priorité.

Page associée : [Dépanner un nœud Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/depanner-un-noeud-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-troubleshoot-kubelet
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Les fichiers du
kubelet appartiennent à root : les commandes utilisent `sudo`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 📂 Exercice 1 : d'où le kubelet tient sa configuration

Le service systemd du kubelet se compose de plusieurs fichiers. Affichez-les,
en ne gardant que les lignes utiles :

```bash
systemctl cat kubelet | grep -E '^# /|ExecStart=/|EnvironmentFile' | head -6
```

```text
# /usr/lib/systemd/system/kubelet.service
ExecStart=/usr/bin/kubelet
# /usr/lib/systemd/system/kubelet.service.d/10-kubeadm.conf
EnvironmentFile=-/var/lib/kubelet/kubeadm-flags.env
EnvironmentFile=-/etc/default/kubelet
ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_CONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS
```

Le service de base, complété par `10-kubeadm.conf`, qui ajoute deux fichiers
de variables et la vraie ligne de démarrage. Lisez le premier fichier de
variables, puis quelques réglages du fichier de configuration du kubelet :

```bash
sudo cat /var/lib/kubelet/kubeadm-flags.env; sudo grep -E '^(clusterDNS|clusterDomain|maxPods|cgroupDriver)' -A1 /var/lib/kubelet/config.yaml | head -6
```

```text
KUBELET_KUBEADM_ARGS=""
cgroupDriver: systemd
clusterDNS:
- 10.96.0.10
clusterDomain: cluster.local
containerRuntimeEndpoint: unix:///var/run/containerd/containerd.sock
```

Trois sources donc : la ligne de démarrage du service, les variables
(`kubeadm-flags.env`, vide ici), et le fichier `/var/lib/kubelet/config.yaml`.
Une panne de démarrage peut venir de chacune : il faut les lire toutes les
trois.

## 🔎 Exercice 2 : la configuration vivante, lue par l'API

Le kubelet publie la configuration qu'il applique, et l'API server sait la
relayer (`/proxy/configz`) :

```bash
kubectl get --raw /api/v1/nodes/k8s-cp.lab/proxy/configz | python3 -c 'import json,sys; c=json.load(sys.stdin)["kubeletconfig"]; print("maxPods", c["maxPods"], "| clusterDNS", c["clusterDNS"], "| staticPodPath", c["staticPodPath"])'
```

```text
maxPods 110 | clusterDNS ['10.96.0.10'] | staticPodPath /etc/kubernetes/manifests
```

C'est la configuration en service, pas celle du fichier. Les deux diffèrent
quand le fichier a été modifié sans redémarrer le kubelet, ou qu'une option
de la ligne de démarrage l'emporte.

## 🎚️ Exercice 3 : changer un réglage, puis le rendre

Sauvegardez le fichier de configuration, et lisez le nombre de Pods que le
nœud accepte :

```bash
sudo cp /var/lib/kubelet/config.yaml ~/kubelet-config.sauve.yaml; kubectl get node k8s-cp.lab -o jsonpath='pods allouables={.status.allocatable.pods}{"\n"}'
```

```text
pods allouables=110
```

Passez `maxPods` à 42, redémarrez le kubelet, et relisez :

```bash
sudo grep -q '^maxPods:' /var/lib/kubelet/config.yaml && sudo sed -i 's/^maxPods:.*/maxPods: 42/' /var/lib/kubelet/config.yaml || echo 'maxPods: 42' | sudo tee -a /var/lib/kubelet/config.yaml >/dev/null; sudo systemctl restart kubelet; sleep 15; kubectl get node k8s-cp.lab -o jsonpath='pods allouables={.status.allocatable.pods}{"\n"}'
```

```text
pods allouables=42
```

Le nœud n'accepte plus que 42 Pods : le kubelet a relu son fichier au
redémarrage, et l'a annoncé à l'API. Remettez la sauvegarde :

```bash
sudo cp ~/kubelet-config.sauve.yaml /var/lib/kubelet/config.yaml; sudo systemctl restart kubelet; sleep 15; kubectl get node k8s-cp.lab -o jsonpath='pods allouables={.status.allocatable.pods}{"\n"}'
```

```text
pods allouables=110
```

Retour à 110, la valeur par défaut. Sauvegarder le fichier avant de le
toucher permet de revenir en arrière en une commande si le kubelet ne
redémarre pas.

## 📜 Exercice 4 : le journal, filtré par priorité

Le journal du kubelet est bavard. `-p err` ne garde que les erreurs.
Cherchez-en dans les deux dernières minutes, qui comptent deux redémarrages :

```bash
sudo journalctl -u kubelet --since '-2 min' -p err --no-pager | tail -3 | cut -c1-200; echo "(lignes d'erreur des deux dernières minutes)"
```

```text
-- No entries --
(lignes d'erreur des deux dernières minutes)
```

Aucune erreur : les deux redémarrages se sont bien passés. Sur un kubelet qui
refuse de démarrer, c'est ce filtre qui fait apparaître la ligne qui compte.
Vérifiez enfin son point de santé :

```bash
printf 'santé du kubelet : '; curl -s "http://127.0.0.1:10248/healthz"; echo
```

```text
santé du kubelet : ok
```

## 🧹 Nettoyage

Supprimez la sauvegarde et vérifiez que le kubelet tourne :

```bash
sudo rm -f ~/kubelet-config.sauve.yaml; systemctl is-active kubelet
```

```text
active
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-kubelet
dsoxlab check cka-troubleshoot-kubelet
```

```text
╭─ Résultat : cka-troubleshoot-kubelet ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : le kubelet du worker refuse de démarrer, et il doit
repartir avec une configuration valide.

```bash
dsoxlab run cka-troubleshoot-kubelet
dsoxlab challenge cka-troubleshoot-kubelet
```
