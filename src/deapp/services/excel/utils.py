from datetime import datetime, time
import re
from collections.abc import Sequence, Mapping
from difflib import SequenceMatcher
from fractions import Fraction

from deapp.models.excel.field import FlaggedValue
from deapp.models.extracted_data import ExtractedData, ProductionActivity


PRODUCTION_LINES = [
    "Dry Syrup",
    "Capsule",
    "Tablet"
]

PRODUCTS = {
    "01" : "ORS X3", 
    "05" : "ASTAMENTIN 60ML",
    "06" : "ASTAPICIN 60ML",
    "07" : "ASTARCLOX 60ML",
    "08" : "ASTAMOCIL 60ML",
    "09" : "ASTARCLOX 500MG",
    "10" : "ASTAMOCIL 500MG",
    "11" : "ASTAMENTIN 625MG",
    "16" : "NESLIN 250MG",
    "17" : "NAZAMOX 250MG",
}

MACHINE_BY_LINE = {
    "Capsule 1": "ALU/PVC 1",
    "Capsule 2": "ALU/PVC 2",
    "Tablet": "ALU/ALU",
}

PRODUCT_PIECES_PER_CARTON ={
    # product code and number of peices per carton
    "01" : 56, 
    "05" : 40,
    "06" : 100,
    "07" : 100,
    "08" : 100,
    "09" : 100,
    "10" : 100,
    "11" : 200,
    "16" : 200,
    "17" : 200,
}

def to_blistering_machine(
    extracted_data: ExtractedData,
    activity: ProductionActivity,
) -> FlaggedValue[str | None]:
    """Resolve the blistering machine from the filling production line."""
    filling_line = to_filling_production_line(extracted_data, activity)

    if filling_line.flag == 2 or not isinstance(filling_line.value, str):
        return FlaggedValue(None, 2)

    line_name = filling_line.value.strip()

    # The filling-line helper can append the activity-stage number.
    if re.fullmatch(r"Tablet(?: \d+)?", line_name):
        line_name = "Tablet"

    
    machine = MACHINE_BY_LINE.get(line_name)

    if machine is None:
        return FlaggedValue(None, 2)

    return FlaggedValue(machine, filling_line.flag)


def to_filling_production_line(extracted_data: ExtractedData, activity: ProductionActivity) -> FlaggedValue:
    line = to_production_line(extracted_data.production_line)
    stage = activity.stage
    num = _extract_whole_number(stage) or ""

    return FlaggedValue(f"{line.value} {num}", line.flag)

