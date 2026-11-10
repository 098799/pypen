"""What a failed AI call means for the person waiting on it (UX U24, U25).

Every failure said "did not answer, try again, or with a sharper photo", also
when the key was refused or the prepaid credit had run out (Gemini on 4 Nov
2026, both Anthropic keys the same day): no new photo or second try can help
then, and the photo was blamed. `why(exc)` gives the words for those two; any
other failure keeps the caller's own words.
"""


def kind(exc: BaseException) -> str:
    """'key', 'credit' or '' (anything else: a timeout, a bad answer)."""
    text = f"{type(exc).__name__} {exc}".lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if any(w in text for w in ("credit balance", "prepay", "billing", "resource_exhausted", "quota")) or status == 429:
        return "credit"
    if any(w in text for w in ("authenticationerror", "permissiondenied", "api key", "api_key", "unauthorized")) or status in (401, 403):
        return "key"
    return ""


def why(exc: BaseException, service: str) -> str:
    """A sentence for the toast, or '' when the caller's own words fit better."""
    k = kind(exc)
    if k == "credit":
        return f"{service} refused: its credit has run out. Nothing to fix in the photo; top it up and try again."
    if k == "key":
        return f"{service} refused the API key. Nothing to fix in the photo; the key needs renewing."
    return ""
