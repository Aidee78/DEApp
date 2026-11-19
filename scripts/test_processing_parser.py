"""Run the IPQC parser against the sample HTML report in TRASH."""
from pprint import pprint
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from deapp.parsers.processing_report import parse_processing_activities


def main() -> None:
    """Read the sample report, parse its activities, and display them."""
    for n in range(1, 2):
        sample_path = (
            PROJECT_ROOT
            / "TRASH"
            / f"DAILY PROCESSING REPORT (NIGHT SHIFT).html"
        )

        if not sample_path.is_file():
            raise FileNotFoundError(f"Sample HTML file not found: {sample_path}")

        mail_content = sample_path.read_text(encoding="utf-8", errors="replace")
        activities = parse_processing_activities(mail_content)

        pprint(activities)


if __name__ == "__main__":
    main()
