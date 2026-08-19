import re


def normalize_for_whatsapp(raw: str):
    """
    WhatsApp Cloud API expects the recipient number in international
    format with no '+', no spaces/dashes (e.g. 923001234567).
    Leads are scraped in whatever format the source site shows
    (0300-1234567, +923001234567, 03001234567, etc) — normalize here.
    Returns None if the number doesn't look usable, so the caller can
    mark that lead as skipped instead of sending garbage to Meta.
    """
    if not raw:
        return None

    digits = re.sub(r"[^\d+]", "", raw)

    if digits.startswith("+92"):
        digits = digits[1:]
    elif digits.startswith("0092"):
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = "92" + digits[1:]
    elif digits.startswith("3") and len(digits) == 10:
        # bare "3xxxxxxxxx" with no country code and no leading 0
        digits = "92" + digits

    if digits.startswith("92") and len(digits) == 12:
        return digits

    return None
