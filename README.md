# twitter2mastodon

A script to search for mastodon handle in twitter following list (name & bio) and follow them on mastodon.

## Usage

### Create a twitter app

Go to https://apps.twitter.com/ and create a new app.

### Create a mastodon app

Run
```bash
./create_mastodon_app.py <mastodon_instance_url>
```

### Declare your twitter and mastodon credentials

Declare the following environment variables:
- TWITTER_BEARER_TOKEN
- MASTODON_USERNAME
- MASTODON_PASSWORD

### Run

```bash
$ virtualenv -p python3 .venv
$ pip install -r requirements.txt
$ ./twitter2mastodon.py
```

