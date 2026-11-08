# Explication du projet

## 1. Objectif

Ce projet est une application locale Streamlit consacrée à deux thèmes :

1. **Systèmes experts** : faits, règles, chaînage avant et chaînage arrière.
2. **Algorithmes de recherche** : graphes orientés pondérés, heuristiques, traces d'exécution et visualisation.

L'architecture sépare clairement l'interface et la logique :

```text
app.py
├── ui/                 interface Streamlit
├── core/expert/        systèmes experts
├── core/search/        algorithmes de recherche
├── data/examples/      exemples JSON
└── tests/              vérification automatique 
```

Le dossier `core` ne dépend pas de Streamlit. NetworkX et Matplotlib sont utilisés uniquement pour les visualisations.

## 2. Fichiers principaux

### `app.py`

Point d'entrée de l'application. Il configure Streamlit, initialise la session et route l'utilisateur vers l'accueil, le module expert, le module de recherche ou la page de sortie.

### `requirements.txt`

Liste les dépendances nécessaires : Streamlit, NetworkX, Matplotlib et Pytest.

### `pytest.ini`

Configure Pytest pour rechercher les tests dans `tests/` et reconnaître la racine du projet comme chemin d'import.

## 3. Module des systèmes experts

### `core/expert/models.py`

Définit les modèles principaux :

- `Rule` représente une règle avec un identifiant, des prémisses et une conclusion;
- `KnowledgeBase` représente une base de faits et de règles;
- `ForwardResult` et `BackwardResult` stockent les résultats;
- `ForwardStep` et `BackwardStep` stockent les traces;
- `ProofNode` et `RuleAttempt` représentent l'arbre de preuve.

La base valide les données, normalise les textes, évite les doublons et calcule une signature stable pour détecter les modifications.

### `core/expert/parsing.py`

Analyse les textes saisis par l'utilisateur. Elle accepte notamment :

```text
SI farine ET beurre ALORS pâte
farine, beurre -> pâte
```

Elle gère aussi `OU`, qui est développé en plusieurs règles.

### `core/expert/forward.py`

Implémente le chaînage avant. Le moteur recherche les règles déclenchables, choisit la première dans l'ordre de la base, ajoute les nouveaux faits et continue jusqu'à atteindre le but ou la saturation.

### `core/expert/backward.py`

Implémente le chaînage arrière. Le moteur part du but, cherche une règle qui peut le produire, puis tente de prouver ses prémisses récursivement. Il gère le retour arrière, les cycles et les échecs.

### `core/expert/explain.py`

Produit les explications lisibles des déductions avant et transforme l'arbre de preuve arrière en données utilisables par l'interface.

### `core/expert/io.py`

Enregistre et charge les bases de connaissances au format JSON. Les fichiers invalides produisent des erreurs de validation.

### `core/expert/examples.py`

Contient les huit bases pédagogiques (des exemples de cours) utilisées par l'application :
`tarte`, `cours_r1_r9`, `exo_avant`, `exo_arriere`, `triangle`, `autruche`, `diagnostic` et `cycle`.

## 4. Module des algorithmes de recherche

### `core/search/models.py`

Définit :

- `Edge` : un arc orienté pondéré;
- `SearchGraph` : le graphe modifiable;
- `SearchParams` : les paramètres des algorithmes;
- `TraceStep`, `SearchStats` et `SearchResult` : traces, statistiques et résultats.

Le graphe conserve l'ordre d'insertion des sommets et des arcs afin de garantir des résultats déterministes.

### `core/search/graph.py`

Valide les graphes et paramètres, calcule leur signature et définit les paramètres utilisés par chaque algorithme.

### `core/search/trace.py`

Contient `SearchNode` et `TraceRecorder`. Les algorithmes enregistrent leur
trace pendant l'exécution : nœuds visités, frontière, parents, successeurs
et événements de recherche.

### `core/search/uninformed.py`

