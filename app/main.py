#!/usr/bin/env python
"""application entry point"""

try:
    from dotenv import load_dotenv

    print("load local .env file")
    load_dotenv(".env")
except ModuleNotFoundError:
    pass


from src.base import Database
from src.reddit import CommentSearchScraper, ReditPost


def setup_database() -> bool:
    """setup empty database with tables"""
    db_handler = Database()
    first_setup: bool = db_handler.validate()
    db_handler.finish()

    return first_setup


def get_new_comments(first_setup: bool) -> None:
    """get new comments from reddit"""
    CommentSearchScraper(first_setup).get_new()
    ReditPost(first_setup).get_new()


# entry point
if __name__ == "__main__":
    FIRST_SETUP: bool = setup_database()
    get_new_comments(FIRST_SETUP)
