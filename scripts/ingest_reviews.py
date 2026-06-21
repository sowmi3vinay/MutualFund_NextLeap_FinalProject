import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

from services.review_intelligence import generate_review_intelligence  # noqa: E402


def main():
    result = generate_review_intelligence()
    print(
        json.dumps(
            {
                "top_theme": result["top_theme"],
                "actions": result["actions"],
                "weekly_pulse_path": str(PROJECT_ROOT / "data" / "outputs" / "weekly_pulse.json"),
                "fee_explainer_path": str(PROJECT_ROOT / "data" / "outputs" / "fee_explainer.md"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
