"""Error hierarchy and STATUS.ID -> exception mapping.

Every rs.ge response carries a STATUS block ``{"ID": int, "TEXT": str}`` (HTTP 200
even on failure). ``ID == 0`` is success; anything else is an error whose ``TEXT`` is
typically Georgian. We surface that text verbatim and add an English gloss for the
handful of codes we recognize.
"""

from __future__ import annotations

# Well-known STATUS.ID values. The full range is undocumented; we only gloss the
# codes we have confirmed meanings for.
INVALID_TOKEN = -104

KNOWN_CODES: dict[int, str] = {
    0: "success",
    -1: "system error (retry later)",
    -2: "invalid action",
    -3: "use test credentials",
    -30: "invalid record id / data error",
    INVALID_TOKEN: "invalid token",
}


class RsgeError(Exception):
    """Base class for all rsge-mcp errors."""


class RsgeConfigError(RsgeError):
    """Missing or invalid configuration / credentials."""


class RsgeEnvelopeError(RsgeError):
    """The API returned a non-success ``STATUS.ID``."""

    def __init__(self, status_id: int, status_text: str, *, gloss: str | None = None) -> None:
        self.status_id = status_id
        self.status_text = status_text
        self.gloss = gloss
        message = f"rs.ge error {status_id}: {status_text or '(no message)'}"
        if gloss:
            message += f" [{gloss}]"
        super().__init__(message)


class RsgeAuthError(RsgeEnvelopeError):
    """Authentication / authorization failure (e.g. invalid token ``-104``)."""


class RsgePinRequiredError(RsgeError):
    """Login needs a two-factor PIN; carries the ``PIN_TOKEN`` to complete it."""

    def __init__(self, pin_token: str, masked_mobile: str | None = None) -> None:
        self.pin_token = pin_token
        self.masked_mobile = masked_mobile
        suffix = f" (code sent to {masked_mobile})" if masked_mobile else ""
        super().__init__(f"Two-factor PIN required to complete rs.ge login{suffix}.")


class RsgeHttpError(RsgeError):
    """Non-200 HTTP response or transport-level failure."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class RsgeTimeoutError(RsgeError):
    """The request timed out."""


def error_for(status_id: int, status_text: str) -> RsgeEnvelopeError:
    """Build the right envelope-error subclass for a ``STATUS.ID``."""
    gloss = KNOWN_CODES.get(status_id)
    if status_id == INVALID_TOKEN:
        return RsgeAuthError(status_id, status_text, gloss=gloss)
    return RsgeEnvelopeError(status_id, status_text, gloss=gloss)
