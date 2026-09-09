# file: src/lib/f/url_utils.py

from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


def remove_url_params(url: str, remove_params: list[str] | str) -> str:
    """Remove specified query parameters from a single URL."""
    if isinstance(remove_params, str):
        remove_params = [remove_params]

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    for param in remove_params:
        query.pop(param, None)
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def remove_urls_params(urls: list[str], remove_params: list[str] | str) -> list[str]:
    """Remove specified query parameters from a list of URLs."""
    return [remove_url_params(url, remove_params) for url in urls]




def remove_url_params_if_has_params(
    url: str,
    remove_params: list[str] | str,
    required_param: list[str] | str,
) -> str:
    parsed = urlparse(url)
    query_keys = {k for k, _ in parse_qsl(parsed.query)}

    if isinstance(required_param, str):
        required_param = [required_param]

    if not any(p in query_keys for p in required_param):
        return url

    return remove_url_params(url, remove_params)