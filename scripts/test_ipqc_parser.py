"""Run the IPQC parser against the sample HTML report in TRASH."""
from pprint import pprint
from pathlib import Path
import sys
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from deapp.parsers.report_parser import parse_production_activities


def main() -> None:
    """Read the sample report, parse its activities, and display them."""
    for n in range(1, 2):
        sample_path = (
            PROJECT_ROOT
            / "TRASH"
            / f"DAILY PACKAGING REPORT (DAY SHIFT).html"
        )

        if not sample_path.is_file():
            raise FileNotFoundError(f"Sample HTML file not found: {sample_path}")

        mail_content = sample_path.read_text(encoding="utf-8", errors="replace")
        activities = parse_production_activities(
            mail_content,
            subject="DAILY PACKAGING REPORT (DAY SHIFT)",
            received_at=datetime(2026,11,2)
            )

        pprint(activities)


if __name__ == "__main__":
    main()
