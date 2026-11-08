"""Write the example knowledge bases and graphs as JSON files."""
"""utile pour régénérer les fichiers JSON d'exemple."""
from __future__ import annotations

from pathlib import Path

from core.expert.examples import EXAMPLE_KBS
from core.expert.io import kb_to_json
from core.search.examples import EXAMPLE_GRAPHS
from core.search.io import graph_to_json

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "data" / "examples"


def export_examples(directory: Path = EXAMPLES_DIR) -> list[Path]:
    """Write every example (idempotent) and return the created paths."""
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for key, example in EXAMPLE_KBS.items():
        path = directory / f"kb_{key}.json"
        path.write_text(kb_to_json(example.kb), encoding="utf-8")
        written.append(path)
    for key, example in EXAMPLE_GRAPHS.items():
        path = directory / f"graph_{key}.json"
        path.write_text(graph_to_json(example.graph), encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    """Export all examples into ``data/examples``."""
    export_examples()


if __name__ == "__main__":
    main()
