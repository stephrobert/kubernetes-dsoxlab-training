# Épreuve du niveau 4 : administrer un cluster

## La situation

Vous reprenez, au pied levé, le cluster kubeadm qui héberge la **boutique**.
L'équipe précédente vous laisse un état hérité, et une liste de soucis :

- le plan de contrôle **`k8s-cp.lab`** est en vrac : le nœud est NotReady et
  `kubectl` ne répond plus ;
- le worker **`k8s-w1.lab`** a été réinitialisé et n'est plus dans le cluster ;
- hier soir, une fausse manœuvre a **supprimé toute la boutique**. Une
  sauvegarde d'etcd de la veille existe : **`/var/backups/etcd/etcd-veille.db`**.
  Depuis, quelqu'un a écrit dans le cluster un objet **`apres-la-veille`**, qui
  n'a rien à y faire ;
- les manifestes de la boutique vivent dans le dépôt git
  **`~/epreuve/manifestes`**, et certains datent d'une époque révolue ;
- le cluster tourne en **1.36.4** et doit passer en **1.37.0** ;
- deux certificats du plan de contrôle ont été réémis pour quelques jours
  seulement ;
- une fois la boutique revenue, son composant **`panier`** ne démarre pas.

La direction veut aussi la preuve qu'un plan de contrôle **hautement
disponible** tient la perte d'un de ses membres. Faute de trois machines
libres, elle vous confie l'hôte **`k8s-kind.lab`**, où Docker et kind sont
installés. Vous y montez un cluster kind nommé **`ha`**, avec l'image de nœud
du catalogue :

```text
kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

Vous êtes sur `k8s-cp.lab`, avec `kubectl` configuré et les droits `sudo`.
`ssh k8s-w1.lab` et `ssh k8s-kind.lab` ouvrent une session sur les deux autres
machines, où vous avez aussi `sudo`. `etcdctl` et `etcdutl` sont installés
sur le plan de contrôle, à la version de son etcd.

## Le cahier des charges

1. Le worker **`k8s-w1.lab`** fait de nouveau partie du cluster, **Ready**, et
   son kubelet annonce une version **1.37**.
2. Le **swap** est coupé sur le worker, et **rien ne le rallumera** au
   prochain démarrage.
3. Le cluster **`ha`** compte **trois plans de contrôle**, tous **Ready**, lus
   par l'**adresse du répartiteur** placé devant leurs API servers.
4. L'**API** de `ha` répond toujours **par cette adresse** quand un de ses plans
   de contrôle est arrêté.
5. **Avant de restaurer quoi que ce soit**, une sauvegarde fraîche d'etcd est
   prise dans **`/var/backups/etcd/etcd-avant-restauration.db`**, et vérifiée.
6. La boutique est revenue **par restauration** de la sauvegarde de la veille :
   ce sont **les mêmes objets**, pas des copies recréées depuis le dépôt.
7. L'objet **`apres-la-veille`** n'existe plus, et **tous les nœuds** sont
   **Ready**.
8. Au **dernier commit** du dépôt, aucun manifeste n'emploie plus une API
   retirée de Kubernetes, et l'API server les **accepte tous**. Aucun ne
   disparaît du dépôt : ils se migrent.
9. L'API server et **chaque nœud** annoncent **1.37.0**, aucun nœud n'est
   resté hors du scheduling, et la vitrine garde **tous ses exemplaires
   prêts**.
10. Pendant toute maintenance volontaire, la vitrine garde **au moins un
    exemplaire disponible**, et le cluster le garantit.
11. Le worker a été **vidé** sans couper la boutique, puis **remis en
    service** : il accepte de nouveau des Pods.
12. Le nœud NotReady est **Ready**, et son kubelet **repartira seul** après un
    redémarrage.
13. L'API server répond de nouveau et **autorise toujours** les requêtes par
    les modes **Node** et **RBAC**.
14. **`panier`** a tous ses exemplaires disponibles, **ne redémarre plus**, et
    lit sa configuration là où il la cherche.
15. **Avant chaque réparation**, la cause est consignée, d'après `describe`,
    les événements ou les journaux, dans **`~/epreuve/constats/`** : un fichier
    **`kubelet.txt`**, un fichier **`apiserver.txt`** et un fichier
    **`panier.txt`**, chacun nommant ce qui était en cause. Ensuite, on n'y
    touche plus : leur date est comparée au démarrage de ce qui a été réparé.
16. Ce que vous avez changé **en direct** sur `panier` porte **la même valeur**
    au dernier commit du dépôt, sans écart avec le cluster.
17. **Aucun certificat** du plan de contrôle n'expire dans moins de **trente
    jours**.
18. Les exemplaires de la vitrine tournent sur **des nœuds différents**, et
    aucun ne reçoit de trafic **avant d'être prêt à servir**.

## Comment vous serez noté

L'épreuve est notée sur l'**état final** des deux clusters, du dépôt et des
constats, jamais sur les commandes tapées. Elle compte **dix-huit critères**
de même poids. Le seuil est de **70 sur 100**, et **sept critères sont
critiques** : ils doivent tous réussir, quel que soit le total. Ce sont les
critères **1, 3, 4, 6, 9, 12 et 13**.

L'ordre dans lequel vous travaillez compte : une restauration ramène tout le
cluster à la veille, y compris ce que vous y auriez fait avant elle.

Chaque check agit sur les clusters : le correcteur **arrête lui-même** un plan
de contrôle de `ha` (il gèle son conteneur) puis le remet en marche, et lance
dans la boutique un Pod éphémère, `sonde-placement`, que le scheduler doit
placer sur le worker. Le retour se limite au verdict : réussi ou non, et la
note.

Quatre indices sont disponibles, du plus vague au plus précis. Ils coûtent 10, 15, 20 et 25 points,
retirés du barème : un indice pris rend le seuil plus difficile à atteindre.

```bash
dsoxlab check  k8s-epreuve-administrer-un-cluster
dsoxlab submit k8s-epreuve-administrer-un-cluster
```
