"""base class for reddit"""

import sqlite3
import urllib.parse
from datetime import datetime
from hashlib import md5
from os import environ
from typing import Any

import requests
from src.static_types import DiscordAuthor, DiscordEmbed, DiscordHook, RedditComment, RedditPost


class Reddit:
    """base config class"""

    BASE: str = "https://www.reddit.com"
    HEADERS: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"  # noqa
    }

    def build_keywords(self) -> list[str]:
        """get keywords from environ"""
        keywords: str = environ["KEYWORDS"]
        keywords_encoded: list[str] = []

        for keyword in keywords.split(","):
            keyword_clean: str = keyword.strip()
            if len(keyword_clean.split()) > 1:
                keyword_clean = f'"{keyword}"'

            query_encoded: str = urllib.parse.quote(keyword_clean)
            keywords_encoded.append(query_encoded)

        return keywords_encoded

    def parse_utc_timestamp(self, utc: str) -> tuple[int, str]:
        """return utc text"""
        time_stamp: int = int(utc)
        time_stamp_iso: str = datetime.fromtimestamp(time_stamp).isoformat()
        time_stamp_text: str = time_stamp_iso.replace("T", " ")

        return time_stamp, time_stamp_text

    def make_request(self, url: str) -> requests.Response:
        """make request to reddit"""
        response: requests.Response = requests.get(url, headers=self.HEADERS, timeout=10)
        if not response.ok:
            print(f"request failed: {response.status_code}")
            raise ValueError

        return response

    @staticmethod
    def insert_into(table: str, dictionary: RedditComment | RedditPost | dict):
        """build query"""
        keys: str = ":" + ", :".join(dictionary)
        to_execute: str = f"INSERT INTO {table} VALUES ({keys})"

        db_handler = Database()
        db_handler.execute(to_execute, values=list(dictionary.values()))
        db_handler.finish()

    @staticmethod
    def exists(table: str, key: str, value: str) -> bool:
        """check if link in table exists"""
        to_execute = f"""
            SELECT
                {key}
            FROM
                {table}
            WHERE
                {key} = '{value}';
        """
        db_handler = Database()
        db_handler.execute(to_execute)
        result = db_handler.fetchone()
        db_handler.finish()

        return bool(result)


class Discord:
    """interact with discord hooks"""

    HOOK_URL: str = environ["DISCORD_HOOK"]

    def __init__(self, data: Any):
        self.data = data

    def send_hook(self) -> None:
        """build send the hook"""
        hook_data: DiscordHook = self.build_hook()
        self.make_request(hook_data)

    def build_hook(self) -> DiscordHook:
        """build discord hook from data"""
        embeds: DiscordEmbed = {
            "author": self._build_author(),
            "title": self._parse_title(),
            "url": self._build_url(),
            "description": self._build_desc(),
            "color": self._get_color(),
            "footer": self._build_footer(),
        }

        hook_data: DiscordHook = {"embeds": [embeds]}

        return hook_data

    def _build_author(self) -> DiscordAuthor:
        """build author object from data"""
        author: DiscordAuthor = {
            "name": self.data["author_name"],
            "url": self.data.get("author_link", False),
        }

        return author

    def _parse_title(self) -> str:
        """build title"""
        if "comment_link" in self.data:
            title = "[New comment]: " + self.data["post_title"]
        else:
            title = "[New post]: " + self.data["post_title"]

        return title

    def _build_url(self) -> str:
        """return comment or post url"""
        return self.data.get("comment_link") or self.data["post_link"]

    def _build_desc(self) -> str:
        """build description"""
        text: str = self.data.get("comment_text") or self.data["post_text"]
        description: str = text[:500].rsplit(" ", 1)[0] + " ..."

        return description

    def _get_color(self) -> int:
        """build color hash"""
        link = self.data["post_link"]
        hex_str = md5(link.encode("utf-8")).hexdigest()[:6].encode()
        discord_col = int(hex_str, 16)
        return discord_col

    def _build_footer(self) -> dict[str, str]:
        """build footer"""
        subreddit = self.data.get("subreddit")
        time_stamp = self.data.get("time_stamp_text")
        footer = {"text": f"{subreddit} | {time_stamp}"}

        return footer

    def make_request(self, hook_data: DiscordHook) -> None:
        """send hook to discord"""
        response = requests.post(f"{self.HOOK_URL}?wait=true", json=hook_data, timeout=10)
        if not response.ok:
            print(response.json())


class Database:
    """handle all database actions"""

    DB_FILE: str = "/data/history.db"

    def __init__(self):
        self.conn = sqlite3.connect(self.DB_FILE)
        self.cursor = self.conn.cursor()

    def validate(self) -> bool:
        """make sure expected tables are there"""
        all_tables_query = """
            SELECT
                name
            FROM
                sqlite_schema
            WHERE
                type ='table' AND
                name NOT LIKE 'sqlite_%';
        """
        self.execute(all_tables_query)
        all_tables: list = self.fetchall()
        if not all_tables:
            print(f"[db] setup new database {self.DB_FILE}")
            self.setup()

        return not bool(all_tables)

    def setup(self) -> None:
        """setup empty database"""
        comments_table: str = """
            CREATE TABLE comments (
                author_link VARCHAR(255),
                author_name VARCHAR(255),
                post_title text,
                post_link text,
                time_stamp integer,
                time_stamp_text VARCHAR(255),
                subreddit VARCHAR(255),
                comment_link text,
                comment_text text
            );
        """
        posts_table: str = """
            CREATE TABLE posts (
                author_link VARCHAR(255),
                author_name VARCHAR(255),
                subreddit VARCHAR(255),
                post_title text,
                post_text text,
                post_link text,
                time_stamp integer,
                time_stamp_text VARCHAR(255)
            );
        """
        self.execute(comments_table)
        self.execute(posts_table)

    def execute(self, to_execute: str, values: list | bool = False) -> None:
        """execute on the cursor"""
        if values:
            self.cursor.execute(to_execute, values)
        else:
            self.cursor.execute(to_execute)

    def fetchall(self) -> list:
        """get all results"""
        return self.cursor.fetchall()

    def fetchone(self):
        """get one result"""
        return self.cursor.fetchone()

    def finish(self) -> None:
        """close all"""
        self.conn.commit()
        self.conn.close()
