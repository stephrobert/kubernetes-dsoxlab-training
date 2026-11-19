# Challenge : Écrire et valider un manifeste

## 📍 La situation

Le cluster kind **`lab`** tourne sur la machine, et votre kubectl le vise déjà.
L'équipe des commandes vous confie son application **`api`** : il faut la
décrire dans un manifeste, un fichier qu'on garde dans Git.

Le namespace **`commandes`** existe. Il contient déjà un Deployment
**`rapport`** qui ne démarre pas. Le répertoire **`~/commandes/`** est vide.

L'image de l'application, qui est aussi celle que `rapport` doit utiliser :

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

## 🎯 Ce que vous devez obtenir

1. **`~/commandes/api.yaml`** est **un seul fichier** qui contient trois
   objets : une ConfigMap **`api-config`**, un Deployment **`api`** et un
   Service **`api`**. Le serveur l'accepte tel quel.
2. Chacun de ces objets **écrit le namespace `commandes` dans le fichier
   lui-même**. Rien de l'application ne doit se trouver dans `default`.
3. **`api`** a **2 réplicas disponibles**, avec un conteneur sur le port
   **80**, sur l'image ci-dessus.
4. Le Service **`api`**, sur le port **80**, trouve les deux Pods.
5. Le conteneur reçoit **`DEVISE=EUR`** de la ConfigMap **`api-config`**, par
   `envFrom`.
6. **`rapport`** tourne avec **3 réplicas disponibles** sur l'image ci-dessus.
   Il est **corrigé en place** : un `rapport` supprimé puis recréé ne compte
   pas.

## 🧭 Les repères utiles

Ne partez pas d'une page blanche : kubectl sait générer le squelette d'un
objet sans rien créer. Complétez-le, puis faites valider le fichier par le
serveur avant de l'appliquer : kubectl seul ne voit pas toutes les erreurs.

Un objet qui ne nomme pas son namespace va dans celui du contexte courant. Un
fichier peut contenir plusieurs objets, séparés par une ligne `---`.

Un objet existant se corrige sans être supprimé : il existe plusieurs façons
de le faire.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre fichier, le font valider par le serveur, puis lisent
dans le cluster ce qu'il a créé, et l'état de `rapport`.

```bash
dsoxlab check k8s-ecrire-un-manifeste
```
