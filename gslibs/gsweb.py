# -*- coding: utf-8 -*-
"""
====
Custom networking functions
====

Mostly customized http request for now
"""

import platform
import socket
from bs4 import BeautifulSoup
import requests
import shutil

# set timeout to 10 seconds
socket.setdefaulttimeout(10)

# Create our own User-Agent string. We may need to fake this if a server tryes
# to mess with us.
user_agent = f"Mozilla/5.0 compatible ({platform.system()} {platform.machine()}; Novel-Indexer-Bot)"

# Start building our session
session = requests.session()
session.headers.update({"user-agent": user_agent})


# Provide a function to replace the default User-Agent:
def set_user_agent(agent: str) -> None:
    """Function to replace the default User-Agent"""
    session.headers.update({"user-agent": agent})


def quote(url: str) -> str:
    """Quote a URL to ensure compatibility with unusual caracters in them.

    Added for Wattpad2Epub, but good for everything."""
    parts = url.rsplit("/", 1)
    url = f"{parts[0]}/{requests.utils.quote(parts[1])}"
    return url


def get_url(url: str) -> str | None:
    tryes = 5
    with session as s:
        while tryes > 0:
            try:
                url = quote(url)
                response = s.get(quote(url))
                if response.status_code == 200:
                    # with open("htmllog.txt", "w") as file:
                    #     file.write(html)
                    return response.text
                else:
                    print("Status code: {response.status_code}")
                    tryes -= 1
            except socket.timeout:
                tryes -= 1
            else:
                raise SystemExit("An URL error happened: --")
    return None


def download_binary(url: str, filename: str) -> bool:
    tryes = 5
    while tryes > 0:
        try:
            url = quote(url)
            response = requests.get(url, stream=True, timeout=20)
            if response.status_code == 200:
                response.raw.decode_content = True
                with open(filename, "wb") as f:
                    shutil.copyfileobj(response.raw, f)
                return True
        except socket.timeout:
            tryes -= 1
        else:
            tryes -= 1
    return False


def get_soup(url: str) -> BeautifulSoup:
    html = get_url(url)
    # soup = BeautifulSoup(html, "lxml")
    soup = BeautifulSoup(html, features="xml")
    return soup