def to_quantity_kg_and_tabs(
    value: str | None,
) -> tuple[FlaggedValue, FlaggedValue]:
    """Extract kilograms and tablet count, assigning flags for missing values."""
    text = to_valid_string(value)

    if not text:
        return FlaggedValue(None, 1), FlaggedValue(None, 1)

    _UNIT_NUMBER_RE = re.compile(
        r"(?<![A-Za-z0-9_])"
        r"(?P<number>\d+(?:[ \t]*,[ \t]*\d{3})*(?:[ \t]*\.[ \t]*\d+)?)"
        r"[ \t]*(?P<unit>kg|k\.g\.?|tabs?|tablets?)(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )

    matches = list(_UNIT_NUMBER_RE.finditer(text))
    kg_matches = []
    tab_matches = []

    for match in matches:
        unit = match.group("unit").casefold().replace(".", "")
        if unit == "kg":
            kg_matches.append(match)
        else:
            tab_matches.append(match)

    # Repeated measurements are ambiguous, so don't guess.
    if len(kg_matches) > 1 or len(tab_matches) > 1:
        return FlaggedValue(None, 2), FlaggedValue(None, 2)

    def number_value(match: re.Match[str]) -> float:
        number = "".join(match.group("number").split()).replace(",", "")
        return float(number)

    if kg_matches and tab_matches:
        return (
            FlaggedValue(number_value(kg_matches[0]), 0),
            FlaggedValue(number_value(tab_matches[0]), 0),
        )

    if not matches:
        return FlaggedValue(None, 2), FlaggedValue(None, 2)

    # Remove recognized measurements before looking for one unlabelled value.
    remaining = list(text)
    for match in matches:
        for index in range(match.start(), match.end()):
            remaining[index] = " "

    remaining_text = "".join(remaining)
    unlabelled_number_pattern = re.compile(
        r"(?<![\w.,/])"
        r"(?P<number>\d+(?:[ \t]*,[ \t]*\d{3})*(?:[ \t]*\.[ \t]*\d+)?)"
        r"(?![\w.,/])",
    )
    unlabelled_numbers = list(unlabelled_number_pattern.finditer(remaining_text))

    if len(unlabelled_numbers) == 1:
        other_quantity = FlaggedValue(number_value(unlabelled_numbers[0]), 0)
        if kg_matches:
            return FlaggedValue(number_value(kg_matches[0]), 0), other_quantity
        return other_quantity, FlaggedValue(number_value(tab_matches[0]), 0)

    missing_flag = (
        2
        if len(unlabelled_numbers) > 1
        or any(char.isalpha() for char in remaining_text)
        else 1
    )

    quantity_kg = number_value(kg_matches[0]) if kg_matches else None
    quantity_tabs = number_value(tab_matches[0]) if tab_matches else None

    return (
        FlaggedValue(quantity_kg, 0)
        if kg_matches
        else FlaggedValue(None, missing_flag),
        FlaggedValue(quantity_tabs, 0)
        if tab_matches
        else FlaggedValue(None, missing_flag),
    )


def to_quantity_kg_and_drums(
    value: str | None,
) -> tuple[FlaggedValue[float | None], FlaggedValue[float | None]]:
    """Extract kilograms and drum count, assigning flags for missing values."""
    text = to_valid_string(value)

    # Empty after conversion: both values are absent with flag 0.
    if not text:
        return FlaggedValue(None, 1), FlaggedValue(None, 1)

    _UNIT_NUMBER_RE = re.compile(
        r"(?<![A-Za-z0-9_])"
        r"(?P<number>\d+(?:[ \t]*\.[ \t]*\d+)?)"
        r"[ \t]*(?P<unit>kg|k\.g\.?|drums?)(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )

    matches = list(_UNIT_NUMBER_RE.finditer(text))

    kg_matches = []
    drum_matches = []

    for match in matches:
        unit = match.group("unit").casefold().replace(".", "")
        if unit == "kg":
            kg_matches.append(match)
        else:
            drum_matches.append(match)

    # Treat repeated measurements as ambiguous rather than guessing.
    if len(kg_matches) > 1 or len(drum_matches) > 1:
        return FlaggedValue(None, 2), FlaggedValue(None, 2)

    # Both values were found.
    if kg_matches and drum_matches:
        quantity_kg = float("".join(kg_matches[0].group("number").split()))
        drums = float("".join(drum_matches[0].group("number").split()))
        return FlaggedValue(quantity_kg, 0), FlaggedValue(drums, 0)

    # Neither unit was found in this non-empty string.
    if not matches:
        return FlaggedValue(None, 2), FlaggedValue(None, 2)

    # Remove the recognized measurement before checking for other letters.
    remaining = list(text)
    for match in matches:
        for index in range(match.start(), match.end()):
            remaining[index] = " "

    missing_flag = 2 if any(char.isalpha() for char in remaining) else 1

    quantity_kg = (
        float("".join(kg_matches[0].group("number").split()))
        if kg_matches
        else None
    )
    drums = (
        float("".join(drum_matches[0].group("number").split()))
        if drum_matches
        else None
    )

    return (
        FlaggedValue(quantity_kg, 0)
        if kg_matches
        else FlaggedValue(None, missing_flag),
        FlaggedValue(drums, 0)
        if drum_matches
        else FlaggedValue(None, missing_flag),
    )

def to_drums_kg_and_capsules(
    value: str | None,
) -> tuple[
    FlaggedValue[float | None],
    FlaggedValue[float | None],
    FlaggedValue[float | None],
]:
    """Extract drum count, kg quantity, and capsule count from a string."""
    text = to_valid_string(value)

    if not text:
        return (
            FlaggedValue(None, 1),
            FlaggedValue(None, 1),
            FlaggedValue(None, 1),
        )

    number_pattern = re.compile(
        r"(?<![\d.,/])"
        r"(?P<number>\d+(?:[ \t]*,[ \t]*\d{3})*(?:[ \t]*\.[ \t]*\d+)?)"
        r"(?![\d.,/])"
    )
    word_pattern = re.compile(r"[A-Za-z]+(?:\.[A-Za-z]+)*")

    numbers = list(number_pattern.finditer(text))
    words = list(word_pattern.finditer(text))

    def one_typo_apart(left: str, right: str) -> bool:
        """Return whether words differ by one edit or adjacent transposition."""
        if left == right or abs(len(left) - len(right)) > 1:
            return left == right

        if len(left) == len(right):
            differences = [
                index
                for index, (left_char, right_char) in enumerate(zip(left, right))
                if left_char != right_char
            ]
            if len(differences) == 1:
                return True
            return (
                len(differences) == 2
                and differences[1] == differences[0] + 1
                and left[differences[0]] == right[differences[1]]
                and left[differences[1]] == right[differences[0]]
            )

        longer, shorter = (left, right) if len(left) > len(right) else (right, left)
        return any(
            longer[:index] + longer[index + 1 :] == shorter
            for index in range(len(longer))
        )

    def matches_anchor(word: str, kind: str) -> bool:
        normalized = word.casefold().replace(".", "")

        aliases = {
            "drums": ("drum", "drums"),
            "kg": ("kg", "kgs", "kilogram", "kilograms"),
            "capsules": ("cap", "caps", "capsule", "capsules"),
        }[kind]

        for alias in aliases:
            if normalized == alias:
                return True

            # Avoid treating a one-letter word such as "g" as the "kg" anchor.
            if alias == "kg" and len(normalized) == 2:
                if one_typo_apart(normalized, alias):
                    return True
            elif len(normalized) >= 3 and len(alias) >= 3:
                if one_typo_apart(normalized, alias):
                    return True

        return False

    def number_before_anchor(anchor: re.Match[str], kind: str) -> float | None:
        preceding = [number for number in numbers if number.end() <= anchor.start()]
        if not preceding:
            return None

        number = max(preceding, key=lambda match: match.end())
        words_between = [
            word
            for word in words
            if number.end() <= word.start() and word.end() <= anchor.start()
        ]

        if kind in ("drums", "kg"):
            # The count or quantity must directly precede its unit.
            if words_between:
                return None
        else:
            # Allow a short descriptor such as "Filled" before "Capsules".
            if len(words_between) > 2:
                return None
            if any(
                matches_anchor(word.group(), other_kind)
                for word in words_between
                for other_kind in ("drums", "kg", "capsules")
            ):
                return None

        numeric_text = "".join(number.group("number").split()).replace(",", "")
        return float(numeric_text)

    def extract(kind: str) -> float | None:
        anchors = [
            word for word in words
            if matches_anchor(word.group(), kind)
        ]
        found = [
            number
            for anchor in anchors
            if (number := number_before_anchor(anchor, kind)) is not None
        ]

        # Leave repeated measurements empty rather than guessing.
        return found[0] if len(found) == 1 else None

    drums = extract("drums")
    quantity_kg = extract("kg")
    capsules = extract("capsules")

    # the way I am handling here, sometimes it will return false negatives
    return (
        FlaggedValue(drums, 0) if drums else FlaggedValue(None, 2),
        FlaggedValue(quantity_kg, 0) if quantity_kg else FlaggedValue(None, 2),
        FlaggedValue(capsules, 0) if quantity_kg else FlaggedValue(None, 2),
    )

def _one_typo_away(word: str, target: str) -> bool:
    word = word.casefold()
    target = target.casefold()

    if word == target:
        return True

    if abs(len(word) - len(target)) > 1:
        return False

    if len(word) == len(target):
        differences = [
            index
            for index, (left, right) in enumerate(zip(word, target))
            if left != right
        ]
        if len(differences) == 1:
            return True
        return (
            len(differences) == 2
            and word[differences[0]] == target[differences[1]]
            and word[differences[1]] == target[differences[0]]
        )

    longer, shorter = (
        (word, target) if len(word) > len(target) else (target, word)
    )
    return any(
        longer[:index] + longer[index + 1:] == shorter
        for index in range(len(longer))
    )


def to_coarse_powder(
    value: str | None,
) -> tuple[FlaggedValue[float | None], FlaggedValue[float | None]]:
    """Extract coarse and fine powder percentages, with quality flags."""
    text = to_valid_string(value)

    if not text:
        return FlaggedValue(None, 1), FlaggedValue(None, 1)

    _WORD_RE = re.compile(r"[A-Za-z]+")
    _NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")  

    exact_labels: dict[str, list[tuple[str, int, int]]] = {
        "coarse": [],
        "fine": [],
    }
    fuzzy_labels: dict[str, list[tuple[str, int, int]]] = {
        "coarse": [],
        "fine": [],
    }

    for match in _WORD_RE.finditer(text):
        word = match.group().casefold()
        label: str | None = None

        if word == "coarse":
            exact_labels["coarse"].append(
                ("coarse", match.start(), match.end())
            )
        elif word in {"fine", "fines"}:
            exact_labels["fine"].append(
                ("fine", match.start(), match.end())
            )
        elif _one_typo_away(word, "coarse"):
            fuzzy_labels["coarse"].append(
                ("coarse", match.start(), match.end())
            )
        elif (
            _one_typo_away(word, "fine")
            or _one_typo_away(word, "fines")
        ):
            fuzzy_labels["fine"].append(
                ("fine", match.start(), match.end())
            )

    labels = (
        exact_labels["coarse"] or fuzzy_labels["coarse"]
    ) + (
        exact_labels["fine"] or fuzzy_labels["fine"]
    )
    labels.sort(key=lambda label: label[1])

    labeled_values: dict[str, list[float]] = {
        "coarse": [],
        "fine": [],
    }

    for index, (label, _, value_start) in enumerate(labels):
        value_end = (
            labels[index + 1][1]
            if index + 1 < len(labels)
            else len(text)
        )
        match = _NUMBER_RE.search(text, value_start, value_end)
        if match:
            labeled_values[label].append(float(match.group()))

    if (
        len(labeled_values["coarse"]) == 1
        and len(labeled_values["fine"]) == 1
    ):
        return (
            FlaggedValue(labeled_values["coarse"][0], 0),
            FlaggedValue(labeled_values["fine"][0], 0),
        )

    numbers = [float(match.group()) for match in _NUMBER_RE.finditer(text)]
    if len(numbers) == 2:
        return FlaggedValue(numbers[0], 3), FlaggedValue(numbers[1], 3)

    return FlaggedValue(None, 2), FlaggedValue(None, 2)

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

def to_valid_string(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    
    if not any(character.isalnum() for character in value):
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



def contains_close_word(text: str, target: str, cutoff: float = 0.9) -> bool:
    words = re.findall(r"[a-z]+", text.casefold())
    return any(
        SequenceMatcher(None, word, target).ratio() >= cutoff
        for word in words
    )

def to_idle_duration(value: str | None) -> FlaggedValue[time | None]:
    """Parse an elapsed HH:MM[:SS] duration without applying shift offsets."""
    if value is None:
        return FlaggedValue(None, 1)
    if not isinstance(value, str):
        return FlaggedValue(None, 2)

    normalized = re.sub(r"\s+", "", value)
    if not normalized or re.fullmatch(r"[-=]+", normalized):
        return FlaggedValue(None, 1)

    match = re.fullmatch(
        r"(?P<hours>\d{1,2}):(?P<minutes>\d{1,2})"
        r"(?::(?P<seconds>\d{1,2}))?",
        normalized,
    )
    if match is None:
        return FlaggedValue(None, 2)

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds") or 0)
    if hours > 23 or minutes > 59 or seconds > 59:
        return FlaggedValue(None, 2)

    return FlaggedValue(time(hours, minutes, seconds), 0)

def to_drums_kg_and_blisters(
    value: str | None,
    mc_no: str | None,
) -> tuple[
    FlaggedValue[float | None],
    FlaggedValue[float | None],
    FlaggedValue[float | None],
]:
    """Extract drum count, kg quantity, and blister count from activity text."""
    from html import unescape

    def valid_part(raw: str | None) -> str:
        text_part = to_valid_string(raw)
        if text_part:
            return text_part

        # to_valid_string treats palindromes such as "7" as empty.
        # Keep numeric-only values so they can count as unlabelled blisters.
        if isinstance(raw, str) and re.fullmatch(
            r"\d+(?:[ \t]*,[ \t]*\d{3})*(?:[ \t]*\.[ \t]*\d+)?",
            raw.strip(),
        ):
            return raw
        return ""

    text = " ".join(
        part for part in (valid_part(value), valid_part(mc_no)) if part
    )
    text = unescape(text).replace("\u00a0", " ").strip()

    if not text:
        return (
            FlaggedValue(None, 1),
            FlaggedValue(None, 1),
            FlaggedValue(None, 1),
        )

    number_pattern = re.compile(
        r"(?<![\d.,/])"
        r"(?P<number>\d+(?:[ \t]*,[ \t]*\d{3})*(?:[ \t]*\.[ \t]*\d+)?)"
        r"(?![\d.,/])"
    )
    word_pattern = re.compile(r"[A-Za-z]+(?:\.[A-Za-z]+)*")

    numbers = list(number_pattern.finditer(text))
    words = list(word_pattern.finditer(text))

    aliases = {
        "drums": ("drum", "drums"),
        "kg": ("kg", "kgs", "kilogram", "kilograms"),
        "blisters": (
            "blister",
            "blisters",
            "blistered",
            "blistering",
            "sachet",
            "sachets",
            "bs",
        ),
    }

    def one_typo_apart(left: str, right: str) -> bool:
        """Match one insertion, deletion, replacement, or adjacent transposition."""
        if left == right or abs(len(left) - len(right)) > 1:
            return left == right

        if len(left) == len(right):
            differences = [
                index
                for index, (left_char, right_char) in enumerate(zip(left, right))
                if left_char != right_char
            ]
            if len(differences) == 1:
                return True
            return (
                len(differences) == 2
                and differences[1] == differences[0] + 1
                and left[differences[0]] == right[differences[1]]
                and left[differences[1]] == right[differences[0]]
            )

        longer, shorter = (
            (left, right) if len(left) > len(right) else (right, left)
        )
        return any(
            longer[:index] + longer[index + 1 :] == shorter
            for index in range(len(longer))
        )

    def is_anchor(word: str, kind: str) -> bool:
        normalized = word.casefold().replace(".", "")

        for alias in aliases[kind]:
            if normalized == alias:
                return True

            # Keep short labels exact to reduce accidental unit matches.
            if alias == "bs":
                continue
            if alias == "kg" and normalized in {"mg", "g"}:
                continue

            if len(normalized) >= 3 and len(alias) >= 3:
                if one_typo_apart(normalized, alias):
                    return True
            elif alias == "kg" and len(normalized) == 2:
                if one_typo_apart(normalized, alias):
                    return True

        return False

    def find_labelled_numbers(kind: str) -> dict[tuple[int, int], float]:
        """Find numbers associated with one recognized unit or label."""
        found: dict[tuple[int, int], float] = {}

        for word in words:
            if not is_anchor(word.group(), kind):
                continue

            preceding = [
                number for number in numbers if number.end() <= word.start()
            ]
            if not preceding:
                continue

            number = max(preceding, key=lambda match: match.end())
            words_between = [
                other_word
                for other_word in words
                if number.end() <= other_word.start()
                and other_word.end() <= word.start()
            ]

            if kind in {"drums", "kg"} and words_between:
                continue

            if kind == "blisters":
                if len(words_between) > 2:
                    continue
                if any(
                    is_anchor(other_word.group(), "drums")
                    or is_anchor(other_word.group(), "kg")
                    for other_word in words_between
                ):
                    continue

            number_text = (
                number.group("number").replace(",", "").replace(" ", "")
            )
            found[(number.start(), number.end())] = float(number_text)

        return found

    drum_values = find_labelled_numbers("drums")
    kg_values = find_labelled_numbers("kg")
    blister_values = find_labelled_numbers("blisters")

    # A single unlabelled number is treated as the blister count.
    used_spans = set(drum_values) | set(kg_values) | set(blister_values)
    unlabelled_values = {
        (number.start(), number.end()): float(
            number.group("number").replace(",", "").replace(" ", "")
        )
        for number in numbers
        if (number.start(), number.end()) not in used_spans
    }
    blister_values.update(unlabelled_values)

    def flagged_result(
        values: dict[tuple[int, int], float],
    ) -> FlaggedValue[float | None]:
        if len(values) == 1:
            return FlaggedValue(next(iter(values.values())), 0)
        return FlaggedValue(None, 2)

    return (
        flagged_result(drum_values),
        flagged_result(kg_values),
        flagged_result(blister_values),
    )

def to_number_of_cartons(
    value: str | None,
    batch_no: str | None,
) -> FlaggedValue[float | None]:
    """Convert carton and piece quantities into equivalent cartons.

    Two unlabelled numbers are interpreted as cartons then pieces only when
    the input contains no words. For a single number, a recognizable unit
    label is required.
    """
    text = to_valid_string(value).strip()
    if not text:
        return FlaggedValue(None, 1)

    if not isinstance(batch_no, str) or len(batch_no.strip()) < 2:
        return FlaggedValue(None, 2)

    product_code = batch_no.strip()[:2]
    pieces_per_carton = PRODUCT_PIECES_PER_CARTON.get(product_code)
    if not isinstance(pieces_per_carton, (int, float)) or pieces_per_carton <= 0:
        return FlaggedValue(None, 2)

    carton_words = (
        "carton", "cartons", "cartoon", "cartoons",
        "ctn", "ctns", "cton", "ctons", "crt", "crtn",
    )
    piece_words = (
        "piece", "pieces", "pc", "pcs", "pce", "pces", "pice", "pices",
    )

    def classify_unit(word: str) -> str | None:
        """Recognize carton or piece labels, including common OCR typos."""
        normalized = word.casefold()

        if normalized in carton_words:
            return "cartons"
        if normalized in piece_words:
            return "pieces"

        # Fuzzy matching is limited to longer words so short labels such as
        # "pc" and "ctn" are handled only by their explicit aliases.
        if len(normalized) < 4:
            return None

        carton_score = max(
            SequenceMatcher(None, normalized, alias).ratio()
            for alias in carton_words
            if len(alias) >= 4
        )
        piece_score = max(
            SequenceMatcher(None, normalized, alias).ratio()
            for alias in piece_words
            if len(alias) >= 4
        )

        if max(carton_score, piece_score) < 0.74:
            return None
        if abs(carton_score - piece_score) < 0.08:
            return None

        return "cartons" if carton_score > piece_score else "pieces"

    number_pattern = re.compile(
        r"(?<![\d,.\-])\d+(?:,\d{3})*(?:\.\d+)?(?![\d,.])"
    )
    word_pattern = re.compile(r"[A-Za-z]+")

    number_matches = list(number_pattern.finditer(text))
    words = word_pattern.findall(text)
    numbers = [
        float(match.group().replace(",", ""))
        for match in number_matches
    ]
    units = [
        unit
        for word in words
        if (unit := classify_unit(word)) is not None
    ]

    if len(numbers) == 1 and len(units) == 1:
        if units[0] == "cartons":
            cartons, pieces = numbers[0], 0.0
        else:
            cartons, pieces = 0.0, numbers[0]

    elif len(numbers) == 2:
        if len(units) == 2 and units[0] != units[1]:
            # Pair labels and numbers in the order they appear.
            quantities = dict(zip(units, numbers))
            cartons = quantities["cartons"]
            pieces = quantities["pieces"]

        elif len(units) == 1:
            # A single recognized label identifies the first quantity;
            # the second quantity is assumed to use the other unit.
            if units[0] == "cartons":
                cartons, pieces = numbers
            else:
                pieces, cartons = numbers

        elif not units and not words:
            # Final fallback for a string containing only numbers/separators.
            cartons, pieces = numbers

        else:
            return FlaggedValue(None, 2)

    else:
        return FlaggedValue(None, 2)

    result = cartons + (pieces / pieces_per_carton)
    return FlaggedValue(result, 0)
