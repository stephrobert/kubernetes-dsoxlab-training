# Épreuve du niveau 2 : déployer une application qui garde ses données

## La situation

La boutique vous confie son déploiement complet, sur le cluster kind
**`multi`** que votre `kubectl` vise déjà : un control plane et deux workers.
Tout vit dans l'espace **`magasin`**, pour l'instant vide. Le répertoire
**`~/boutique/`** est vide lui aussi. Le cahier des charges dit ce qu'il faut
obtenir, pas comment : c'est à vous de choisir les ressources.

Les images :

```text
vitrine      : nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
tout le reste : busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Le cahier des charges

**La vitrine**

- Elle tourne en **trois exemplaires interchangeables**, sur l'image de la
  vitrine **référencée par digest**. Dans le cluster, elle s'appelle
  **exactement `vitrine`**, sans préfixe ni suffixe, même livrée par l'overlay.
- Sa description vit dans une **base** Kustomize, **`~/boutique/base/`**, et
  elle est livrée par un **overlay** **`~/boutique/overlays/prod/`** construit
  sur cette base. Le cluster correspond exactement à cet overlay.
- **Chaque conteneur** de la vitrine, étape de préparation et compagnon compris,
  déclare ce qu'il demande et sa limite. Le
  serveur est sondé au **démarrage**, en **vivacité** et en **disponibilité**,
  sur son **port 80**.
- Une **étape de préparation** écrit la page d'accueil et se termine avant le
  démarrage du serveur. Un **compagnon** reprend dans ses journaux, ligne à
  ligne, les accès que le serveur écrit dans `/var/log/nginx/access.log`, par un
  volume partagé. Le compagnon est **prêt avant le serveur** et reste actif à
  côté de lui pendant toute la vie du Pod, pour ne perdre aucune ligne.
- **Aucun Pod** de l'espace `magasin` ne redémarre.

**La base de données `catalogue`**

- Elle tourne en **deux réplicas** à **identité stable**, créés dans l'ordre et
  nommés **`catalogue-0`** et **`catalogue-1`**, tous **Ready**.
- Chaque réplica a **son propre volume**, monté sur **`/data`**. Le correcteur
  y écrira une donnée sur `catalogue-0`, supprimera ce Pod, et relira la donnée
  sur le Pod recréé.
- Ces volumes sont **créés à la demande** par une classe de stockage qui les
  **garde** quand leur revendication disparaît.

**La sauvegarde**

- La tâche planifiée s'appelle **exactement `sauvegarde`**.
- Elle tourne **chaque jour à 2 h 30** et écrit un fichier dont le nom commence
  par **`sauvegarde`** à la racine d'un volume persistant revendiqué sous le nom
  **`archives`**.
- Lancez-la **une fois à la main** depuis sa planification, et laissez ce
  lancement se terminer.

**L'agent `collecteur`**

- Il s'appelle **exactement `collecteur`** dans le cluster.
- Il tourne en **un exemplaire Ready sur chaque nœud**, control plane compris,
  et le control plane **garde son taint**.

**La ressource personnalisée**

- La CRD **`Sauvegarde`** de la leçon est déjà installée. Créez dans `magasin`
  la Sauvegarde **`nocturne`**, de source **`catalogue`**, gardée **14 jours**,
  rien de plus. L'API doit toujours refuser une rétention hors des bornes du
  schéma.

## Comment vous serez noté

L'épreuve est notée sur l'**état final du cluster**, sur `~/boutique/` et sur
les volumes, jamais sur les commandes tapées. Elle compte **dix critères**, P01
à P10, qui pèsent tous autant. Le seuil est de **70 sur 100**, et **cinq
critères sont critiques** : ils doivent tous réussir, quel que soit le total. Ce
sont la livraison depuis Kustomize sans écart (P01), la vitrine disponible sur
son digest sans redémarrage (P02), la base à identité stable avec un volume par
réplica (P05), la donnée du correcteur qui survit à son Pod (P06), et les
volumes créés par la classe et gardés (P07).

Vous pouvez lancer `dsoxlab check` autant que vous voulez, mais chaque check agit
sur le cluster : il écrit une donnée dans `catalogue-0`, supprime ce Pod et
attend son retour, et envoie une requête à la vitrine.

Sept critères donnent 70, dont les cinq critiques. Aucune procédure n'est
donnée, et l'épreuve ne propose **aucun indice** : les leçons du niveau 2 ont
tout enseigné.

```bash
dsoxlab check  k8s-epreuve-deployer-une-application
dsoxlab submit k8s-epreuve-deployer-une-application
```
