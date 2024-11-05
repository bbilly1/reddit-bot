"""scrape for comments matching keywords"""

import re
from datetime import datetime
from os import environ
from time import sleep

from bs4 import BeautifulSoup
from requests import Response
from src.base import Discord, Reddit
from src.static_types import RedditComment, RedditPost


class CommentSearchScraper(Reddit):
    """scrape comments from search page"""

    DB_TABLE: str = "comments"

    def __init__(self, first_setup: bool = False):
        self.first_setup: bool = first_setup
        self.new_comments: list[RedditComment] = []

    def get_new(self) -> None:
        """get new comments"""
        urls: list[str] = self.build_urls()

        for url in urls:
            html: Response = self.make_request(url)
            self.parse_raw_comments(html.text)
            self.send_notifications()
            sleep(5)

    def build_urls(self) -> list[str]:
        """build urls for all keywords to scrape"""
        urls: list[str] = []
        for keyword in self.build_keywords():
            url: str = f"{self.BASE}/search/?q={keyword}&type=comment&sort=new"
            urls.append(url)

        subreddit = environ.get("SUB_REDDIT")
        if subreddit:
            urls.append(f"https://www.reddit.com/{subreddit}/search/?q=&type=comment&sort=new")

        return urls

    def parse_raw_comments(self, text: str) -> None:
        """extract raw comments from text"""
        soup = BeautifulSoup(text, "html.parser")
        all_comments = soup.find_all("faceplate-tracker", {"data-testid": "search-comment"})

        for comment in all_comments:
            comment_parsed = self.parse_comment(comment)
            if not comment_parsed:
                return

            self.new_comments.append(comment_parsed)

    def parse_comment(self, comment) -> RedditComment | None:
        """extract comment fields from bs4 object"""
        author = comment.find("a", href=re.compile("/user/*"))
        if author:
            author_name: str = author.text
            author_link: str | bool = self.BASE + author.get("href")
        else:
            author_name = "[deleted]"
            author_link = False

        if author_name == "AutoModerator":
            return None

        title = comment.find("faceplate-tracker")
        time_stamp = datetime.fromisoformat(comment.find("faceplate-timeago").get("ts"))
        time_stamp_text = time_stamp.replace(microsecond=0).isoformat(" ")
        subreddit = comment.find("faceplate-hovercard").get("aria-label")
        comment_link = self.BASE + [i for i in comment.find_all("a") if i.text == "Go To Thread"][0].get("href")
        comment_text = comment.find("span", id=re.compile("comment-content-[0-9]*")).text.strip()

        if self.link_is_notified(comment_link):
            return None

        comment_parsed: RedditComment = {
            "author_link": author_link,
            "author_name": author_name,
            "post_title": title.text,
            "post_link": self.BASE + title.find("a").get("href"),
            "time_stamp": time_stamp,
            "time_stamp_text": time_stamp_text,
            "subreddit": subreddit,
            "comment_link": comment_link,
            "comment_text": comment_text,
        }

        return comment_parsed

    def link_is_notified(self, comment_link: str) -> bool:
        """check if link was already notified before"""
        exists = self.exists(self.DB_TABLE, "comment_link", comment_link)

        return exists

    def send_notifications(self) -> None:
        """send notifications new comments"""
        for comment in self.new_comments:
            link: str = comment["comment_link"]
            if self.link_is_notified(link):
                continue

            print(f"[comment][archive]: {link}")
            self.insert_into(self.DB_TABLE, comment)

            if self.first_setup and comment != self.new_comments[0]:
                continue

            print(f"[comment][notify]: {link}")
            Discord(comment).send_hook()

        if not self.new_comments:
            print("[comment] no new mentions found")


class ReditPost(Reddit):
    """handle all redit post"""

    DB_TABLE: str = "posts"

    def __init__(self, first_setup: bool = False):
        self.first_setup: bool = first_setup
        self.new_posts: list[RedditPost] = []

    def get_new(self) -> None:
        """get new comments"""
        urls = self.build_urls()

        for url in urls:
            response: Response = self.make_request(url)
            self.parse_posts(response)
            self.send_notifications()
            sleep(5)

    def build_urls(self) -> list[str]:
        """build urls for all keywords to scrape"""
        urls: list[str] = []
        for word in self.build_keywords():
            url: str = f"{self.BASE}/search.json?q={word}&type=link&sort=new"
            urls.append(url)

        return urls

    def parse_posts(self, response: Response) -> None:
        """add new posts"""

        for post in response.json()["data"]["children"]:
            author_name: str = post["data"]["author"]
            post_link: str = self.BASE + post["data"]["permalink"]

            if self.link_is_notified(post_link):
                continue

            utc: str = post["data"]["created_utc"]
            time_stamp, time_stamp_text = self.parse_utc_timestamp(utc)
            new_post: RedditPost = {
                "author_link": f"{self.BASE}/user/{author_name}/",
                "author_name": author_name,
                "subreddit": post["data"]["subreddit_name_prefixed"],
                "post_title": post["data"]["title"],
                "post_text": post["data"]["selftext"],
                "post_link": post_link,
                "time_stamp": time_stamp,
                "time_stamp_text": time_stamp_text,
            }

            self.new_posts.append(new_post)

    def link_is_notified(self, post_link: str) -> bool:
        """check if link was already notified before"""

        return self.exists(self.DB_TABLE, "post_link", post_link)

    def send_notifications(self) -> None:
        """send notifications new comments"""
        for post in self.new_posts:
            link: str = post["post_link"]
            print(f"[post][archive]: {link}")
            self.insert_into(self.DB_TABLE, post)

            if self.first_setup and post != self.new_posts[0]:
                continue

            print(f"[post][notify]: {link}")
            Discord(post).send_hook()

        if not self.new_posts:
            print("[post] no new mentions found")
