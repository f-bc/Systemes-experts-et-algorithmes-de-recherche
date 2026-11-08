# IA & ML — Assignment 1

Application locale Streamlit pour l'assignement **Systèmes experts et algorithmes de recherche**. L'application fonctionne hors ligne et propose deux modules interactifs.

## Prérequis et installation

- Python 3.11 ou plus récent
- Un environnement virtuel recommandé

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement et tests

```bash
streamlit run app.py
pytest
python -m core.export_examples
```

Le dernier commande régénère les fichiers JSON d'exemple dans `data/examples/`.

## Fonctionnalités

### Systèmes experts

- Base de faits et de règles modifiable.
- Parsing des formes `SI ... ET ... ALORS ...`, `OU`, `->` et `=>`.
- Chaînage avant et chaînage arrière, implémentés dans `core/expert/`.
- Traces d'inférence, arbre de preuve NetworkX, explication, import et export JSON.
- Huit bases d'exemple, dont les exercices des diapositives du chapitre 2.

Pour le chaînage arrière, la preuve est affichée comme un arbre NetworkX :
l'objectif est la racine et les prémisses sont ses enfants. Les couleurs différencient les faits connus, les buts prouvés, les cycles et les échecs.

### Algorithmes de recherche

Le module accepte un graphe orienté pondéré éditable, des états initial/but et des heuristiques. Il implémente les dix algorithmes suivants : BFS, UCS, DFS (version itérative), DFS (version récursive), DLS, IDS, Greedy Search, A*, SBA*, et RBFS.

Chaque exécution conserve une trace détaillée, affiche la frontière et les noeuds visités, dessine le graphe avec NetworkX/Matplotlib, présente le chemin et ses statistiques, et permet une comparaison des algorithmes.

## Architecture

```text
app.py                  routeur Streamlit
ui/                     état, thème, composants et pages
core/expert/            modèles, parsing, chaînages, JSON, exemples
core/search/            graphes, traces, algorithmes, JSON, visualisation
data/examples/          JSON générés
tests/                  tests unitaires et d'architecture
```

## Utilisation

1. Depuis le menu, ouvrir **Systèmes experts** ou **Algorithmes de recherche**.
2. Charger un exemple ou modifier les données.
3. Choisir l'objectif ou les états initial/but.
4. Cliquer sur **Lancer** (pour exécuter étape par étape) puis utiliser **Précédent**, **Suivant**, ou **Tout exécuter** (pour exécuter toutes les étapes).
5. Utiliser les onglets d'édition et les boutons JSON pour conserver les données.

## Livrables

- Code source dans `core/`, `ui/` et `app.py`.
- Documentation.
- Exemples JSON dans `data/examples/`.