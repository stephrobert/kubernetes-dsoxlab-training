# Épreuve du niveau 5 : sécuriser un cluster

## La situation

Vous reprenez le cluster kubeadm qui héberge la boutique. Il fonctionne, et
c'est tout ce qu'on lui a jamais demandé. L'audit dresse la liste de ce dont il
hérite :

- l'API server expose son profileur, et un audit CIS du plan de contrôle
  échoue sur plusieurs points ;
- rien ne trace qui lit quoi, données sensibles comprises ;
- l'espace de la boutique, **`boutique`**, accepte n'importe quel Pod et
  n'importe quelle image ; son catalogue, **`catalogue`** (deux exemplaires,
  joignables au nom stable **`catalogue-svc`**), tourne sur
  `nginxinc/nginx-unprivileged:1.21`, une image désignée par un tag, non
  signée et criblée de failles ; à côté, le Pod **`outil-ancien`** a été lancé
  « pour que ça marche », avec tous les privilèges ;
- dans l'espace des factures, **`facturation`**, les charges partagent
  librement le noyau de la machine ; son Pod **`export-comptable`** envoie les
  écritures au cabinet comptable par un canal déjà ouvert, et personne ne
  verrait un outil de téléchargement s'y lancer ;
- dans l'espace **`commandes`**, un maillage Istio accepte le trafic en clair :
  depuis l'espace **`partenaires`**, **`transporteur`**, sans sidecar, lit ce
  que le suivi des commandes **`suivi`** sert au panier **`panier`** ;
- dans l'espace **`paiement`**, **`caisse`** est le client légitime du grand
  livre **`grand-livre`**, la base des paiements (HTTP, port 80), et tous les
  autres, le traceur publicitaire **`publicite`** compris, joignent tout, hors
  de l'espace aussi.

Ce qui se trouve sur `k8s-cp.lab`, où vous travaillez avec `kubectl` et les
droits root par `sudo` :

- **Falco** y tourne et écrit ses alertes en JSON dans
  `/var/log/falco/events.json`. Le runtime bac à sable `runsc` est connu de
  `containerd`. Les profils AppArmor et seccomp que vous écrirez y vivent, et
  seulement là.
- `trivy`, `cosign` et `crane` sont installés. Un **registre local** répond à
  `localhost:5000` : il porte `boutique/catalogue:1.21`, copie de l'image
  d'origine, et `boutique/outil:1.0`, une autre image. Aucune n'est signée. Le
  cluster, lui, tire les images de la boutique depuis Docker Hub.
- Le Dockerfile du catalogue est dans **`/root/boutique`**. Gardez-y aussi vos
  clés de signature : elles ne quittent jamais le nœud.

Aucune procédure n'est donnée, et ce cahier des charges ne nomme aucun objet
Kubernetes : les choisir fait partie de l'épreuve.

## Le cahier des charges

**Plan de contrôle et audit**

1. Le profileur de l'API server ne répond plus ; l'API répond toujours.
2. Un nouvel audit CIS du plan de contrôle compte moins d'échecs qu'au départ,
   et ses contrôles de profilage passent sur chaque composant qu'ils visent.
3. L'API server tourne avec l'audit activé, sa politique et son journal vivant
   sur le nœud.
4. Les lectures des secrets du cluster sont enregistrées en entier ; tout le
   reste en métadonnées seulement.

**Admission, dans l'espace `boutique` et là seulement**

5. Un Pod qui enfreint le standard de sécurité **restricted** est refusé ; un
   Pod conforme est accepté.
6. Un Pod dont l'image est désignée par un tag est refusé, par le cluster
   lui-même ; celui dont l'image est épinglée par son digest est accepté. Les
   autres espaces ne sont pas touchés.
7. `outil-ancien` n'existe plus. Un Pod nommé **`outil`** fait le même travail
   (il dort), sans aucun de ses défauts, et ne voit plus les processus de
   l'hôte.

**Confinement, dans l'espace `facturation`** (image `busybox:1.37`, sur
`k8s-cp.lab`, pour ce groupe et pour le bac à sable)

8. Un Pod **`consultation`**, qui affiche les factures, peut lire son système
   de fichiers mais ne peut rien déposer dans `/dev/shm`, le refus venant d'un
   profil AppArmor chargé en mode enforce.
9. Un Pod **`numerotation`**, qui attribue les numéros de facture, tourne sous
   un profil seccomp local qui refuse la famille `chown` et autorise tout le
   reste.

**Réseau**

10. L'espace `commandes` exige le TLS mutuel : `transporteur` ne joint plus
    `suivi`, `panier` le joint toujours.
11. L'espace `paiement` refuse par défaut le trafic entrant et sortant pour
    tous ses Pods ; seul `caisse` joint `grand-livre`, sur le port 80, et les
    noms se résolvent toujours.

**Bac à sable, dans l'espace `facturation`**

12. Un Pod **`rendu`**, qui fabrique les factures à partir de documents
    reçus, tourne dans le runtime bac à sable et lit un noyau différent de
    celui de la machine.

**Détection**

13. Un outil réseau ou de téléchargement (`wget`, `curl`, `nc` et
    semblables) lancé dans un conteneur de `facturation` lève une alerte d'une
    règle Falco nommée **`outil-reseau-en-facturation`**, de priorité
    **`WARNING`** ; le même outil lancé dans un autre espace, non.
14. Les règles livrées avec Falco restent intactes.

**Chaîne d'approvisionnement, et la boutique**

15. Le catalogue référence son image par le digest que le nœud exécute
    réellement, une image de `nginxinc/nginx-unprivileged` autre que
    l'originale.
16. Sa copie dans le registre local, `localhost:5000/boutique/catalogue`, est
    signée ; la clé publique est publiée dans l'espace `boutique`, et la
    vérification avec elle accepte cette image et refuse `boutique/outil:1.0`.
17. Cette image de production porte strictement moins de failles critiques que
    l'originale.
18. Les constats de l'analyse statique du Dockerfile ont disparu, et il
    construit toujours une image nginx qui sert les pages de la boutique.
19. La boutique répond toujours à `catalogue-svc`, tous ses exemplaires
    disponibles, créés sous les durcissements ci-dessus.

## Comment vous serez évalué

Dix-neuf états, à poids égal, numérotés P01 à P19 dans l'ordre de la grille.
Le seuil est de **70 sur 100**, et sept états sont **critiques** : le
profileur fermé (P01), le journal d'audit (P04), le standard restricted (P05),
le refus des tags (P06), le TLS mutuel (P10), l'alerte Falco (P13) et la
boutique qui répond toujours (P19). Réussir les autres ne compense pas l'échec
de l'un d'eux.

Les tests lisent le nœud et le cluster, jamais vos manifestes : ils rejouent
l'audit CIS, lisent le journal d'audit après deux requêtes réelles, soumettent
des Pods à l'admission, écrivent et lancent `chown` dans les Pods, font de
vraies connexions, comparent les noyaux, lancent eux-mêmes `wget`, vérifient
les signatures avec votre clé publiée, réanalysent les images et interrogent
la boutique.

Des indices existent, ils coûtent des points, et ils vont du plus vague au
plus explicite.

```bash
dsoxlab hint   k8s-epreuve-securiser-un-cluster
dsoxlab check  k8s-epreuve-securiser-un-cluster
dsoxlab submit k8s-epreuve-securiser-un-cluster
```
