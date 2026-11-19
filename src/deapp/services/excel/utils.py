from datetime import datetime, time
import re
from collections.abc import Sequence, Mapping
from difflib import SequenceMatcher
from fractions import Fraction


PRODUCTION_LINES = [
    "Dry Syrup",
    "Capsule",
    "Tablet"
]
PRODUCTS = {
    "01" : "ORS X3", 
    "05": "ASTAMENTIN 60ML",
    "06": "ASTAPICIN 60ML",
    "07": "ASTARCLOX 60ML",
    "08": "ASTAMOCIL 60ML",
    "09": "ASTARCLOX 500MG",
    "10": "ASTAMOCIL 500MG",
    "11": "ASTAMENTIN 625MG"
}

def to_datetime(value: str | None) -> datetime | None:
    """Convert an ISO date or datetime string; return None if empty or invalid."""
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None

def to_shift(value: str | None) -> str | None:
    """Return 'Day' or 'Night' when exactly one shift is mentioned."""
    if not isinstance(value, str) or not value.strip():
        return None

    shifts = set(re.findall(r"\b(day|night)\b", value.casefold()))

    if shifts == {"day"}:
        return "Day"
    if shifts == {"night"}:
        return "Night"
    return None

def to_production_line(
    value: str | None,
    # production_lines: Sequence[str],
    *,
    minimum_score: float = 0.85,
    ambiguity_margin: float = 0.05,
) -> str | None:
    """Return the canonical line name for a clear match, or None."""
    production_lines = PRODUCTION_LINES
    if not isinstance(value, str) or not value.strip():
        return None

    def normalize(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

    input_normalized = normalize(value)

    if not input_normalized:
        return None

    # Return the canonical spelling for an exact match after normalization.
    exact_matches = [
        line
        for line in production_lines
        if normalize(line) == input_normalized
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if exact_matches:
        return None

    input_numbers = re.findall(r"\d+", input_normalized)
    scored_matches: list[tuple[float, str]] = []

    for line in production_lines:
        line_normalized = normalize(line)
        if not line_normalized:
            continue

        # Don't fuzzy-match different numbered lines to each other.
        if re.findall(r"\d+", line_normalized) != input_numbers:
            continue

        score = SequenceMatcher(
            None,
            input_normalized,
            line_normalized,
            autojunk=False,
        ).ratio()
        scored_matches.append((score, line))

    scored_matches.sort(key=lambda item: item[0], reverse=True)

    if not scored_matches or scored_matches[0][0] < minimum_score:
        return None

    if (
        len(scored_matches) > 1
        and scored_matches[0][0] - scored_matches[1][0] <= ambiguity_margin
    ):
        return None

    return scored_matches[0][1]

def to_resolve_product(
    product_name: str | None,
    batch_number: str | None,
    # products: Mapping[str, str],
    *,
    minimum_score: float = 0.85,
    ambiguity_margin: float = 0.05,
) -> str | None:
    """Find a product by name, then fall back to its two-digit batch code."""

    products = PRODUCTS

    def normalize(value: str) -> str:
        normalized = " ".join(
            re.findall(r"[a-z0-9]+", value.casefold())
        )
        # Treat forms such as "60 ML" and "60ML" as equivalent.
        normalized = re.sub(r"(?<=[a-z])\s+(?=\d)", "", normalized)
        normalized = re.sub(r"(?<=\d)\s+(?=[a-z])", "", normalized)
        return normalized

    if isinstance(product_name, str) and product_name.strip():
        target = normalize(product_name)

        # Prefer normalized exact matches.
        exact_matches = {
            name for name in products.values()
            if normalize(name) == target
        }
        if len(exact_matches) == 1:
            return next(iter(exact_matches))

        # For fuzzy matching, require any numbers in the name to match.
        target_numbers = re.findall(r"\d+", target)
        candidates: list[tuple[float, str]] = []

        for canonical_name in set(products.values()):
            normalized_name = normalize(canonical_name)

            if re.findall(r"\d+", normalized_name) != target_numbers:
                continue

            score = SequenceMatcher(
                None, target, normalized_name, autojunk=False
            ).ratio()
            candidates.append((score, canonical_name))

        candidates.sort(key=lambda item: item[0], reverse=True)

        if candidates and candidates[0][0] >= minimum_score:
            if (
                len(candidates) == 1
                or candidates[0][0] - candidates[1][0] > ambiguity_margin
            ):
                return candidates[0][1]

    # Fall back to the first two digits found in the batch number.
    if isinstance(batch_number, str):
        digits = batch_number[0:2]
        
        return products.get(digits[:2])

    return None

def to_batch_number(
    value: str | None
) -> str | None:
    if value is None:
        return None

    value = value.strip()
    try:
        int(value)
        return value
    except ValueError, TypeError:
        digits = "".join(re.findall(r"\d", value))
        if digits:
            return value

def to_extract_kg_quantity(value: str | None) -> float | None:
    """Extract the first number followed by 'kg', or return None."""
    if not isinstance(value, str):
        return None

    pattern = re.compile(
        r"(?<![\w.])"
        r"(?P<number>\d+\s*/\s*\d+|\d+(?:\.\d+)?|\.\d+)"
        r"\s*kg\b",
        re.IGNORECASE,
    )

    for match in pattern.finditer(value):
        number_text = re.sub(r"\s+", "", match.group("number"))
        try:
            return float(Fraction(number_text))
        except (ValueError, ZeroDivisionError):
            continue

    return None

def _extract_whole_number(value: str | None) -> int | None:
    """Extract the first whole number from text, or return None."""
    if not isinstance(value, str):
        return None

    pattern = re.compile(
        r"(?<![\w.,/])"
        r"(?P<number>[+-]?(?:\d{1,3}(?:,\d{3})+|\d+))"
        r"(?![\w.,/])"
    )

    match = pattern.search(value)
    if match is None:
        return None

    return int(match.group("number").replace(",", ""))

def to_dispensing_room(
    value: str | None
) -> str | None:
    room_num = _extract_whole_number(value)
    if isinstance(room_num, int):
        return f"Dispensing Room {room_num}"

    return None

def _consolidate_names(value: str) -> str | None:
    """Split names on symbols or digits, preserve spaces within names."""
    value.capitalize()
    parts = re.split(r"[^\w\s]+|[\d_]+", value, flags=re.UNICODE)
    names = [" ".join(part.split()) for part in parts]
    return ", ".join(name for name in names if name)

def to_personnel_names(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None

    if value.strip()[::-1] == value.strip():
        return None

    return _consolidate_names(value.replace(".", " "))

def to_valid_string(value: str | None) -> str | None:
    if not isinstance(value, str):
        return ""
    
    if value.strip()[::-1] == value.strip():
        return ""

    return value

def _extract_single_time(
    value: str | None,
    shift: str | None,
) -> time | None:
    """Extract one time and resolve AM/PM ambiguity using the shift."""
    if not isinstance(value, str):
        return None

    
    if shift is None:
        raise ValueError("Shift is required to resolve the time.")

    shift_name = shift.strip().casefold()
    if shift_name not in {"day", "night"}:
        raise ValueError("Shift must be 'Day' or 'Night'.")

    

    pattern = re.compile(
        r"(?<!\w)"
        r"(?P<hour>(?:[01]?\d|2[0-3])):"
        r"(?P<minute>[0-5]\d)"
        r"(?::(?P<second>[0-5]\d))?"
        r"(?:\s*(?P<period>AM|PM))?"
        r"(?!\w)",
        re.IGNORECASE,
    )

    matches = list(pattern.finditer(value))

    if len(matches) > 1:
        raise ValueError(
            f"Expected one time, but found {len(matches)} in the input."
        )
    if not matches:
        return None

    match = matches[0]
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = int(match.group("second") or 0)
    period = match.group("period")

    if period:
        if not 1 <= hour <= 12:
            return None

        if period.upper() == "AM":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12

    elif 1 <= hour <= 12:
        if shift_name == "day":
            # 7 AM–6:59 AM maps to 07:00–18:59;
            # 1:00–6:59 maps to 13:00–18:59.
            if 1 <= hour <= 6:
                hour += 12
        else:
            # Night shift: 7 PM–11:59 PM, then midnight–6:59 AM.
            if hour == 12:
                hour = 0
            elif 7 <= hour <= 11:
                hour += 12

    return time(hour, minute, second)
