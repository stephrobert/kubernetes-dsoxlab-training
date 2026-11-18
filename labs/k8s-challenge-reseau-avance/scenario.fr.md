# Réparer, ouvrir, faire sortir et auditer les flux d'un cluster Cilium, sans guidage

## La situation

Vous reprenez le cluster Cilium des hôtes `net-*` : un plan de contrôle,
`net-cp.lab`, et deux workers, `net-w1.lab` et `net-w2.lab`. Il tourne
**sans kube-proxy** : Cilium 1.20.5 le remplace. Hubble est actif, et la
**passerelle d'egress** de Cilium est déjà activée. Cilium 1.20.5 déclare
Kubernetes 1.33 à 1.36, et ce cluster tourne en 1.37.

L'équipe précédente laisse quatre sujets ouverts :

- Dans le namespace **`catalogue`**, le Service **`catalogue`** ne répond plus
  depuis le Pod **`client`**. Les Pods du Deployment `catalogue` tournent
  pourtant. Quelqu'un propose de réinstaller kube-proxy.
- Le namespace **`commandes`** refuse tout le trafic entrant, par la
  NetworkPolicy **`refus-par-defaut`**. Le Pod **`panier`** du namespace
  **`boutique`** doit maintenant joindre le Service **`stock`** sur le port 80.
  Le Pod **`robot`**, du même namespace, ne doit pas.
- L'équipe réseau n'accepte le trafic du namespace **`facturation`** vers son
  serveur témoin que s'il vient de l'adresse de **`net-w2.lab`**. L'URL du
  témoin est dans la ConfigMap **`temoin`** de `facturation`. Le témoin note
  chaque requête dans son journal, avec l'adresse source qu'il voit.
- Dans le namespace **`paiement`**, trois clients appellent l'**`api`** toutes
  les deux secondes. L'un d'eux se plaint : l'API ne lui répond plus. Personne
  ne sait lequel, ni pourquoi.

Vous travaillez sur `net-cp.lab`, avec `kubectl` et `helm` configurés et les
droits root par `sudo`. Aucune procédure n'est donnée : le module vous a appris
ce qu'il faut. N'installez et ne désinstallez rien.

## Ce que vous devez obtenir

1. Le Service `catalogue` répond de nouveau depuis le Pod `client`, avec la
   page que servent les Pods du Deployment `catalogue`. kube-proxy reste
   absent, et Cilium le remplace toujours.
2. `panier` joint `stock` sur le port 80. `robot`, et tout Pod d'un autre
   namespace, restent refusés.
3. Le trafic du namespace `facturation` vers le témoin sort par
   **`net-w2.lab`** : le journal du témoin note l'adresse de ce nœud. Cela vaut
   pour tout Pod du namespace, y compris un Pod créé après votre réglage. Les
   autres namespaces sortent toujours par leur propre nœud.
4. Une ConfigMap **`flux-refuse`**, dans `paiement`, désigne le flux refusé avec
   trois clés : **`source`** (le Pod client), **`destination`** (le Pod appelé)
   et **`port`** (le port de destination). Le flux doit **rester refusé** : on
   le désigne, on ne l'ouvre pas.

## Comment vous serez évalué

Quatre états, à poids égal. Le seuil est de **70 sur 100** : trois états sur
quatre. Le retour se limite à la liste des critères non satisfaits, par leur
libellé, et à la note : aucun message ne dit pourquoi.

Les tests lisent le cluster, jamais vos fichiers. Ils interrogent le Service
depuis `client`, font de vraies connexions depuis `panier`, `robot` et un Pod
d'un autre namespace, créent eux-mêmes un Pod neuf dans `facturation` et lisent
le journal du témoin, puis comparent votre ConfigMap aux flux que Hubble marque
`DROPPED` dans les deux dernières minutes.

```bash
dsoxlab check  k8s-challenge-reseau-avance
dsoxlab submit k8s-challenge-reseau-avance
```
