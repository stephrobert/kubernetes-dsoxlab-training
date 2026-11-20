# Challenge : Confiner un Pod et détecter une activité anormale, sans guidage

## La situation

L'équipe sécurité a repris le cluster kubeadm, et son audit est sans appel :
rien n'est confiné, rien n'est exigé, rien n'est surveillé.

- Dans le namespace **`coffre`**, des charges sensibles tournent comme
  n'importe quel conteneur : libres d'écrire partout, de changer des
  permissions, et partageant le noyau de la machine. Le Pod **`tresor`** est
  l'application protégée ; **`ordinaire`** tourne avec le runtime par défaut,
  et on n'y touche pas.
- Le namespace **`maille`** est dans un maillage Istio : **`api`** sert une
  page et **`client-maille`** l'appelle. Depuis **`exterieur`**,
  **`client-nu`**, qui n'a pas de sidecar, lit cette page en clair.
- Dans le namespace **`donnees`**, **`appli`** est le client légitime de la
  base **`base`** (HTTP sur le port 80). **`intrus`** et **`annuaire`** y
  vivent aussi, et tout le monde parle à tout le monde, hors du namespace
  compris.
- **Falco** tourne sur le plan de contrôle `k8s-cp.lab` et écrit ses alertes
  en JSON dans `/var/log/falco/events.json`. Personne ne verrait un shell
  ouvert dans `tresor`.

Les profils AppArmor et seccomp que vous écrirez, le runtime bac à sable
`runsc` et Falco n'existent que sur **`k8s-cp.lab`**. Vous travaillez sur ce
nœud, avec `kubectl` configuré et les droits root par `sudo`. Aucune procédure
n'est donnée : le module vous a appris ce qu'il faut. N'installez et ne
désinstallez rien.

## Ce que vous devez obtenir

**Confiner face au noyau, dans `coffre`** (image `busybox:1.37`, des Pods qui
restent en marche) :

1. Un profil AppArmor nommé **`k8s-coffre-sans-tmp`** est chargé sur
   `k8s-cp.lab` en mode **enforce**. Il refuse toute écriture sous `/tmp` et
   permet le reste.
2. Un Pod **`lecteur`** tourne sur le nœud où ce profil est chargé et le
   déclare.
3. Depuis `lecteur`, écrire dans `/tmp` est refusé, lire le système de
   fichiers fonctionne.
4. Un profil seccomp **`profiles/coffre-sans-chmod.json`**, dans le répertoire
   des profils locaux du kubelet, refuse la famille `chmod` et autorise tout le
   reste par défaut.
5. Un Pod **`calcul`** déclare ce profil local et tourne.
6. Dans `calcul`, un `chmod` échoue et la création d'un fichier fonctionne.

**Chiffrer et filtrer les flux :**

7. Le namespace `maille` n'accepte plus que du trafic mutuellement
   authentifié.
8. `client-nu` ne joint plus `api`, `client-maille` le joint toujours.
9. Le namespace `donnees` refuse par défaut le trafic entrant et sortant, pour
   tous ses Pods.
10. Seul `appli` joint `base`, sur le port 80.
11. Les noms se résolvent toujours dans `donnees`, sans rouvrir le reste de la
    sortie.

**Isoler dans un bac à sable :**

12. Le runtime bac à sable que connaît `containerd` est proposé au cluster
    sous le nom **`gvisor-coffre`**.
13. Un Pod **`isole`** tourne dans ce bac à sable et lit un noyau différent de
    celui de la machine.

**Détecter :**

14. Un shell ouvert dans un conteneur de `coffre` lève une alerte d'une règle
    Falco nommée **`coffre-shell`**, de priorité **`CRITICAL`**.
15. Un shell ouvert dans un autre namespace ne déclenche pas cette règle.
16. Les règles livrées avec Falco, `/etc/falco/falco_rules.yaml`, restent
    intactes.

## Comment vous serez évalué

Seize exigences, à poids égal. Le seuil est de **70 sur 100**, et trois exigences
sont **bloquantes** : l'écriture dans `/tmp` refusée (3), le client sans sidecar
bloqué pendant que le client maillé passe (8), et l'alerte Falco pour un shell
dans `coffre` (14). Réussir les autres ne compense pas l'échec de l'un d'eux.

Les tests lisent le nœud et le cluster, jamais vos fichiers : ils écrivent et
lancent vraiment `chmod` dans les Pods, font de vraies connexions entre Pods,
comparent les noyaux, et ouvrent eux-mêmes un shell dans `tresor`, puis dans
un Pod d'`exterieur`, avant de lire les alertes écrites par Falco.

```bash
dsoxlab check  k8s-challenge-confiner-et-detecter
dsoxlab submit k8s-challenge-confiner-et-detecter
```
