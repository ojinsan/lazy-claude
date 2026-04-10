"""Shared Stockbit request fingerprint helpers."""

STOCKBIT_BROWSER_HEADERS = {
    "accept": "application/json",
    "accept-language": "id-ID",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "referer": "https://stockbit.com/",
    "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def stockbit_headers(token: str, extra: dict | None = None) -> dict:
    headers = {**STOCKBIT_BROWSER_HEADERS, "authorization": f"Bearer {token}"}
    if extra:
        headers.update(extra)
    return headers
