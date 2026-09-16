# Capstone : ouvrir une enclave pour une équipe qui n'est pas de confiance

## La situation

Une équipe extérieure va livrer une application dans votre cluster. Le contrat
est signé, la date est prise, et vous ne saurez pas ce qu'elle déploie avant
qu'elle ne le déploie.

On vous demande de lui ouvrir un espace, **`enclave`**, qui reste sûr même si
elle ne l'est pas. La règle que vous a donnée la sécurité tient en une phrase :
ce qui protège cet espace doit tenir sans que personne ne relise leurs
manifestes.

Deux témoins sont déjà en place, et ils ne sont pas à vous : un Pod
**`autorise`** dans `enclave`, porteur du label `role=appelant`, et un Pod
**`intrus`** dans le namespace `dehors`. N'y touchez pas, ils servent à
mesurer.

Comptez environ **45 minutes**, et traitez cela comme l'épreuve : le seuil de
réussite est de **66 %**. Une exigence entièrement satisfaite vaut mieux que
trois à moitié.

## Ce que l'on attend de vous

1. **Le cluster refuse de lui-même ce qui ne doit pas entrer dans l'enclave.**
   Toute charge qui demanderait des privilèges, l'accès au noyau ou à la
   machine doit être rejetée **à la création**, par le cluster, et non par une
   relecture humaine. Le rejet doit être expliqué à qui le subit, et laisser
   une trace pour qui audite.

2. **L'application dispose d'une identité qui lui est propre**, appelée
   `coffre`, et le jeton de cette identité n'est **jamais déposé** dans les
   charges qui l'emploient.

3. **Cette identité ne peut que consulter la liste des charges de son propre
   espace.** Rien d'autre : ni lire les secrets, ni créer ou supprimer quoi
   que ce soit, ni voir ce qui se passe dans les autres espaces.

4. **Une charge nommée `coffre` tourne dans l'enclave**, emploie cette
   identité, et sert une page. On la joint dans le cluster sous le nom
   `coffre`, sur le port `80`.

5. **Rien n'atteint `coffre` depuis l'extérieur de l'enclave.** Seules les
   charges de l'enclave portant le label `role=appelant` y accèdent. Le Pod
   `autorise` doit continuer de passer : ce n'est pas une coupure que l'on
   vous demande, c'est une frontière.

## Si vous bloquez

Un micro-lab vous donne ses repères gratuitement. Un capstone, non : décider
**ce qu'il faut poser** est justement ce qu'il mesure. Les quatre indices vont
du plus vague au plus explicite, ils **coûtent des points**, et le premier ne
nomme aucun objet : il dit seulement quoi regarder d'abord.

```bash
dsoxlab hint cks-capstone-enclave
```

## Comment vous saurez que c'est bon

Deux des cinq tests ne se contentent pas de relire ce que vous avez posé : ils
**tentent** ce qui doit être refusé. Un réglage mal orthographié est accepté
sans broncher par le cluster et ne refuse rien ; une règle dont le sélecteur
ne désigne personne est un objet parfaitement valide qui ne protège rien.

```bash
dsoxlab check cks-capstone-enclave
```
