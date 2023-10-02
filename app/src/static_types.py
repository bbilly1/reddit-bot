"""all static types"""

from typing import TypedDict

from typing_extensions import NotRequired


class RedditComment(TypedDict):
    """describes a reddit comment"""

    author_link: str | bool
    author_name: str
    post_title: str
    post_link: str
    post_text: NotRequired[str]
    time_stamp: int
    time_stamp_text: str
    subreddit: str | bool
    comment_link: str
    comment_text: str


class RedditPost(TypedDict):
    """describes a reddit post"""

    author_link: str
    author_name: str
    subreddit: str
    post_title: str
    post_text: str
    post_link: str
    time_stamp: int
    time_stamp_text: str


class DiscordAuthor(TypedDict):
    """describes an author object"""

    name: str
    url: str | bool


class DiscordEmbed(TypedDict):
    """describes a list item discord hook"""

    author: DiscordAuthor | bool
    title: str
    url: str
    description: str
    color: int
    footer: dict[str, str]


class DiscordHook(TypedDict):
    """describes a discord hook"""

    embeds: list[DiscordEmbed]
