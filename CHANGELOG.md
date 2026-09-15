# Journal des modifications

Tous les changements notables de ce projet sont consignés dans ce fichier. Le
format s'appuie sur [Keep a Changelog](https://keepachangelog.com/), et le
projet suit le [versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

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
