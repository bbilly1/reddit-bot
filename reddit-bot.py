import os
import praw
from discord_webhook import DiscordWebhook, DiscordEmbed


reddit = praw.Reddit(
  password = os.environ['password'],
  username = os.environ['username'],
  client_id = os.environ['client_id'],
  client_secret = os.environ['client_secret'],
  user_agent = "<replyComment>"
)

subreddit = reddit.subreddit("all")
webhook = DiscordWebhook(url=os.environ['webhook_url'])
keyword = os.environ['keyword']

for comment in subreddit.stream.comments(skip_existing=True):
  comment_lower = comment.body.lower()
  if keyword in comment_lower:
    comment_test = comment.permalink
    truncated_text2 = comment_lower[0:400] + "..."
    truncated_text = truncated_text2.replace("hello", "**hello**")    
    embed = DiscordEmbed(description=truncated_text, color='fe4500')
    embed.set_author(
    name="New Reddit Post",
    url="https://www.reddit.com" + comment_test,)
    webhook.add_embed(embed)
    embed.set_timestamp()

    print("https://www.reddit.com" + comment_test)
    response = webhook.execute()
