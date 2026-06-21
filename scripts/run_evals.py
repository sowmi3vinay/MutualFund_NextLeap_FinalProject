import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

from services.eval_runner import EVAL_RESULTS_PATH, run_all_evals  # noqa: E402


def main():
    results = run_all_evals()
    print(f"RAG Eval: {results['rag_eval']['status']}")
    print(f"Safety Eval: {results['safety_eval']['status']}")
    print(f"UX Eval: {results['ux_eval']['status']}")
    print(f"Saved results: {EVAL_RESULTS_PATH}")


if __name__ == "__main__":
    main()
