# Reddit - Discord Bot
*Monitor Reddit for keywords*

## Core Functionality
- Send Discord notifications on events
- Monitor a Subreddit and notify for all comments
- Monitor Reddit for any keyword mentions in comments or post

## Setup
Needs a volume at `/data` to store a sqlite database with notifications sent.

Configure the following environment variables
- **SUB_REDDIT**: Name of the subreddit to monitor, e.g. `r/TubeArchivist`
- **KEYWORDS**: Comma separated list of minimal one keyword
- **DISCORD_HOOK**: Hook url to send discord notifications to

## Run
At first run, *reddit bot* will pupulate the database will add matches and send one notification of each for testing.  

After that, the bot will search for new mentions every hour.
