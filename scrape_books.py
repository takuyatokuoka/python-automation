"""books.toscrape.com から書籍情報（タイトル・価格・在庫状況）を収集する。

- robots.txt を読み込み、禁止パスへはアクセスしない
- リクエスト間に 1〜3 秒のランダム待機を挟む
- 接続エラー時はログに出力して終了する
- 結果を books_<日付>.md として保存する
"""

from __future__ import annotations

import logging
import random
import sys
import time
from datetime import date
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
START_PATH = "catalogue/page-1.html"
USER_AGENT = "python-automation-scraper/1.0 (educational; +https://github.com/takuyatokuoka/python-automation)"
REQUEST_TIMEOUT = 20
MIN_DELAY = 1.0
MAX_DELAY = 3.0

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scrape_books.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def load_robots(session: requests.Session) -> RobotFileParser:
    """robots.txt を取得してパースする。取得失敗時は全許可扱いにする。"""
    robots_url = urljoin(BASE_URL, "/robots.txt")
    parser = RobotFileParser()
    try:
        resp = session.get(robots_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        parser.parse(resp.text.splitlines())
        logger.info("robots.txt を読み込みました: %s", robots_url)
    except requests.RequestException as exc:
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


def fetch(session: requests.Session, url: str) -> requests.Response:
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    return resp


def parse_books(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    books: list[dict[str, str]] = []
    for article in soup.select("article.product_pod"):
        title_tag = article.select_one("h3 > a")
        price_tag = article.select_one(".price_color")
        stock_tag = article.select_one(".availability")
        books.append(
            {
                "title": title_tag["title"].strip() if title_tag else "(不明)",
                "price": price_tag.get_text(strip=True) if price_tag else "(不明)",
                "stock": stock_tag.get_text(strip=True) if stock_tag else "(不明)",
            }
        )
    return books


def find_next_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    next_link = soup.select_one("li.next > a")
    if not next_link:
        return None
    return urljoin(current_url, next_link["href"])


def write_markdown(books: list[dict[str, str]], pages: int) -> str:
    filename = f"books_{date.today():%Y%m%d}.md"
    lines = [
        f"# 書籍一覧（books.toscrape.com）",
        "",
        f"- 取得日: {date.today():%Y-%m-%d}",
        f"- 取得ページ数: {pages}",
        f"- 取得件数: {len(books)}",
        "",
        "| # | タイトル | 価格 | 在庫状況 |",
        "| ---: | --- | --- | --- |",
    ]
    for i, book in enumerate(books, start=1):
        title = book["title"].replace("|", "\\|")
        lines.append(f"| {i} | {title} | {book['price']} | {book['stock']} |")
    lines.append("")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filename


def main() -> int:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    robots = load_robots(session)

    all_books: list[dict[str, str]] = []
    url: str | None = urljoin(BASE_URL, START_PATH)
    page_count = 0

    try:
        while url:
            if not can_fetch(robots, url):
                break

            logger.info("取得中: %s", url)
            resp = fetch(session, url)
            page_count += 1

            books = parse_books(resp.text)
            all_books.extend(books)
            logger.info("ページ %d: %d 件取得（累計 %d 件）", page_count, len(books), len(all_books))

            next_url = find_next_url(resp.text, url)
            url = next_url
            if url:
                polite_sleep()
    except requests.ConnectionError as exc:
        logger.error("接続エラーが発生しました: %s", exc)
        return 1
    except requests.Timeout as exc:
        logger.error("タイムアウトが発生しました: %s", exc)
        return 1
    except requests.RequestException as exc:
        logger.error("リクエストエラーが発生しました: %s", exc)
        return 1

    if not all_books:
        logger.error("書籍情報を 1 件も取得できませんでした。")
        return 1

    filename = write_markdown(all_books, page_count)
    logger.info("保存しました: %s（%d 件）", filename, len(all_books))
    return 0


if __name__ == "__main__":
    sys.exit(main())
