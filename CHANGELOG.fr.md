# Journal des modifications

**Langue :** [English](./CHANGELOG.md) · [Français](./CHANGELOG.fr.md)

Tous les changements notables de ce projet sont consignés dans ce fichier. Le
format s'appuie sur [Keep a Changelog](https://keepachangelog.com/), et le
projet suit le [versionnage sémantique](https://semver.org/lang/fr/).

## [0.2.1] - 2026-10-19

### Modifié

- **Chaque `doc_url` pointe désormais `www.stephane-robert.info`.** Le site est
  passé de `blog.` à `www.`, et l'ancien hôte redirige en 301 vers le même
  chemin. Rien n'était cassé : `validate-structure --check-urls` suit les
  redirections, et ce catalogue était vert avant qu'une ligne change. La
  migration est une mise au propre et non une réparation : un `doc_url` doit
  pointer la page, pas dépendre d'une redirection qu'il faudra bien retirer un
  jour.

  Les chemins sont identiques entre les deux hôtes : seul l'hôte a changé. Les
  359 `doc_url` que les catalogues déclarent ont été cherchés dans le dépôt du
  site, hors réseau : ils y existent tous, y compris vingt-trois pages que
  l'ancien hôte rendait en 404.

## [0.2.0] - 2026-10-17

### Modifié

- **Le validateur lit le contrat, plus l'encadré du terminal.**
  `scripts/valider-labs.py` lisait le score dans ce que `dsoxlab check`
  *affiche*. Cet encadré est de l'interface : il a changé en dsoxlab 0.4.0 et
  la regex a cessé de trouver quoi que ce soit. Il lit désormais
  `check --json`, qui porte un `schema`, et cette lecture vit dans
  `scripts/verdict_check.py`, **identique dans les douze catalogues**.

- **Trois verdicts, pas deux.** Une exécution dont tous les tests collectés ont
  skippé n'a rien mesuré : elle est **SKIP**, ni verte ni rouge, et reste à
  mesurer. La peindre en rouge accuserait le lab de ce qui manque au poste.
  `--check` sort donc en `10` dans ce cas, contre `1` pour un ROUGE, à l'image
  de `dsoxlab doctor --strict` où 9 se répare et 10 se remesure.

- **Le README prend la structure de référence** commune aux douze catalogues :
  quatorze sections, dans les deux langues. Sept d'entre elles décrivent
  dsoxlab et non le sujet, et sont donc identiques partout.

### Exige

- **dsoxlab 0.4.1 ou plus récent**, qui a introduit le champ `status` de
  `check --json`. Sans lui, le validateur refuse de conclure plutôt que de
  deviner.

## [0.1.1] - 2026-10-15

Les trois labs que le relevé du 2026-10-12 donnait ROUGE sont verts, et le
relevé compte soixante-quatre verdicts VALIDE sur soixante-quatre labs.

Aucun des trois n'avait de défaut de pédagogie : ils enseignent ce qu'ils
annoncent, et deux portaient même, en commentaire, la mesure qui aurait dû les
protéger. Ce qui avait vieilli dans les trois cas, c'est une valeur écrite à la
main là où il fallait lire le monde.

### Corrigé

- **`cks-runtime-sandbox-gvisor` : l'archive gVisor porte sept binaires, pas
  deux.** Elle contient désormais `runsc`, `containerd-shim-runsc-v1` et un
  répertoire `gvisor-bin/` de cinq binaires, dont `gvisor_sentry` que runsc
  exige. `fixtures/prepare.sh` n'installait que les deux de la racine, si bien
  que runsc refusait de créer le moindre bac à sable. Le message ne paraissait
  que dans le journal de containerd, jamais dans la sortie de kubectl, qui se
  contentait d'un délai dépassé sur le Pod. La garde regarde maintenant aussi
  `gvisor-bin/gvisor_sentry`, sans quoi un nœud portant déjà runsc ne
  réinstallerait jamais le répertoire absent.

  Le setup déclare en outre les options de runsc, `SystemdCgroup = true` : le
  socle alignait runc sur les cgroups systemd par un `replace` de chaîne, qui
  n'atteignait pas la section ajoutée ensuite.

- **`cka-kubeadm-upgrade` : la cible du retour était épinglée.** Le cleanup
  visait `1.37.0-1.1` en dur, alors que `shared/kubeadm-cluster.yml` avertit que
  « rien ne fige le PATCH » dans `pkgs.k8s.io/v1.37`. La 1.37.1 est sortie
  depuis, et le cleanup rétrogradait donc le cluster d'un patch à chaque
  passage. Le setup relève maintenant la version du catalogue avant de la
  dégrader, le cleanup la relit, et il ne reste aucun numéro de version dans ce
  fichier. Le numéro de paquet est demandé à APT plutôt que reconstruit, le
  suffixe variant d'une version à l'autre.

- **`cks-istio-mtls-lockdown` : un ConfigMap de plus qu'Istio distribue.** Le
  cleanup retirait `istio-ca-root-cert` namespace par namespace, mais istiod en
  pousse un second, `istio-ca-crl`, qu'une version plus récente a ajouté. Le
  retrait se fait désormais par préfixe `istio-ca-` : nommer les objets un par
  un était la vraie cause, la liste ne pouvant que prendre du retard sur Istio.

- Le catalogue des README suivait des titres de labs périmés, le hook qui
  l'attrape ne jouant qu'au push.

### Ajouté

- **Deux sondes dans le setup de `cks-runtime-sandbox-gvisor`**, et c'est l'une
  d'elles qui a nommé la cause au premier essai. La seconde est la seule qui
  prouve quelque chose : elle lance un Pod témoin dans `runsc` et, sur échec,
  affiche ses Events et le journal de containerd avant de sortir en 1. Elle
  prend son propre namespace jetable, rendu par un `trap`. Un setup doit échouer
  chez lui, avec un message, plutôt que laisser la solution du formateur échouer
  trois minutes plus tard sur un délai dépassé muet.

- **`tests/test_tolerance_de_version.py`**, trente-trois cas. Aucun test ne
  couvrait `scripts/valider-labs.py` jusqu'ici, alors que c'est lui qui décide
  si un lab est publiable.

### Changé, deux tolérances nommées dans le validateur

`cka-kubeadm-upgrade` est le seul lab du catalogue qui touche à la version de
son cluster : son setup le rétrograde pour qu'il y ait quelque chose à monter,
et son cleanup le remonte par `kubeadm upgrade apply` là où le socle monte par
`kubeadm init`. Deux tolérances, nominatives, le reconnaissent :

- la version des nœuds peut être **supérieure ou égale** à celle de la
  photographie initiale, jamais inférieure. Ce n'est pas « on ignore la version
  pour ce lab », c'est « on accepte qu'il laisse le cluster monté, pas qu'il le
  laisse tombé ». Une rétrogradation reste un écart, et c'était exactement le
  défaut corrigé plus haut ;
- les ConfigMaps `kubeadm-config` et `kubelet-config` peuvent différer, parce
  que `kubeadm upgrade apply` les régénère autrement que `kubeadm init`. Mesuré
  en capturant leur contenu : la différence tient en une ligne,
  `resolvConf: /run/systemd/resolve/resolv.conf`, que l'upgrade pose en
  détectant systemd-resolved.

Ce second desserrement est plus large que le premier, la photographie ne portant
que des empreintes. Il reste borné à deux clés nommées et à un identifiant :
`coredns`, `kube-proxy` et tout autre objet de `kube-system` restent comparés, y
compris pour ce lab. Le supprimer plutôt que l'accepter demanderait de faire
écrire `resolvConf` par le socle dès l'`init`, ce qui changerait la façon dont
les soixante-quatre labs montent leur cluster.

### Durées mesurées

`cks-runtime-sandbox-gvisor` 231 s, `cks-istio-mtls-lockdown` 409 s,
`cka-kubeadm-upgrade` 874 s.

## [0.1.0] - 2026-10-09

### Changé, la provenance passe au niveau SLSA 3

Le workflow de release attestait depuis son job de build, ce qui donne le
**niveau 2** : le processus qui fabrique l'archive était aussi celui qui signait
ce qu'il en disait. Le badge, lui, annonçait 3 dans le dépôt Linux jumeau, et
2 ici depuis la mise en conformité. Les deux disent maintenant 3, et le
workflow le produit.

- **`.github/workflows/attester.yml`**, workflow réutilisable, est désormais le
  seul du dépôt à recevoir `attestations: write`. Il ne fait aucun `checkout`,
  ne reçoit qu'un nom et une empreinte, et n'exécute aucun code du dépôt.
- **`release.yml` est découpé en trois jobs** : construire, attester, publier.
  Le job de publication écrit la release mais ne peut pas attester, faute de la
  permission. L'archive est recomparée à son empreinte avant publication, pour
  qu'un artefact altéré entre deux jobs ne parte pas avec une provenance qui ne
  le décrit pas.
- **Deux linters en désaccord, tranché avec une raison.** zizmor recommande la
  forme `uses: $/...`, disponible sur github.com depuis juillet 2026 ;
  actionlint 1.7.12, publié en mars, la rejette encore comme un format
  invalide. La forme `$/` gagne sur le fond, puisqu'elle ne dépend pas de
  l'état du système de fichiers et ne peut donc pas charger un fichier qu'une
  étape précédente aurait déposé. L'exception actionlint est limitée à ce
  message et à ce fichier, datée, et vérifiée ciblée en fabriquant une autre
  faute dans le même fichier : la règle l'attrape toujours.

La vérification qui prouve le niveau est dans `RELEASING.md` : elle nomme le
workflow signataire, et échoue si la provenance vient d'ailleurs.

### Ajouté, la chaîne d'un dépôt public

Le dépôt portait un catalogue et rien autour. Il reprend maintenant ce que le
catalogue Linux jumeau a éprouvé, adapté à Kubernetes et au français.

- **Intégration continue** (`.github/workflows/ci.yml`), six barrières. zizmor
  analyse les workflows, actionlint les vérifie et passe chaque bloc `run:` au
  shellcheck, poutine cherche les chaînes d'exploitation CI/CD, CodeQL lit le
  Python, un job de parité rejoue **tous** les hooks pre-commit, et un dernier
  vérifie le contrat du catalogue avec le réseau.
  - Chaque action est épinglée par SHA de commit complet, et les dix SHA repris
    du dépôt Linux ont été **vérifiés un par un** contre le tag qu'ils
    annoncent avant d'être écrits ici. Copier un épinglage sans le vérifier,
    c'est faire confiance au presse-papier.
  - Le job de parité installe `ansible-core`. Sans `ansible-playbook` sur le
    PATH, le contrôle de syntaxe des playbooks se met en `skip` : le job serait
    resté vert en n'ayant rien vérifié.
  - Le contrôle des leçons jumelées passe par
    `dsoxlab validate-structure --check-urls`, et n'est câblé en aucun hook : un
    commit hors ligne ne doit pas échouer, et une indisponibilité du blog n'a
    rien à voir avec la justesse d'un lab.
- **Six vérificateurs de catalogue** (`tests/`), câblés en pre-commit. Chacun a
  été éprouvé en fabriquant le défaut qu'il vise, sur un lab factice : les neuf
  défauts fabriqués sont tous attrapés.
  - `test_pieges_du_depot.py` couvre les quatre pièges que ce dépôt a payés au
    moins une fois : un `ssh` sans `-n` dans une solution lue par `bash -s`, un
    `prepare.sh` qui ne trace pas sur le nœud, un `setup.yaml` qui n'installe
    pas le socle, un namespace créé mais jamais supprimé.
  - `test_indices.py` refuse un indice en clair, une traduction qui n'en est pas
    une (`text_fr` copie de l'anglais), et des coûts qui ne croissent pas.
  - `test_style_apprenant.py` refuse emoji et tiret cadratin dans ce que
    l'apprenant lit, indices décodés compris.
  - `test_collections_declarees.py` inclut `shared/` dans son périmètre : le
    socle porte le seul appel à une collection externe du dépôt, et l'oublier
    n'aurait contrôlé que la moitié du catalogue.
  - `test_playbooks_syntaxe.py` charge aussi le socle pour lui-même : il arrive
    par `include_tasks`, qu'Ansible ne résout qu'à l'exécution, donc aucun
    `setup.yaml` ne le vérifie.
  - `test_outillage_coherent.py` refuse qu'un vérificateur existe sans être
    câblé : un test débranché ne protège plus rien, en silence.
- **Aucun de ces tests ne refait ce que le moteur rend déjà.** `dsoxlab
  validate-structure` vérifie les liens relatifs cassés, les fixtures déclarées
  et la cohérence des cibles avec `meta.yml` : un second contrôle qui diverge du
  premier est pire qu'aucun.
- **Gouvernance** : `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`,
  `RELEASING.md`, ce journal. En français seulement, contrairement au dépôt
  Linux qui est bilingue : la formation que ce catalogue éprouve est en
  français.
- **Durcissement de la chaîne** : `.github/CODEOWNERS`, `dependabot.yml` groupé
  par lot hebdomadaire avec un délai de décantation, `.poutine.yml`,
  `.plumber.yaml`, workflows OpenSSF Scorecard et Plumber, et un workflow de
  release qui publie un bundle `tar.gz` signé en keyless avec sa provenance
  SLSA.
- **Catalogue généré** (`scripts/gen_catalog.py`) : le README liste les labs par
  certification, avec leur domaine de blueprint, leur leçon jumelée et la date
  de leur dernière validation. Un catalogue écrit à la main se périme en
  silence ; un hook `pre-push` refuse désormais un README périmé.

### Changé

- **`CLAUDE.md` et `todo/` ne sont plus versionnés**, comme dans le dépôt Linux
  jumeau : c'est du pilotage local. La doctrine que `CLAUDE.md` portait et dont
  un contributeur a besoin est passée dans `CONTRIBUTING.md`, qui est publié.

### Ajouté, le catalogue

- **37 labs transposés de K8sExamLab et validés**, chacun joué dans les deux
  sens sur un cluster kubeadm 1.37 à deux nœuds : 0 avant le travail, 100 après
  la solution du formateur, rejouable, et sans laisser de trace sur le cluster.
  Le jalon CKAD est complet. Les mesures sont dans `validation-labs.json`.
- **`scripts/valider-labs.py`**, qui rend ce verdict. Il photographie le
  cluster, joue le cycle complet, puis compare : un lab qui laisse un namespace,
  un `ClusterRole` ou un taint derrière lui est ROUGE, parce que c'est le lab
  suivant qui en paierait le prix. Le validateur a lui-même été éprouvé dans les
  deux sens, sur un `cleanup.yaml` privé de sa suppression de namespace.
- **Le socle à deux nœuds** (`shared/kubeadm-cluster.yml`) : le control plane,
  puis chaque worker déclaré dans `meta.yml`, préparé et joint par délégation.
  Calico remplace Flannel, qui n'applique pas les NetworkPolicy et rendait
  invérifiables quatre labs.

[Non publié]: https://github.com/stephrobert/kubernetes-dsoxlab-training/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/stephrobert/kubernetes-dsoxlab-training/releases/tag/v0.1.1
[0.1.0]: https://github.com/stephrobert/kubernetes-dsoxlab-training/releases/tag/v0.1.0
