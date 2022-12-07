"""scrape for comments matching keywords"""

from time import sleep
from os import environ

from bs4 import BeautifulSoup

from src.base import Discord, Reddit


class CommentSearchScraper(Reddit):
    """scrape comments from search page"""

    DB_TABLE = "comments"

    def __init__(self, first_setup=False):
        self.first_setup = first_setup
        self.new_comments = False

    def get_new(self):
        """get new comments"""
        url = self.build_url()
        html = self.make_request(url)
        self.parse_raw_comments(html.text)
        self.send_notifications()

    def build_url(self):
        """build url to scrape"""
        query_encoded = self.build_keywords()
        url = f"{self.BASE}/search/?q={query_encoded}&type=comment&sort=new"

        return url

    def parse_raw_comments(self, text):
        """extract raw comments from text"""
        soup = BeautifulSoup(text, "html.parser")
        all_comments = soup.find_all("div", {"data-click-id": "background"})

        self.new_comments = []

        for comment in all_comments:
            author = comment.find("a", {"data-testid": "comment_author_icon"})
            author_name = author.get("href").strip("/").split("/")[1]
            if author_name == "AutoModerator":
                continue

            post = comment.find("a", {"data-click-id": "body"})
            time_stamp = comment.find(
                "a", {"data-testid": "comment_timestamp"}
            )
            comment_link = time_stamp.get("href").split("?")[0]
            text = comment.find("div", {"data-testid": "comment"}).text
            subreddit = "/".join(post.get("href").split("/")[1:3])

            is_notified = self.link_is_notified(comment_link)
            if is_notified:
                continue

            time_stamp, time_stamp_text = self.get_timestamp(comment_link)

            self.new_comments.append(
                {
                    "author_link": self.BASE + author.get("href"),
                    "author_name": author_name,
                    "post_title": post.text,
                    "post_link": self.BASE + post.get("href"),
                    "time_stamp": time_stamp,
                    "time_stamp_text": time_stamp_text,
                    "subreddit": subreddit,
                    "comment_link": comment_link,
                    "comment_text": text,
                }
            )
            sleep(1)

    def get_timestamp(self, link):
        """get timestamp from API"""
        api_link = link.rstrip("/") + ".json"
        response = self.make_request(api_link)
        utc = response.json()[0]["data"]["children"][0]["data"]["created_utc"]
        time_stamp, time_stamp_text = self.parse_utc_timestamp(utc)

        return time_stamp, time_stamp_text

    def link_is_notified(self, comment_link):
        """check if link was already notified before"""
        exists = self.exists(self.DB_TABLE, "comment_link", comment_link)

        return exists

    def send_notifications(self):
        """send notifications new comments"""
        for comment in self.new_comments:
            link = comment["comment_link"]
            if self.first_setup and comment == self.new_comments[0]:
                print(f"[comment][notify]: {link}")
                Discord(comment).send_hook()

            self.insert_into(self.DB_TABLE, comment)
            print(f"[comment][archive]: {link}")

        if not self.new_comments:
            print("[comment] no new mentions found")


class SubReddit(Reddit):
    """get new comments from subreddit comments API"""

    SUB_REDDIT = environ.get("SUB_REDDIT")
    DB_TABLE = "comments"

    def __init__(self, first_setup=False):
        self.first_setup = first_setup
        self.new_comments = False

    def get_new(self):
        """get new comments"""
        url = f"{self.BASE}/{self.SUB_REDDIT}/comments.json"
        response = self.make_request(url)
        self.parse_comments(response)
        self.send_notifications()

    def parse_comments(self, response):
        """build comments list"""
        all_comments = response.json()["data"]["children"]
        self.new_comments = []

        for comment in all_comments:
            author_name = comment["data"]["author"]
            comment_link = self.BASE + comment["data"]["permalink"]

            is_notified = self.link_is_notified(comment_link)
            if is_notified:
                continue

            utc = comment["data"]["created_utc"]
            time_stamp, time_stamp_text = self.parse_utc_timestamp(utc)

            self.new_comments.append(
                {
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
            )

    def link_is_notified(self, comment_link):
        """check if link was already notified before"""
        exists = self.exists(self.DB_TABLE, "comment_link", comment_link)

        return exists

    def send_notifications(self):
        """send notifications new comments"""
        for comment in self.new_comments:
            link = comment["comment_link"]
            if self.first_setup and comment == self.new_comments[0]:
                print(f"[comment][notify]: {link}")
                Discord(comment).send_hook()

            self.insert_into(self.DB_TABLE, comment)
            print(f"[comment][archive]: {link}")

        if not self.new_comments:
            print("[comment] no new items in subreddit found")


class ReditPost(Reddit):
    """handle all redit post"""

    DB_TABLE = "posts"

    def __init__(self, first_setup=False):
        self.first_setup = first_setup
        self.new_posts = False

    def get_new(self):
        """get new posts from reddit"""
        url = self.build_url()
        response = self.make_request(url)
        self.parse_posts(response)
        self.send_notifications()

    def build_url(self):
        """return url"""
        query_encoded = self.build_keywords()
        url = f"{self.BASE}/search.json?q={query_encoded}&type=link&sort=new"

        return url

    def parse_posts(self, response):
        """add new posts"""
        self.new_posts = []

        for post in response.json()["data"]["children"]:
            author_name = post["data"]["author_fullname"]
            post_link = self.BASE + post["data"]["permalink"]

            is_notified = self.link_is_notified(post_link)
            if is_notified:
                continue

            utc = post["data"]["created_utc"]
            time_stamp, time_stamp_text = self.parse_utc_timestamp(utc)

            self.new_posts.append(
                {
                    "author_link": f"{self.BASE}/user/{author_name}/",
                    "author_name": author_name,
                    "subreddit": post["data"]["subreddit_name_prefixed"],
                    "post_title": post["data"]["title"],
                    "post_text": post["data"]["selftext"],
                    "post_link": post_link,
                    "time_stamp": time_stamp,
                    "time_stamp_text": time_stamp_text,
                }
            )

    def link_is_notified(self, post_link):
        """check if link was already notified before"""
        exists = self.exists(self.DB_TABLE, "post_link", post_link)

        return exists

    def send_notifications(self):
        """send notifications new comments"""
        for post in self.new_posts:
            link = post["post_link"]
            if self.first_setup and post == self.new_posts[0]:
                print(f"[post][notify]: {link}")
                Discord(post).send_hook()

            self.insert_into(self.DB_TABLE, post)
            print(f"[post][archive]: {link}")

        if not self.new_posts:
            print("[post] no new mentions found")
