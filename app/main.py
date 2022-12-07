#!/usr/bin/env python
"""application entry point"""

from src.base import Database
from src.reddit import CommentSearchScraper, SubReddit, ReditPost


def setup_databasse():
    """setup empty database with tables"""
    db_handler = Database()
    first_setup = db_handler.validate()
    db_handler.finish()

    return first_setup


def get_new_comments(first_setup):
    """get new comments from reddit"""
    CommentSearchScraper(first_setup).get_new()
    SubReddit(first_setup).get_new()
    ReditPost(first_setup).get_new()


# entry point
if __name__ == "__main__":
    FIRST_SETUP = setup_databasse()
    get_new_comments(FIRST_SETUP)
