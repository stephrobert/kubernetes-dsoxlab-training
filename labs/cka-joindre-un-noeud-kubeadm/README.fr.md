# Joindre un worker à un cluster kubeadm

La leçon montre `kubeadm join` : un nœud rejoint le cluster avec un jeton
d'amorçage et l'empreinte de l'autorité de certification (CA) du cluster. Le
lab a sorti le worker du cluster : c'est le challenge. Ce cours ne joint donc
rien. Il vous fait manipuler ce dont un join a besoin, et ajoute des cas que
la leçon ne montre pas : un jeton court et décrit, le Secret qui le porte,
l'empreinte de la CA recalculée à la main, un join refusé avant de toucher au
nœud, et un jeton supprimé.

Vous travaillez avec des jetons d'essai décrits `essai-cours`, gardés dans le
fichier `~/jeton-essai`. Le challenge porte sur le worker `k8s-w1.lab` : vous
le ferez seul, à la fin.

Page associée : [Joindre un nœud avec kubeadm](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/kubeadm-joindre-un-noeud/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-joindre-un-noeud-kubeadm
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Les commandes de
`kubeadm` demandent `sudo`.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

## 🎟️ Exercice 1 : un jeton qui expire vite, avec une description

Créez un jeton valable 15 minutes, avec une description, puis listez les
jetons :

```bash
sudo kubeadm token create --ttl 15m --description essai-cours > ~/jeton-essai; cat ~/jeton-essai; sudo kubeadm token list | grep -E 'TOKEN|essai-cours'
```

```text
y559h8.a3h0gktefu10b1d3
TOKEN                     TTL         EXPIRES                USAGES                   DESCRIPTION                                                EXTRA GROUPS
y559h8.a3h0gktefu10b1d3   14m         2026-11-21T04:11:22Z   authentication,signing   essai-cours                                                system:bootstrappers:kubeadm:default-node-token
```

Le jeton a deux parties : un identifiant public (`y559h8` ici) et un secret.
Il expire à l'heure indiquée, et sa description dit à quoi il sert. Un jeton
court réduit le risque si quelqu'un le recopie. Sans `--ttl`, kubeadm le rend
valable 24 heures.

## 🗄️ Exercice 2 : le jeton est un Secret

Un jeton d'amorçage est rangé dans un Secret de `kube-system`, nommé d'après
son identifiant. Lisez son type, sa date d'expiration et l'un de ses usages :

```bash
ID=$(cut -d. -f1 ~/jeton-essai); kubectl -n kube-system get secret bootstrap-token-$ID -o jsonpath='{.type}{"\n"}{range .data}{end}'; kubectl -n kube-system get secret bootstrap-token-$ID -o jsonpath='{.data.expiration}' | base64 -d; echo; kubectl -n kube-system get secret bootstrap-token-$ID -o jsonpath='{.data.usage-bootstrap-authentication}' | base64 -d; echo
```

```text
bootstrap.kubernetes.io/token
2026-11-21T04:11:22Z
true
```

Le type `bootstrap.kubernetes.io/token`, la même expiration, et l'usage
« authentification » activé. Qui peut lire les Secrets de `kube-system` peut
donc lire les jetons d'amorçage, et faire entrer une machine dans le cluster.

## 🔏 Exercice 3 : recalculer l'empreinte de la CA

Le nœud qui rejoint vérifie qu'il parle au bon cluster en comparant
l'empreinte (le hash SHA-256) de la clé publique de la CA. Calculez-la à la
main depuis le certificat :

```bash
sudo openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt -noout | openssl pkey -pubin -outform der | sha256sum | cut -d' ' -f1
```

```text
214a42d520d089d390bbda9c97317185dc1d745e07d565e1fe6b68b952121807
```

Comparez avec celle que donne la commande de join prête à l'emploi. Elle crée
au passage un second jeton, valable 5 minutes :

```bash
sudo kubeadm token create --print-join-command --ttl 5m | grep -o 'sha256:[0-9a-f]*'
```

```text
sha256:214a42d520d089d390bbda9c97317185dc1d745e07d565e1fe6b68b952121807
```

Les deux empreintes sont identiques. Savoir la recalculer permet de vérifier
une commande de join reçue par un autre canal, au lieu de lui faire confiance.

## 🚫 Exercice 4 : une empreinte fausse, refusée avant de rien toucher

Depuis le worker, lancez un join à blanc (`--dry-run`) avec une empreinte
fausse, faite de zéros. La commande n'affiche que les lignes qui parlent de
l'empreinte ou d'une erreur :

```bash
IP=$(kubectl get node k8s-cp.lab -o jsonpath='{.status.addresses[0].address}'); ssh -o StrictHostKeyChecking=no k8s-w1.lab "sudo kubeadm join $IP:6443 --token $(cat ~/jeton-essai) --discovery-token-ca-cert-hash sha256:$(printf '0%.0s' $(seq 64)) --dry-run --ignore-preflight-errors=all 2>&1 | grep -i -m2 -E 'hash|error|pin'"
```

```text
error: error execution phase preflight: couldn't validate the identity of the API Server: cluster CA found in cluster-info ConfigMap is invalid: none of the public keys "sha256:214a42d520d089d390bbda9c97317185dc1d745e07d565e1fe6b68b952121807" are pinned
To see the stack trace of this error execute with --v=5 or higher
```

kubeadm a récupéré la CA du cluster, calculé son empreinte, et constaté
qu'elle ne correspond pas à celle qu'on lui a donnée. Il s'arrête dès les
vérifications préalables : le worker n'a pas été modifié. C'est la protection
contre un faux control plane qui se ferait passer pour le vrai.

## 🗑️ Exercice 5 : supprimer un jeton

Supprimez le jeton d'essai, puis cherchez-le dans la liste et parmi les
Secrets :

```bash
sudo kubeadm token delete $(cut -d. -f1 ~/jeton-essai); sudo kubeadm token list | grep -c essai-cours; ID=$(cut -d. -f1 ~/jeton-essai); kubectl -n kube-system get secret bootstrap-token-$ID
```

```text
bootstrap token "y559h8" deleted
0
Error from server (NotFound): secrets "bootstrap-token-y559h8" not found
```

Plus de jeton, plus de Secret : supprimer l'un supprime l'autre. Un jeton
qu'on soupçonne d'avoir fui se révoque ainsi, sans attendre son expiration.

## 🧹 Nettoyage

Supprimez le fichier du jeton et vérifiez qu'aucun jeton d'essai ne reste. Le
jeton de 5 minutes créé à l'exercice 3 expire tout seul :

```bash
rm -f ~/jeton-essai; sudo kubeadm token list | grep -c essai-cours
```

```text
0
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-joindre-un-noeud-kubeadm
dsoxlab check cka-joindre-un-noeud-kubeadm
```

```text
╭─ Résultat : cka-joindre-un-noeud-kubeadm ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests          │
╰───────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : préparer le worker et le faire rejoindre le
cluster, jusqu'à ce qu'il porte un Pod.

```bash
dsoxlab run cka-joindre-un-noeud-kubeadm
dsoxlab challenge cka-joindre-un-noeud-kubeadm
```
