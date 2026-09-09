"""quotes.toscrape.com/js から名言（テキスト・著者名）を収集する。

- JavaScript でレンダリングされるページを Playwright（Chromium, ヘッドあり）で取得
- robots.txt を読み込み、禁止パスへはアクセスしない
- リクエスト間に 1〜3 秒のランダム待機を挟む
- 接続エラー時はログに出力して終了する
- 結果を quotes_<日付>.md、スクリーンショットを quotes_<日付>.png として保存する
"""

from __future__ import annotations

import logging
import random
import sys
import time
from datetime import date
from urllib.parse import urljoin
from urllib.request import urlopen
from urllib.error import URLError
from urllib.robotparser import RobotFileParser

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://quotes.toscrape.com/"
START_URL = "https://quotes.toscrape.com/js/"
USER_AGENT = "python-automation-scraper/1.0 (educational; +https://github.com/takuyatokuoka/python-automation)"
NAV_TIMEOUT = 30_000
MIN_DELAY = 1.0
MAX_DELAY = 3.0

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scrape_quotes.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def load_robots() -> RobotFileParser:
    """robots.txt を取得してパースする。取得失敗時は全許可扱いにする。"""
    robots_url = urljoin(BASE_URL, "/robots.txt")
    parser = RobotFileParser()
    try:
        with urlopen(robots_url, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        parser.parse(content.splitlines())
        logger.info("robots.txt を読み込みました: %s", robots_url)
    except URLError as exc:
        logger.warning("robots.txt を取得できませんでした (%s)。全パス許可として続行します。", exc)
        parser.parse([])
    return parser


def can_fetch(parser: RobotFileParser, url: str) -> bool:
    allowed = parser.can_fetch(USER_AGENT, url)
    if not allowed:
        logger.warning("robots.txt により禁止: %s", url)
    return allowed


def polite_sleep() -> None:
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    logger.info("待機 %.2f 秒", delay)
    time.sleep(delay)


def scrape(page, url: str) -> tuple[list[dict[str, str]], str | None]:
    page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT)
    page.wait_for_selector(".quote", timeout=NAV_TIMEOUT)

    quotes: list[dict[str, str]] = []
    for el in page.query_selector_all(".quote"):
        text_el = el.query_selector(".text")
        author_el = el.query_selector(".author")
        quotes.append(
            {
                "text": (text_el.inner_text().strip() if text_el else "(不明)"),
                "author": (author_el.inner_text().strip() if author_el else "(不明)"),
            }
        )

    next_el = page.query_selector("li.next > a")
    next_url = urljoin(url, next_el.get_attribute("href")) if next_el else None
    return quotes, next_url


def write_markdown(quotes: list[dict[str, str]], pages: int) -> str:
    filename = f"quotes_{date.today():%Y%m%d}.md"
    lines = [
        "# 名言一覧（quotes.toscrape.com/js）",
        "",
        f"- 取得日: {date.today():%Y-%m-%d}",
        f"- 取得ページ数: {pages}",
        f"- 取得件数: {len(quotes)}",
        "",
        "| # | 名言 | 著者 |",
        "| ---: | --- | --- |",
    ]
    for i, q in enumerate(quotes, start=1):
        text = q["text"].replace("|", "\\|").replace("\n", " ")
        author = q["author"].replace("|", "\\|")
        lines.append(f"| {i} | {text} | {author} |")
    lines.append("")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filename


def main() -> int:
    robots = load_robots()

    all_quotes: list[dict[str, str]] = []
    page_count = 0
    screenshot_name = f"quotes_{date.today():%Y%m%d}.png"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            url: str | None = START_URL
            while url:
                if not can_fetch(robots, url):
                    break

                logger.info("取得中: %s", url)
                quotes, next_url = scrape(page, url)
                page_count += 1
                all_quotes.extend(quotes)
                logger.info(
                    "ページ %d: %d 件取得（累計 %d 件）", page_count, len(quotes), len(all_quotes)
                )

                if page_count == 1:
                    page.screenshot(path=screenshot_name, full_page=True)
                    logger.info("スクリーンショットを保存しました: %s", screenshot_name)

                url = next_url
                if url:
                    polite_sleep()

            browser.close()
    except PlaywrightTimeoutError as exc:
        logger.error("タイムアウトが発生しました: %s", exc)
        return 1
    except PlaywrightError as exc:
        # ネットワーク到達不可（ERR_CONNECTION_*, ERR_NAME_NOT_RESOLVED 等）を含む
        logger.error("接続エラーが発生しました: %s", exc)
        return 1

    if not all_quotes:
        logger.error("名言を 1 件も取得できませんでした。")
        return 1

    filename = write_markdown(all_quotes, page_count)
    logger.info("保存しました: %s（%d 件） / %s", filename, len(all_quotes), screenshot_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
