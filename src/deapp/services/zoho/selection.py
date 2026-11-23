"""Select Zoho messages by normalized subject phrases, then fuzzy signals."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from deapp.services.zoho.mail_client import ZohoMailClient
from deapp.services.zoho.models import ZohoMessage


@dataclass(frozen=True, slots=True)
class FuzzySignal:
    """A subject phrase and its relative importance for one mail type."""

    phrase: str
    weight: float


# These phrases are searched as normalized word sequences within each subject.
# Include common valid variants here; spelling errors can be caught by fuzzy
# signals when a type has no exact matches.
ACCEPTED_SUBJECTS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "ipqc report": (
        "IPQC DAILY REPORT (Processing Units)",
        "IPQC REPORT (Processing Units)",
        "IPQC DAY REPORT (Processing Units)",
        "IPQC NIGHT REPORT (Processing Units)",
        "IPQC NIGHT ACTIVITY REPORT",
        "IPQC NITE ACTIVITY REPORT",
        "IPQC DAILY ACTIVITY REPORT",
    ),
    "packaging report": (
        "PACKAGING REPORT",
        "DAILY PACKAGING REPORT",
    ),
    "processing report": (
        "PROCESSING REPORT",
        "DAILY PROCESSING REPORT",
    ),
    "store packaging report": (
        "BETA- LACTAM PACKAGING/STORE IPQC AREA REPORT",
        "BETA LACTAM STORE/DISPENSING & PACKAGING IPQC DAILY REPORT",
    ),
}


# The weights express how useful each signal is for identifying its type.
# Shift words such as DAY, NIGHT, SHIFT, and DUTY are intentionally omitted:
# they describe the report but do not identify its type.
FUZZY_SIGNALS_BY_TYPE: dict[str, tuple[FuzzySignal, ...]] = {
    "ipqc report": (
        FuzzySignal("IPQC", 4.5),
        FuzzySignal("REPORT", 0.5),
        FuzzySignal("ACTIVITY", 1.0),
        FuzzySignal("PROCESSING UNITS", 1.5),
    ),
    "packaging report": (
        FuzzySignal("PACKAGING", 3.0),
        FuzzySignal("DAILY", 1.0),
        FuzzySignal("REPORT", 0.5),
    ),
    "processing report": (
        FuzzySignal("PROCESSING", 3.0),
        FuzzySignal("DAILY", 1.0),
        FuzzySignal("REPORT", 0.5),
    ),
    "store packaging report": (
        FuzzySignal("BETA LACTAM", 3.0),
        FuzzySignal("STORE", 1.5),
        FuzzySignal("PACKAGING", 1.0),
        FuzzySignal("IPQC", 1.0),
        FuzzySignal("AREA", 0.5),
        FuzzySignal("REPORT", 0.5),
    ),
}


# A signal contributes to a score only if its phrase similarity reaches this.
_SIGNAL_MATCH_FLOOR = 0.72


def get_daily_messages_by_subject(
    mail_client: ZohoMailClient,
    account_id: str,
    processing_date,
    accepted_subjects_by_type: Mapping[str, Sequence[str]] = (
        ACCEPTED_SUBJECTS_BY_TYPE
    ),
    fuzzy_signals_by_type: Mapping[str, Sequence[FuzzySignal]] = (
        FUZZY_SIGNALS_BY_TYPE
    ),
    *,
    minimum_fuzzy_score: float = 0.70,
    ambiguity_margin: float = 0.08,
) -> dict[str, list[ZohoMessage]]:
    """Group messages by subject, fuzzy-matching subjects without exact matches.

    First, normalized accepted phrases are searched within each subject.
    Then, subjects not matched in that pass are scored against every type.
    Fuzzy matches below the threshold or too close to another type's score
    are left unclassified.

    A type with no exact or confident fuzzy match has an empty list.
    """
    _validate_rules(accepted_subjects_by_type, fuzzy_signals_by_type)

    if not 0.0 <= minimum_fuzzy_score <= 1.0:
        raise ValueError("minimum_fuzzy_score must be between 0 and 1.")
    if not 0.0 <= ambiguity_margin <= 1.0:
        raise ValueError("ambiguity_margin must be between 0 and 1.")

    metadata_rows = mail_client.search_messages(
        account_id=account_id,
        start_date=processing_date,
        end_date=processing_date,
    )

    print(f"{len(metadata_rows)} messages found.")

    grouped: dict[str, list[ZohoMessage]] = {
        type_name: []
        for type_name in accepted_subjects_by_type
    }

    # Remember metadata rows that matched any exact phrase. This includes
    # ambiguous exact matches, which should not be reclassified fuzzily.
    exact_match_indices: set[int] = set()

    # Pass 1: normalized accepted-phrase matching.
    for index, metadata in enumerate(metadata_rows):
        subject = metadata.get("subject")
        if not isinstance(subject, str) or not subject.strip():
            continue

        had_exact_match, type_name = _find_exact_type(
            subject,
            accepted_subjects_by_type,
        )
        if not had_exact_match:
            continue

        exact_match_indices.add(index)

        # If accepted phrases from two types match equally specifically,
        # leave the message unclassified rather than guessing.
        if type_name is not None:
            grouped[type_name].append(
                mail_client.get_message(account_id, metadata)
            )

    # Fuzzy fallback applies to unmatched subjects, regardless of whether
    # other messages already matched a type exactly.
    fuzzy_type_names = tuple(accepted_subjects_by_type)

    # Pass 2: fuzzy-score metadata rows not handled by the exact pass.
    for index, metadata in enumerate(metadata_rows):
        if index in exact_match_indices:
            continue

        subject = metadata.get("subject")
        if not isinstance(subject, str) or not subject.strip():
            continue

        ranked_types = sorted(
            (
                (
                    type_name,
                    _score_subject(
                        subject,
                        fuzzy_signals_by_type[type_name],
                    ),
                )
                for type_name in fuzzy_type_names
            ),
            key=lambda result: result[1],
            reverse=True,
        )

        if not ranked_types:
            continue

        best_type, best_score = ranked_types[0]
        if best_score < minimum_fuzzy_score:
            continue

        if len(ranked_types) > 1:
            second_score = ranked_types[1][1]
            if best_score - second_score <= ambiguity_margin:
                continue

        grouped[best_type].append(
            mail_client.get_message(account_id, metadata)
        )

    return grouped


def _normalize_subject(value: str) -> str:
    """Lowercase text and replace punctuation with single spaces."""
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _find_exact_type(
    subject: str,
    accepted_subjects_by_type: Mapping[str, Sequence[str]],
) -> tuple[bool, str | None]:
    """Find the most specific accepted phrase contained in a subject.

    Returns `(False, None)` if no phrase matches. If matching phrases from
    multiple types have the same specificity, returns `(True, None)` to mark
    the subject as ambiguous.
    """
    normalized_subject = f" {_normalize_subject(subject)} "
    matches_by_type: dict[str, int] = {}

    for type_name, accepted_phrases in accepted_subjects_by_type.items():
        for phrase in accepted_phrases:
            normalized_phrase = _normalize_subject(phrase)
            if not normalized_phrase:
                continue

            if f" {normalized_phrase} " in normalized_subject:
                specificity = len(normalized_phrase.split())
                matches_by_type[type_name] = max(
                    matches_by_type.get(type_name, 0),
                    specificity,
                )

    if not matches_by_type:
        return False, None

    highest_specificity = max(matches_by_type.values())
    winners = [
        type_name
        for type_name, specificity in matches_by_type.items()
        if specificity == highest_specificity
    ]

    if len(winners) != 1:
        return True, None

    return True, winners[0]


def _score_subject(
    subject: str,
    signals: Sequence[FuzzySignal],
) -> float:
    """Return a weighted subject score between 0.0 and 1.0."""
    total_weight = sum(signal.weight for signal in signals)
    if total_weight <= 0:
        return 0.0

    subject_tokens = _normalize_subject(subject).split()
    weighted_score = 0.0

    for signal in signals:
        similarity = _best_phrase_similarity(
            signal.phrase,
            subject_tokens,
        )
        if similarity >= _SIGNAL_MATCH_FLOOR:
            weighted_score += signal.weight * similarity

    return weighted_score / total_weight


def _best_phrase_similarity(
    phrase: str,
    subject_tokens: Sequence[str],
) -> float:
    """Compare a signal phrase against nearby subject word sequences."""
    phrase_tokens = _normalize_subject(phrase).split()
    if not phrase_tokens or not subject_tokens:
        return 0.0

    expected_length = len(phrase_tokens)
    candidate_lengths = {
        max(1, expected_length - 1),
        expected_length,
        expected_length + 1,
    }
    normalized_phrase = " ".join(phrase_tokens)
    best_similarity = 0.0

    for candidate_length in candidate_lengths:
        if candidate_length > len(subject_tokens):
            continue

        for start in range(len(subject_tokens) - candidate_length + 1):
            candidate = " ".join(
                subject_tokens[start : start + candidate_length]
            )
            similarity = SequenceMatcher(
                None,
                normalized_phrase,
                candidate,
            ).ratio()
            best_similarity = max(best_similarity, similarity)

    return best_similarity


def _validate_rules(
    accepted_subjects_by_type: Mapping[str, Sequence[str]],
    fuzzy_signals_by_type: Mapping[str, Sequence[FuzzySignal]],
) -> None:
    """Check that subject rules cover the same types and contain valid values."""
    if not accepted_subjects_by_type:
        raise ValueError("At least one mail type must be configured.")

    if set(accepted_subjects_by_type) != set(fuzzy_signals_by_type):
        raise ValueError(
            "Accepted subjects and fuzzy signals must define the same mail types."
        )

    for type_name, phrases in accepted_subjects_by_type.items():
        if not type_name.strip():
            raise ValueError("Mail type names must not be empty.")
        if isinstance(phrases, str) or not phrases:
            raise ValueError(
                f"Accepted subjects for {type_name!r} must be a non-empty sequence."
            )
        if any(not isinstance(phrase, str) or not phrase.strip()
               for phrase in phrases):
            raise ValueError(
                f"Accepted subjects for {type_name!r} must be non-empty strings."
            )

    for type_name, signals in fuzzy_signals_by_type.items():
        if isinstance(signals, str) or not signals:
            raise ValueError(
                f"Fuzzy signals for {type_name!r} must be a non-empty sequence."
            )
        if any(
            not isinstance(signal, FuzzySignal)
            or not signal.phrase.strip()
            or signal.weight <= 0
            for signal in signals
        ):
            raise ValueError(
                f"Fuzzy signals for {type_name!r} must have a phrase "
                "and a positive weight."
            )
