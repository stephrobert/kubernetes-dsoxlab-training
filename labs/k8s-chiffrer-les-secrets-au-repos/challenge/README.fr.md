# Challenge : chiffrer les Secrets au repos dans etcd et limiter qui les lit

## 🧭 La situation

Un audit vient de relever deux problèmes sur le cluster.

D'abord, l'API server écrit les Secrets **en clair** dans etcd. Les deux
Secrets du namespace **`tresorerie`**, `cle-banque` et `cle-paie`, se lisent
tels quels dans etcd, donc aussi dans chaque sauvegarde d'etcd.

Ensuite, le ServiceAccount **`facturation`** de `tresorerie` peut lire **tous**
les Secrets du namespace. Il n'a besoin que de `cle-banque`.

## 🎯 Ce que vous devez obtenir

1. Tout Secret écrit à partir de maintenant est **chiffré** dans etcd par le
   fournisseur **secretbox**.
2. `cle-banque` et `cle-paie`, qui existaient avant, sont **chiffrés** eux
   aussi dans etcd. Par l'API, ils rendent toujours leur valeur.
3. `facturation` peut lire `cle-banque`, et **rien d'autre** : ni `cle-paie`,
   ni la liste des Secrets, ni leur suivi en continu (`watch`).

## 🔎 Les repères utiles

Vous êtes sur `k8s-cp.lab`, le nœud qui fait tourner l'API server. Son
manifeste est `/etc/kubernetes/manifests/kube-apiserver.yaml`. Le kubelet le
surveille : dès que vous l'enregistrez, il redémarre l'API server, qui
répond de nouveau au bout d'une minute environ. Copiez-le dans un autre
répertoire avant de le modifier, **jamais** dans `/etc/kubernetes/manifests`.

L'API server tourne dans un conteneur : un fichier que vous posez sur le nœud
n'y est visible que si le manifeste le monte.

etcdctl est installé sur le nœud. Il demande les trois certificats d'etcd,
rangés dans `/etc/kubernetes/pki/etcd/`, et `sudo` pour les lire.

La leçon montre comment vérifier qu'un Secret est chiffré, et pourquoi
changer la configuration ne suffit pas pour les Secrets déjà présents.

## ✅ Comment vous saurez que c'est bon

Les tests lisent etcd : ils créent un Secret de test et regardent comment il
est stocké, puis regardent `cle-banque` et `cle-paie`. Ils demandent ensuite à
l'API server ce que `facturation` a le droit de faire (`kubectl auth can-i`).

```bash
dsoxlab check k8s-chiffrer-les-secrets-au-repos
```