Implémente les six algorithmes non informés :

- BFS;
- UCS;
- DFS itératif;
- DFS récursif;
- DLS;
- IDS.

### `core/search/informed.py`

Implémente les quatre algorithmes informés :

- Greedy;
- A*;
- SBA*;
- RBFS.

Les variantes suivent les règles définies dans les spécifications du projet,
notamment les limites mémoire, les bornes de profondeur et les limites
d'itérations.

### `core/search/registry.py`

Registre central des dix algorithmes. `run_algorithm` valide les entrées,
lance l'algorithme et mesure son temps. `compare_algorithms` permet de
comparer plusieurs résultats.

### `core/search/heuristics.py`

Calcule les vrais coûts vers le but et vérifie l'admissibilité ainsi que la
consistance des heuristiques.

### `core/search/io.py`

Enregistre et charge les graphes au format JSON, avec validation des sommets,
arcs, coûts, états et heuristiques.

### `core/search/examples.py`

Contient les sept graphes d'exemple :
`g1`, `g2`, `g3`, `g4`, `g5`, `t1` et `gn`.

### `core/search/visualization.py`

Contient toute la visualisation graphique :

- disposition du graphe;
- couleurs des nœuds selon leur rôle;
- affichage des arcs, coûts et heuristiques;
- dessin de l'arbre de preuve du chaînage arrière avec NetworkX.

NetworkX ne lance aucun algorithme de recherche : il sert uniquement à
dessiner les graphes et l'arbre de preuve.

### `core/export_examples.py`

Commande qui génère les fichiers JSON d'exemple dans `data/examples/` :

```bash
python -m core.export_examples
```

## 5. Interface `ui/`

### `ui/state.py`

Initialise et conserve l'état Streamlit : page courante, base de
connaissances, graphe, paramètres, résultats et étape affichée.

### `ui/theme.py`

Contient le style général et les en-têtes des pages.

### `ui/components.py`

Contient les composants réutilisables : affichage des erreurs, faits,
règles, résultats et statistiques.

### `ui/home.py`

Affiche le menu principal et les deux cartes d'accès aux modules.

### `ui/expert_page.py`

Affiche le module expert : choix du but et de la méthode, exécution pas à
pas, édition des faits et règles, import/export JSON et arbre de preuve
NetworkX.

### `ui/search_page.py`

Affiche l'éditeur de graphe, la sélection de l'algorithme, les paramètres,
la visualisation, les traces, les statistiques et la comparaison.

### `ui/quit_page.py`

Affiche un message de sortie. Streamlit ne peut pas arrêter son serveur
depuis la page.

## 6. Données et tests

### `data/examples/`

Contient les JSON générés pour les huit bases de connaissances et les sept
graphes d'exemple.

### `tests/`

Les tests vérifient :

- les modèles et validations;
- le parsing;
- les deux moteurs experts;
- les dix algorithmes de recherche;
- les traces et statistiques;
- les heuristiques;
- les formats JSON;
- les contraintes d'architecture, notamment l'absence de recherche NetworkX.

Les dossiers `__pycache__` et `.pytest_cache` sont des caches générés
automatiquement et ne sont pas nécessaires au dépôt.

## 7. Flux d'utilisation

### Raisonnement expert

1. L'utilisateur choisit une base, un but et une méthode.
2. Le moteur calcule tout le résultat et sa trace lorsque **Lancer** est
   utilisé.
3. Les boutons de navigation affichent les étapes déjà calculées.
4. En chaînage arrière, l'arbre NetworkX place le but à la racine et les
   prémisses comme descendants.

### Recherche

1. L'utilisateur charge ou édite un graphe.
2. Il choisit les états initial et but, puis un algorithme.
3. Le registre valide les données et exécute l'algorithme.
4. La trace, les statistiques, le chemin et la figure sont affichés.

Cette organisation rend le projet modulaire, testable et facile à étendre.
