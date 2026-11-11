# Prévisualiser avec diff, attendre avec wait

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, le namespace
**`paiements`** fait tourner **`facturation`** en version 1, sur 2 réplicas. Son
dossier versionné, **`~/deploiement/`**, porte `facturation.yaml` et
**`migration.yaml`**, un Job de migration qui n'a jamais été appliqué.

La version 2 :

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## Ce que vous devez obtenir

1. Dans le dossier, `facturation.yaml` décrit la **version 2**, et **le cluster
   correspond au dossier** : le comparer au cluster ne trouve aucune différence.
2. **Tous les Pods** de `facturation` tournent en version 2 et sont Ready, et le
   **Job `migration` est terminé**.
3. **`~/deploiement/releve.txt`** donne le code de sortie de `kubectl diff` dans
   les trois cas, tel que vous l'avez mesuré :

   ```text
   aucune-difference: <code>
   differences: <code>
   erreur: <code>
   ```

4. **`~/deploiement/deployer.sh`**, exécutable, prend un dossier en argument,
   compare ce dossier au cluster, applique s'il y a des différences, puis attend
   la fin du déploiement. Il **sort en 0** quand rien ne diffère, et il
   **s'arrête en erreur, sans rien appliquer**, quand `kubectl diff` ne peut pas
   comparer le dossier.

## Les repères utiles

Prévisualisez chaque changement avant de l'appliquer. Le code de sortie de
`kubectl diff` ne veut pas dire ce qu'on croit : mesurez-le, ne le supposez pas.
Un script en `set -e` qui ignore cette particularité s'arrête au mauvais moment.

Un Deployment peut se dire Available pendant que d'anciens Pods servent encore :
attendez la fin réelle du déploiement, pas seulement sa disponibilité. Attendez
la fin d'un Job sans rester bloqué s'il échoue.

Un `kubectl apply` sur un dossier dont un objet est refusé applique quand même
les autres.

## Comment vous saurez que c'est bon

Les tests comparent votre dossier au cluster, lisent le relevé, vérifient
l'image de chaque Pod et l'état du Job, puis lancent votre script deux fois : sur
le dossier inchangé, et sur une copie qui contient un objet refusé par le
serveur.

```bash
dsoxlab check k8s-verifier-et-attendre
```
