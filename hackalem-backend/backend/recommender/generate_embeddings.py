import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recommender.data_loader import load_contractors
from recommender.semantic import SemanticIndex


if __name__ == "__main__":
    index = SemanticIndex(load_contractors())
    index.initialize()
    print(f"Indexed {len(index.contractors)} profiles / {len(index.passages)} passages / {index.dimension} dimensions")
