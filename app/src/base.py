"""base class for reddit"""

import sqlite3
import urllib.parse
from datetime import datetime
from hashlib import md5
from os import environ
from typing import Any

import requests
from src.static_types import (
    DiscordAuthor,
    DiscordEmbed,
    DiscordHook,
    RedditComment,
    RedditPost,
)


class Reddit:
    """base config class"""

    BASE: str = "https://www.reddit.com"
    HEADERS: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",  # noqa
        "Cookie": f'reddit_session={environ.get("REDDIT_SESSION", "12341234%2Cxxxxxxxxxxxxxxxxxxxxxxx%2Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")}',  # noqa
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
        keys = ", ".join(dictionary.keys())
        placeholders = ", ".join([f":{k}" for k in dictionary.keys()])
        to_execute = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"

        db_handler = Database()
        db_handler.execute(to_execute, dict(dictionary))
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
            "url": self.data.get("author_link", None),
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

    DB_FILE: str = environ.get("DB_FILE", "/data/history.db")

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
        if all_tables:
            # migrations
            self.add_column_if_not_exists("comments", "author_img", "VARCHAR(255)")
        else:
            print(f"[db] setup new database {self.DB_FILE}")
            self.setup()

        return not bool(all_tables)

    def setup(self) -> None:
        """setup empty database"""
        comments_table: str = """
            CREATE TABLE comments (
                author_link VARCHAR(255),
                author_name VARCHAR(255),
                author_img VARCHAR(255),
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

    def add_column_if_not_exists(self, table_name: str, column_name: str, column_type, default=None):
        """add column if needed"""
        self.execute(f"PRAGMA table_info({table_name});")
        columns = [info[1] for info in self.cursor.fetchall()]

        if column_name not in columns:
            print(f"[db] adding column '{column_name}' to table '{table_name}'")
            if default is not None:
                self.cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT ?;", (default,)
                )
            else:
                self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")

    def execute(self, to_execute: str, values: list | dict | bool = False) -> None:
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
