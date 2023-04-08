# Reddit - Discord Bot
*Monitor Reddit for keywords*

## About this project
There aren't really any plans to further develop this little script. This was a lazy afternoon project automating some specific repetitive task. I open sourced it in the hopes others might find this useful, but don't expect any support or feature developments. If you want to contribute, I'm happy to look at your PR. When in doubt if your idea will be a good fit, reach out first.

## Core Functionality
- Send Discord notifications on events
- Monitor a single Subreddit, notify all comments
- Monitor all of Reddit for any keyword mentions in comments or post

## Setup
Needs a volume at `/data` to store a sqlite database with notifications sent.

Configure the following environment variables
- **SUB_REDDIT**: Name of the subreddit to monitor, e.g. `r/TubeArchivist`
- **KEYWORDS**: Comma separated list of minimal one keyword
- **DISCORD_HOOK**: Hook url to send discord notifications to

## Run
At first run, *reddit bot* will pupulate the database with past matches and send one notification of each for testing.  

After that, the bot will search for new mentions every hour.
