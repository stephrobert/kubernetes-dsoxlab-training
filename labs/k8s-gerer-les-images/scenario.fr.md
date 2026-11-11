# Figer une image par digest et tirer d'un registre privé

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, le namespace
**`galerie`** fait tourner deux Deployments :

- **`affiche`** tourne sur l'image **`nginx:1.30`**, un tag qui peut changer de
  contenu du jour au lendemain ;
- **`vignettes`** tire **`localhost:30500/galerie/vignettes:1.0`**, d'un registre
  privé servi dans le cluster, et ne démarre pas. Son ServiceAccount s'appelle
  **`vignettes`**.

Les identifiants du registre : utilisateur **`galerie`**, mot de passe
**`Vignettes-2026`**. Le répertoire **`~/galerie/`** attend votre relevé.

## Ce que vous devez obtenir

1. **`affiche`** est **figée par digest** sur l'image **qu'elle fait tourner
   aujourd'hui**, ni une autre version ni une image voisine, et tous ses Pods
   tournent sur ce digest.
2. **Avant toute réparation**, **`~/galerie/releve.txt`** dit sur une ligne
   **`cause:`** pourquoi `vignettes` ne tire pas son image : ce que le registre
   attend et ne reçoit pas. Ensuite, n'y touchez plus.
3. **`vignettes`** est disponible : ses identifiants viennent d'un **Secret
   docker-registry porté par son ServiceAccount**, et non écrits dans le Pod.

## Les repères utiles

Un tag désigne une image aujourd'hui ; un digest la désigne pour toujours.
L'image qu'un Pod fait réellement tourner se lit dans son statut, pas dans sa
spec.

Un Pod qui ne tire pas son image dit pourquoi dans ses événements. Lisez-les
avant de corriger quoi que ce soit.

Les identifiants d'un registre privé se donnent à un Pod, ou à son
ServiceAccount. Ils sont injectés à la création d'un Pod : un Pod déjà créé ne
les reçoit pas.

## Comment vous saurez que c'est bon

Les tests comparent le digest d'`affiche` à celui que ses Pods faisaient tourner
au départ, lisent votre relevé et sa date, puis vérifient d'où viennent les
identifiants de `vignettes`.

```bash
dsoxlab check k8s-gerer-les-images
```
