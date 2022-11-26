#!/usr/bin/env python3

import os
import uuid
from mastodon import Mastodon

if __name__ == "__main__":
    url = os.argv[1:]
    Mastodon.create_app(
        "twitter2mastodon" + str(uuid.uuid4()),
        api_base_url=url,
        to_file="twitter2mastodon.secret",
    )
