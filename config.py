"""Load runtime configuration from RUNNER_CONFIG env var (JSON)."""
from __future__ import annotations
import json
import os
import re


def load_config() -> dict:
    raw = os.environ.get("RUNNER_CONFIG")
    if not raw:
        raise SystemExit("RUNNER_CONFIG env var not set")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"RUNNER_CONFIG invalid JSON: {e}")


CFG = load_config()
BASE = CFG["target_base_url"]
CAPTCHA_MARKERS = tuple(CFG.get("captcha_markers", []))
REQUIRED_KEYWORDS = tuple(CFG.get("required_keywords", []))
SOURCE_PREFIX = CFG.get("source_prefix", "backfill")
SEARCH_URL_PATH = CFG.get("search_url_path", "")
DETAIL_REFERER_PATH = CFG.get("detail_referer_path", "/")
LIST_URL_PATH = CFG.get("list_url_path", "")
LIST_PAGE_PARAM = CFG.get("list_page_param", "page")
DAILY_SOURCES = CFG.get("daily_sources", [])

# --- Browser impersonation --------------------------------------------------
# ⚠️ 2026-09-01：目標站前面那層 WAF 開始針對 **User-Agent 字串**擋，UA 含
# `Chrome/120` 一律回 HTTP 500 的 "Web Page Blocked" 頁（帶 Attack ID）。
# 只點名 120 這一個版號（119 和 121 都正常）—— 因為它是 curl_cffi 最多爬蟲
# 在用的預設 profile。擋的是 UA 不是 TLS 指紋，也不看來源 IP，
# 所以 GHA runner 換 IP 沒有用。
#
# 下次再被擋：設 IMPERSONATE env（或 RUNNER_CONFIG 加 "impersonate"）換版號即可，
# 不用改 code。選版號要順便量速度——目標站對指紋有慢佇列：
# chrome124 0.75s / chrome131 0.77s / chrome142 1.17s / chrome146 1.06s 每頁，
# chrome136 4.56s 要避開（等於掉回慢佇列）。
IMPERSONATE = os.environ.get("IMPERSONATE") or CFG.get("impersonate", "chrome146")

# 跟 IMPERSONATE 對齊的 UA。部分 script 會自己帶完整 header set（目標站會把
# 缺 header 的請求 slow-lane），那邊的 UA 要從這裡取，不要再各自寫死版號。
_CHROME_MAJOR = re.sub(r"\D", "", IMPERSONATE) or "146"
CHROME_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{_CHROME_MAJOR}.0.0.0 Safari/537.36"
)

# Regex to find detail links in list/search HTML. group(1) = url, group(2) = kind discriminator.
DETAIL_LINK_REGEX = CFG.get(
    "detail_link_regex",
    r'href="([^"]*?/detail\?id=[\w=%]+)"'
)
# Maps the discriminator captured in group(2) to a kind label stored in DB.
KIND_MAP = CFG.get("kind_map", {})


def search_url(query: str, year_or_param: str) -> str:
    """Build the per-query search URL."""
    return BASE + SEARCH_URL_PATH.format(q=query, year=year_or_param)


def detail_referer() -> str:
    return BASE + DETAIL_REFERER_PATH


def list_url(start: str, end: str, page: int | None = None) -> str:
    """Build list URL for a date range. Optionally append page param."""
    url = BASE + LIST_URL_PATH.format(start=start, end=end)
    if page is not None:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{LIST_PAGE_PARAM}={page}"
    return url
