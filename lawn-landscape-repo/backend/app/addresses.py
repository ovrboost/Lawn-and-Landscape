import re

_ABBR = {
    "street": "st", "avenue": "ave", "road": "rd", "drive": "dr", "lane": "ln",
    "court": "ct", "boulevard": "blvd", "circle": "cir", "place": "pl",
    "highway": "hwy", "parkway": "pkwy", "terrace": "ter", "trail": "trl",
    "north": "n", "south": "s", "east": "e", "west": "w",
    "apartment": "apt", "suite": "ste", "missouri": "mo",
}


def normalize_address(address: str) -> str:
    """Lower-case, strip punctuation, abbreviate street words, drop ZIP+4 and country."""
    s = (address or "").lower()
    s = re.sub(r"\b(usa|united states)\b", " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\b(\d{5})\s+\d{4}\b", r"\1", s)
    words = [_ABBR.get(w, w) for w in s.split()]
    return " ".join(words)
