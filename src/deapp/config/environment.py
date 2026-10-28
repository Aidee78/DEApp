"""Read secret values from environment variables."""

import os
from collections.abc import Mapping


def load_secrets(
    required_names: tuple[str, ...],
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return required secrets or report missing variable names.

    Values are read from the process environment by default. Supplying
    ``environ`` makes the function straightforward to test.
    """
    source = os.environ if environ is None else environ

    missing = [
        name
        for name in required_names
        if not source.get(name, "").strip()
    ]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return {name: source[name].strip() for name in required_names}

# Use case exmaple:
# zoho_secrets = load_secrets(
#     ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN")
# )