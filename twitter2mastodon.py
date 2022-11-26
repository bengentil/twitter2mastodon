#!/usr/bin/env python3

# Script to migrate Twitter following users to Mastodon
# Copyright 2022 Benjamin Gentil

import argparse
import json
import logging
import os
import re
import sys

import tweepy
from mastodon import Mastodon

# log to stderr
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr
)

TWITTER_FOLLOWING_CACHE = "twitter_{username}_following.json"


def get_twitter_following_users(username, bearer_token, no_cache=False):
    if not no_cache and os.path.exists(
        TWITTER_FOLLOWING_CACHE.format(username=username)
    ):
        with open(TWITTER_FOLLOWING_CACHE.format(username=username), "r") as f:
            return json.load(f)

    if bearer_token == "":
        raise ValueError("Twitter Bearer token is required")
    client = tweepy.Client(bearer_token)
    userid = client.get_user(username=username).data.get("id")

    # Get Twitter following users
    users = []
    for twitter_user in tweepy.Paginator(
        client.get_users_following,
        userid,
        user_fields=["username", "name", "description"],
        max_results=1000,
    ).flatten():
        users.append(
            {
                "username": twitter_user.data.get("username"),
                "name": twitter_user.data.get("name"),
                "description": twitter_user.data.get("description"),
            }
        )

    # Cache Twitter following users
    with open(TWITTER_FOLLOWING_CACHE.format(username=username), "w") as f:
        json.dump(users, f)

    return users


def get_mastodon_user_from_twitter_user(twitter_user):
    for k in twitter_user.keys():
        m = re.search(r"(@[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+)", twitter_user[k])
        if m:
            mastodon_username = m.group(1)
            if mastodon_username.endswith("."):
                mastodon_username = mastodon_username[:-1]
            logging.debug(
                f"@{twitter_user['username']} is {mastodon_username}"
            )

            return mastodon_username


def get_mastodon_following_users(api, user_id):
    first_page = api.account_following(user_id)
    all_pages = api.fetch_remaining(first_page)

    for user in all_pages:
        yield user


def follow_mastodon_users(
    to_follow=[], mastodon_username="", mastodon_password="", mastodon_client_id=""
):
    if mastodon_username == "":
        raise ValueError("Mastodon username is required")
    if mastodon_password == "":
        raise ValueError("Mastodon password is required")
    if mastodon_client_id == "":
        raise ValueError("Mastodon client ID is required")

    # Authenticate to Mastodon
    mastodon_api = Mastodon(
        client_id=mastodon_client_id,
    )
    mastodon_api.log_in(
        mastodon_username,
        mastodon_password,
    )

    # Get Mastodon following users
    user = mastodon_api.account_verify_credentials()
    instance = mastodon_api.instance().uri
    mastodon_api.account_following(user.id)
    mastodon_following_users = [
        "@" + u["acct"] for u in get_mastodon_following_users(mastodon_api, user.id)
    ]

    def is_following(user):
        return user in mastodon_following_users or (
            user.endswith("@" + instance)
            and user[: -len(instance) - 1] in mastodon_following_users
        )

    logging.debug(f"currently following {len(mastodon_following_users)} Mastodon users")

    # Dumping Mastodon following users
    with open("mastodon_following.json", "w") as f:
        json.dump(mastodon_following_users, f)

    for mastodon_user in to_follow:
        if is_following(mastodon_user):
            logging.debug(f"Already following Mastodon user {mastodon_user}")
            continue

        logging.debug(f"Looking for Mastodon user {mastodon_user}")
        res = mastodon_api.account_search(q=mastodon_user)
        if len(res) > 0:
            account = res[0]
            if "moved" in account and account["moved"] is not None:
                logging.debug(
                    f"Mastodon user {mastodon_user} has moved to {account['moved']['acct']}"
                )
                account = account["moved"]
                if is_following("@" + account["acct"]):
                    logging.info(
                        f"Already following Mastodon user {account['acct']} (was {mastodon_user})"
                    )
                    continue

            if account["locked"]:
                logging.info(
                    f"Mastodon user {mastodon_user} is locked, please follow manually"
                )
                continue

            logging.info(f"Following Mastodon user @{account['acct']} ...")
            try:
                mastodon_api.account_follow(account["id"])
            except Exception as e:
                logging.error(
                    f"Error while following Mastodon user {mastodon_user}: {e}"
                )
                logging.debug(account)
                continue
        else:
            logging.error(f"Mastodon user {mastodon_user} not found")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Twitter following users to Mastodon"
    )
    parser.add_argument(
        "--twitter-username",
        dest="twitter_username",
        help="Twitter username",
        default=os.getenv("TWITTER_USERNAME", "benjamin_gentil"),
    )
    parser.add_argument(
        "--twitter-bearer-token",
        dest="twitter_bearer_token",
        help="Twitter Bearer token",
        default=os.getenv("TWITTER_BEARER_TOKEN", ""),
    )
    parser.add_argument(
        "--mastodon-username",
        dest="mastodon_username",
        help="Mastodon username",
        default=os.getenv("MASTODON_USERNAME", ""),
    )
    parser.add_argument(
        "--mastodon-password",
        dest="mastodon_password",
        help="Mastodon password",
        default=os.getenv("MASTODON_PASSWORD", ""),
    )
    parser.add_argument(
        "--mastodon-client-id",
        dest="mastodon_client_id",
        help="Mastodon client ID",
        default=os.getenv("MASTODON_CLIENT_ID", "twitter2mastodon.secret"),
    )
    parser.add_argument(
        "--to-follow",
        dest="to_follow",
        required=False,
        help="File containing Mastodon users to follow",
    )
    parser.add_argument(
        "--no-follow",
        dest="no_follow",
        default=False,
        action="store_true",
        help="Just print Mastodon users to follow to stdout",
    )
    parser.add_argument(
        "--no-cache",
        dest="no_cache",
        default=False,
        action="store_true",
        help="Do not cache Twitter following users",
    )
    parser.add_argument(
        "--debug", dest="debug", default=False, action="store_true", help="Debug mode"
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    mastodon_users = []
    if args.to_follow is None:
        twitter_following_users = get_twitter_following_users(
            args.twitter_username, args.twitter_bearer_token, args.no_cache
        )

        for twitter_user in twitter_following_users:
            mastodon_user = get_mastodon_user_from_twitter_user(twitter_user)
            if mastodon_user is not None:
                mastodon_users.append(mastodon_user)
    else:
        with open(args.to_follow, "r") as f:
            mastodon_users = json.load(f)

    if args.no_follow:
        print(json.dumps(mastodon_users))
    else:
        follow_mastodon_users(
            mastodon_users,
            args.mastodon_username,
            args.mastodon_password,
            args.mastodon_client_id,
        )


if __name__ == "__main__":
    main()
