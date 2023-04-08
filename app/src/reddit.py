"""scrape for comments matching keywords"""

from time import sleep
from os import environ

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

    def build_urls(self) -> list:
        """build urls for all keywords to scrape"""
        urls: list = []
        for keyword in self.build_keywords():
            url: str = f"{self.BASE}/search/?q={keyword}&type=comment&sort=new"
            urls.append(url)

        return urls

    def parse_raw_comments(self, text: str) -> None:
        """extract raw comments from text"""
        soup = BeautifulSoup(text, "html.parser")
        all_comments = soup.find_all("div", {"data-click-id": "background"})

        for comment in all_comments:
            author = comment.find("a", {"data-testid": "comment_author_icon"})
            if author:
                author_name: str = author.get("href").strip("/").split("/")[1]
                author_link: str | bool = self.BASE + author.get("href")
            else:
                author_name = "[deleted]"
                author_link = False

            if author_name == "AutoModerator":
                continue

            post = comment.find("a", {"data-click-id": "body"})
            time_stamp = comment.find(
                "a", {"data-testid": "comment_timestamp"}
            )
            comment_link: str = time_stamp.get("href").split("?")[0]
            comment_text: str = comment.find("div", {"data-testid": "comment"}).text
            subreddit: str = "/".join(post.get("href").split("/")[1:3])

            if self.link_is_notified(comment_link):
                continue

            time_stamp, time_stamp_text = self.get_timestamp(comment_link)

            comment_parsed: RedditComment = {
                "author_link": author_link,
                "author_name": author_name,
                "post_title": post.text,
                "post_link": self.BASE + post.get("href"),
                "time_stamp": time_stamp,
                "time_stamp_text": time_stamp_text,
                "subreddit": subreddit,
                "comment_link": comment_link,
                "comment_text": comment_text,
            }
            self.new_comments.append(comment_parsed)
            sleep(1)

    def get_timestamp(self, link: str) -> tuple[int, str]:
        """get timestamp from API"""
        api_link = link.rstrip("/") + ".json"
        response = self.make_request(api_link)
        utc = response.json()[0]["data"]["children"][0]["data"]["created_utc"]
        time_stamp, time_stamp_text = self.parse_utc_timestamp(utc)

        return time_stamp, time_stamp_text

    def link_is_notified(self, comment_link: str) -> bool:
        """check if link was already notified before"""
        exists = self.exists(self.DB_TABLE, "comment_link", comment_link)

        return exists

    def send_notifications(self) -> None:
        """send notifications new comments"""
        for comment in self.new_comments:
            link: str = comment["comment_link"]
            print(f"[comment][archive]: {link}")
            self.insert_into(self.DB_TABLE, comment)

            if self.first_setup and comment != self.new_comments[0]:
                continue

            print(f"[comment][notify]: {link}")
            Discord(comment).send_hook()

        if not self.new_comments:
            print("[comment] no new mentions found")


class SubReddit(Reddit):
    """get new comments from subreddit comments API"""

    SUB_REDDIT: str | bool = environ.get("SUB_REDDIT", False)
    DB_TABLE: str = "comments"

    def __init__(self, first_setup: bool = False):
        self.first_setup: bool = first_setup
        self.new_comments: list[RedditComment] = []

    def get_new(self) -> None:
        """get new comments"""
        if not self.SUB_REDDIT:
            return

        url: str = f"{self.BASE}/{self.SUB_REDDIT}/comments.json"
        response: Response = self.make_request(url)
        self.parse_comments(response)
        self.send_notifications()

    def parse_comments(self, response) -> None:
        """build comments list"""
        all_comments: list = response.json()["data"]["children"]

        for comment in all_comments:
            author_name: str = comment["data"]["author"]
            comment_link: str = self.BASE + comment["data"]["permalink"]

            if self.link_is_notified(comment_link):
                continue

            utc: str = comment["data"]["created_utc"]
            time_stamp, time_stamp_text = self.parse_utc_timestamp(utc)
            new_comment: RedditComment = {
                "author_link": f"{self.BASE}/user/{author_name}/",
                "author_name": author_name,
                "post_title": comment["data"]["link_title"],
                "post_link": comment["data"]["link_url"],
                "time_stamp": time_stamp,
                "time_stamp_text": time_stamp_text,
                "subreddit": self.SUB_REDDIT,
                "comment_link": comment_link,
                "comment_text": comment["data"]["body"],
            }

            self.new_comments.append(new_comment)

    def link_is_notified(self, comment_link: str) -> bool:
        """check if link was already notified before"""
        return self.exists(self.DB_TABLE, "comment_link", comment_link)

    def send_notifications(self) -> None:
        """send notifications new comments"""
        for comment in self.new_comments:
            link: str = comment["comment_link"]
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
            author_name: str = post["data"]["author_fullname"]
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
