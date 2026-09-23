#!/usr/bin/env python3
"""Read-only smoke test for CSS and JavaScript assets served by a Demo instance."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and "stylesheet" in (values.get("rel") or "").split():
            path = values.get("href")
            if path:
                self.assets.append(("css", path))
        elif tag == "script":
            for path in (values.get("src"), values.get("data-src")):
                if path:
                    self.assets.append(("javascript", path))


def fetch(url: str) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "PMQMS-demo-assets-smoke/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.headers.get_content_type(), response.read()
    except HTTPError as error:
        error.close()
        raise RuntimeError(f"HTTP {error.code} for {url}") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Demo origin, e.g. http://127.0.0.1:8171")
    parser.add_argument("--database", required=True, help="Approved Demo database name")
    args = parser.parse_args()

    login_url = urljoin(args.base_url.rstrip("/") + "/", f"web/login?db={args.database}")
    login_status, login_type, body = fetch(login_url)
    if login_status not in (200, 302) or login_type != "text/html":
        raise RuntimeError(f"unexpected login response: HTTP {login_status}, {login_type}")

    asset_parser = AssetParser()
    asset_parser.feed(body.decode("utf-8", errors="replace"))
    assets = [item for item in dict.fromkeys(asset_parser.assets) if "/web/assets/" in item[1]]
    if not any(kind == "css" for kind, _ in assets) or not any(kind == "javascript" for kind, _ in assets):
        raise RuntimeError("login HTML did not reference both CSS and JavaScript assets")

    for kind, path in assets:
        asset_url = urljoin(args.base_url.rstrip("/") + "/", path.lstrip("/"))
        status, content_type, asset_body = fetch(asset_url)
        expected_type = "text/css" if kind == "css" else "application/javascript"
        if status != 200 or content_type != expected_type or not asset_body:
            raise RuntimeError(
                f"invalid {kind} response for {path}: HTTP {status}, {content_type}, {len(asset_body)} bytes"
            )
        print(f"asset={path} status={status} content_type={content_type} bytes={len(asset_body)}")

    print(f"login=PASS status={login_status} content_type={login_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
