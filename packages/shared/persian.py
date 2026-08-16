"""Persian text and numeral normalization utilities."""
import re
import unicodedata

# Translation table for Arabic/Persian character unification
_CHAR_MAP = {
    ord("ي"): "ی",
    ord("ى"): "ی",
    ord("ئ"): "ی",
    ord("ك"): "ک",
    ord("ة"): "ه",
    ord("ۀ"): "ه",
    ord("ؤ"): "و",
    ord("إ"): "ا",
    ord("أ"): "ا",
    ord("آ"): "ا",
    ord("ء"): "",
}

# Numeral translations
_DIGIT_MAP = {
    ord("۰"): "0", ord("۱"): "1", ord("۲"): "2", ord("۳"): "3", ord("۴"): "4",
    ord("۵"): "5", ord("۶"): "6", ord("۷"): "7", ord("۸"): "8", ord("۹"): "9",
    ord("٠"): "0", ord("١"): "1", ord("٢"): "2", ord("٣"): "3", ord("٤"): "4",
    ord("٥"): "5", ord("٦"): "6", ord("٧"): "7", ord("٨"): "8", ord("٩"): "9",
}

_PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"]


def normalize_persian_text(text: str | None) -> str:
    """
    Normalizes Persian text:
    - Normalizes Arabic Yeh/Kaf to standard Persian characters.
    - Strips unwanted diacritics (Tashdid, Tanwin, Fathah, etc.).
    - Collapses redundant whitespaces and standardizes Zero-Width Non-Joiners (ZWNJ).
    - Preserves semantic characters while ensuring clean search/comparison.
    """
    if not text:
        return ""

    # Normalize unicode forms
    text = unicodedata.normalize("NFKD", text)

    # Replace character variants
    text = text.translate(_CHAR_MAP)

    # Remove Persian/Arabic diacritics (fatha, damma, kasra, tanwin, tashdid, sukun)
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)

    # Normalize non-breaking and multiple spaces
    text = re.sub(r"[\u2000-\u200B\u200D-\u200F\uFEFF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_ticker(ticker: str | None) -> str:
    """
    Creates a canonical, normalized search key for Iranian tickers.
    Converts numbers to ASCII, trims whitespaces, normalizes characters.
    """
    if not ticker:
        return ""
    normalized = normalize_persian_text(ticker)
    normalized = normalized.translate(_DIGIT_MAP)
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return normalized.strip()


def to_persian_digits(number: int | float | str) -> str:
    """Converts ASCII digits in a number/string to Persian digits."""
    s = str(number)
    out = []
    for char in s:
        if "0" <= char <= "9":
            out.append(_PERSIAN_DIGITS[int(char)])
        else:
            out.append(char)
    return "".join(out)


def to_ascii_digits(text: str) -> str:
    """Converts Persian/Arabic numerals to ASCII numerals."""
    if not text:
        return ""
    return text.translate(_DIGIT_MAP)


def format_currency_fa(amount: float | int, unit: str = "ریال") -> str:
    """Formats a number as Persian currency string with comma thousand-separators."""
    if amount is None:
        return "-"
    formatted = f"{int(amount):,}".replace(",", "،")
    return f"{to_persian_digits(formatted)} {unit}"
