"""base class for reddit"""

import urllib.parse
import sqlite3
from datetime import datetime
from hashlib import md5
from os import environ

import requests


class Reddit:
    """base config class"""

    BASE = "https://www.reddit.com"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'}

    def build_keywords(self):
        """get keywords from environ"""
        keywords = environ.get("KEYWORDS")
        keywords_clean = ""

        for keyword in keywords.split(","):
            keyword = keyword.strip()
            if len(keyword.split()) > 1:
                keyword = f"\"{keyword}\""

            if not keywords_clean:
                keywords_clean = keyword
            else:
                keywords_clean += f" OR {keyword}"


        query_encoded = urllib.parse.quote(keywords_clean)

        return query_encoded

    def parse_utc_timestamp(self, utc):
        """return utc text"""
        time_stamp = int(utc)
        time_stamp_iso = datetime.fromtimestamp(time_stamp).isoformat()
        time_stamp_text = time_stamp_iso.replace("T", " ")

        return time_stamp, time_stamp_text

    def make_request(self, url):
        """make request to reddit"""
        response = requests.get(url, headers=self.HEADERS, timeout=10)
        if not response.ok:
            print(f"request failed: {response.status_code}")
            raise ValueError

        return response

    @staticmethod
    def insert_into(table, dictionary):
        """build query"""
        keys = ":" + ", :".join(dictionary)
        to_execute = (f"INSERT INTO {table} VALUES ({keys})")

        db_handler = Database()
        db_handler.execute(to_execute, values=list(dictionary.values()))
        db_handler.finish()

    @staticmethod
    def exists(table, key, value):
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

    HOOK_URL = environ.get("DISCORD_HOOK")

    def __init__(self, data):
        self.data = data

    def send_hook(self):
        """build send the hook"""
        hook_data = self.build_hook()
        self.make_request(hook_data)

    def build_hook(self):
        """build discord hook from data"""
        hook_data = {
            "embeds": [
                {
                    "author": {
                        "name": self.data["author_name"],
                        "url": self.data["author_link"],
                    },
                    "title": self._parse_title(),
                    "url": self._build_url(),
                    "description": self._build_desc(),
                    "color": self._get_color(),
                    "footer": self._build_footer(),
                }
            ]
        }

        return hook_data

    def _parse_title(self):
        """build title"""
        if "comment_link" in self.data:
            title = "[New comment]: " + self.data["post_title"]
        else:
            title = "[New post]: " + self.data["post_title"]

        return title

    def _build_url(self):
        """return comment or post url"""
        return self.data.get("comment_link") or self.data.get("post_link")

    def _build_desc(self):
        """build description"""
        text = self.data.get("comment_text") or self.data.get("post_text")
        description = text[:500].rsplit(" ", 1)[0] + " ..."

        return description

    def _get_color(self):
        """build color hash"""
        link = self.data["post_link"]
        hex_str = md5(link.encode("utf-8")).hexdigest()[:6].encode()
        discord_col = int(hex_str, 16)
        return discord_col

    def _build_footer(self):
        """build footer"""
        subreddit = self.data.get("subreddit")
        time_stamp = self.data.get("time_stamp_text")

        return {
            "text": f"{subreddit} | {time_stamp}"
        }

    def make_request(self, hook_data):
        """send hook to discord"""
        response = requests.post(
            f"{self.HOOK_URL}?wait=true", json=hook_data, timeout=10
        )
        if not response.ok:
            print(response.json())


class Database:
    """handle all database actions"""

    DB_FILE = "/data/history.db"

    def __init__(self):
        self.conn = sqlite3.connect(self.DB_FILE)
        self.cursor = self.conn.cursor()

    def validate(self):
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
        all_tables = self.fetchall()
        if not all_tables:
            print(f"[db] setup new database {self.DB_FILE}")
            self.setup()

        return not bool(all_tables)

    def setup(self):
        """setup empty database"""
        comments_table = """
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
        posts_table = """
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

    def execute(self, to_execute, values=False):
        """execute on the cursor"""
        if values:
            self.cursor.execute(to_execute, values)
        else:
            self.cursor.execute(to_execute)

    def fetchall(self):
        """get all results"""
        return self.cursor.fetchall()

    def fetchone(self):
        """get one result"""
        return self.cursor.fetchone()

    def finish(self):
        """close all"""
        self.conn.commit()
        self.conn.close()
