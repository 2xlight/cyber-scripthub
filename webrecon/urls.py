from urllib.parse import urlparse, urlunparse
# import asyncio
# argparse python main.py -u https://example.com -w wordlist.txt
# logging
# requests.Session()
# Type Hinting

def normalize_url(url: str) -> str:
    url = url.strip() # no " "

    if not url.startswith(("http://", "https://")): 
        url = "https://" + url # add https/https

    parsed = urlparse(url) #parse url

    scheme = parsed.scheme.lower() # text
    domain = parsed.netloc.lower() # text
    path = parsed.path.rstrip("/") # /login/ -> /login

    return urlunparse((
        scheme, # https
        domain, # google.com
        path, # /login
        "", #no old params
        parsed.query, # vd: ?id=123
        "" #no #section1 
    ))

def deduplicate(urls):
    normalized = [] # like lib=""

    for url in urls:
        url = normalize_url(url) # fuction

        if url not in normalized:
            normalized.append(url) # is url in fuction?

    return normalized # return list