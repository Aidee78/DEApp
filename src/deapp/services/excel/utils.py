from datetime import datetime, time
import re
from collections.abc import Sequence, Mapping
from difflib import SequenceMatcher
from fractions import Fraction

from deapp.models.excel.field import FlaggedValue


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

def to_datetime(value: str | None) -> FlaggedValue:
    """Convert an ISO date or datetime string; return None if empty or invalid."""
    if not isinstance(value, str):
        # The value was not a string, it is not even parseable
        return FlaggedValue(None, 2)

    if not value.strip():
        # It was a string but empty
        return FlaggedValue(None, 1)

    try:
        # It was a string, was parseable and valid
        return FlaggedValue(datetime.fromisoformat(value.strip()),0)
    except ValueError:
        # It was a string, but was not parseable
        return FlaggedValue(None, 2)


def to_shift(value: str | None) -> FlaggedValue:
    """Return 'Day' or 'Night' when exactly one shift is mentioned."""
    if value is None:
        # The value was not a string, it is not even parseable
        return FlaggedValue("Day", 3)
    
    if not value.strip():
        # It was a string but empty
        return FlaggedValue(None, 1)

    shifts = set(re.findall(r"\b(day|night)\b", value.casefold()))

    if shifts == {"day"}:
        return FlaggedValue("Day", 0)
    if shifts == {"night"}:
        return FlaggedValue("Night", 0)
    
    return FlaggedValue(None, 2)

def to_production_line(
    value: str | None,
    *,
    minimum_score: float = 0.85,
    ambiguity_margin: float = 0.05,
) -> FlaggedValue:
    """Return the canonical line name for a clear match, or None."""
    production_lines = PRODUCTION_LINES
    if not isinstance(value, str):
        # The value was not a string, it is not even parseable
        return FlaggedValue(None, 2)
    
    if not value.strip():
        # It was a string but empty
        return FlaggedValue(None, 1)

    def normalize(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

    input_normalized = normalize(value)

    if not input_normalized:
        # was a string but empty
        return FlaggedValue(None, 1)

    # Return the canonical spelling for an exact match after normalization.
    exact_matches = [
        line
        for line in production_lines
        if normalize(line) == input_normalized
    ]
    if len(exact_matches) == 1:
        # was parseable and valid
        return FlaggedValue(exact_matches[0], 0)
    
    if exact_matches:
        # Not exactly parseable, as it returned mutiple
        return FlaggedValue(None, 2)

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
        # The value was not a string, it is not even parseable
        return FlaggedValue(None, 2)

    if (
        len(scored_matches) > 1
        and scored_matches[0][0] - scored_matches[1][0] <= ambiguity_margin
    ):
        # if scored_matches > 1 and the score of the first find and the second are not too different

        # The value was not a string, it is not even parseable
        return FlaggedValue(None, 2)

    return FlaggedValue(scored_matches[0][1])

def to_resolve_product(
    product_name: str | None,
    batch_number: str | None,
    *,
    minimum_score: float = 0.85,
    ambiguity_margin: float = 0.05,
) -> FlaggedValue:
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
            return FlaggedValue(next(iter(exact_matches)), 0)

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
                return FlaggedValue(candidates[0][1], 0)

    # Fall back to the first two digits found in the batch number.
    if isinstance(batch_number, str):
        digits = batch_number[0:2]
        
        return FlaggedValue(products.get(digits[:2]), 0)

    if isinstance(product_name, str) and (not product_name.strip()):
        return FlaggedValue(None, 1) 
       
    return FlaggedValue(None, 2)

def to_batch_number(
    value: str | None
) -> FlaggedValue:
    if not isinstance(value, str):
        return FlaggedValue(None, 2)

    value = value.strip()
    if not value:
        return FlaggedValue(None, 1)
    try:
        int(value)
        return FlaggedValue(value, 0)
    except (ValueError, TypeError):
        digits = "".join(re.findall(r"\d", value))
        if digits:
            return FlaggedValue(value, 0)

    value = to_valid_string(value)
    if not value:
        return FlaggedValue(None, 1)
     
    return FlaggedValue(None, 2)

def to_extract_kg_quantity(value: str | None) -> FlaggedValue:
    """Extract the first number followed by 'kg', or return None."""
    if value is None:
        return FlaggedValue(None, 1)

    pattern = re.compile(
        r"(?<![\w.])"
        r"(?P<number>\d+\s*/\s*\d+|\d+(?:\.\d+)?|\.\d+)"
        r"\s*kg\b",
        re.IGNORECASE,
    )

    for match in pattern.finditer(value):
        number_text = re.sub(r"\s+", "", match.group("number"))
        try:
            return FlaggedValue(float(Fraction(number_text)), 0)
        except (ValueError, ZeroDivisionError):
            continue

    if not to_valid_string(value):
        return FlaggedValue(None, 1)
    
    return FlaggedValue(None, 2)

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
) -> FlaggedValue:
    room_num = _extract_whole_number(value)
    if isinstance(room_num, int):
        return FlaggedValue(f"Dispensing Room {room_num}", 0)

    if isinstance(value, str) and not value.strip():
        return FlaggedValue(None, 1)
    return FlaggedValue(None, 2)

def _consolidate_names(value: str) -> str | None:
    """Split names on symbols or digits, preserve spaces within names."""
    value.capitalize()
    parts = re.split(r"[^\w\s]+|[\d_]+", value, flags=re.UNICODE)
    names = [" ".join(part.split()) for part in parts]
    return ", ".join(name for name in names if name)

def to_personnel_names(value: str | None) -> FlaggedValue:
    if not isinstance(value, str):
        return FlaggedValue(None, 2)

    if value.strip()[::-1] == value.strip():
        return FlaggedValue(None, 1)

    return FlaggedValue(_consolidate_names(value.replace(".", " ")), 0)

def to_valid_string(value: str | None) -> str | None:
    if not isinstance(value, str):
        return ""
    
    if value.strip()[::-1] == value.strip():
        return ""

    return value

def _extract_single_time(
    value: str | None,
    shift: str | None,
) -> FlaggedValue:
    """Extract one time and resolve AM/PM ambiguity using the shift."""
    if not isinstance(value, str):
        return FlaggedValue(None, 2)

    
    if shift is None:
        return FlaggedValue(None, 2)
        raise ValueError("Shift is required to resolve the time.")

    shift_name = shift.strip().casefold()
    if shift_name not in {"day", "night"}:
        return FlaggedValue(None, 2)
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
        return FlaggedValue(None, 2)
        raise ValueError(
            f"Expected one time, but found {len(matches)} in the input."
        )
    if not matches:
        return FlaggedValue(None, 1)

    match = matches[0]
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = int(match.group("second") or 0)
    period = match.group("period")

    if period:
        if not 1 <= hour <= 12:
            return FlaggedValue(None, 2)

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

    return FlaggedValue(time(hour, minute, second), 0)

def extract_time(
    value: str | None,
    shift: str | None,
) -> FlaggedValue:
    """Extract one time and resolve AM/PM ambiguity using the shift."""
    return _extract_single_time(value, shift)

def to_remarks(
    challenges: str | None,
    action_taken_remarks: str | None,
) -> FlaggedValue:
    
    challenges = to_valid_string(challenges)
    action_taken_remarks = to_valid_string(action_taken_remarks)

    if not challenges and (not action_taken_remarks):
        return FlaggedValue(None, 1)


    return FlaggedValue(f"{challenges}. || {action_taken_remarks}.", 0)