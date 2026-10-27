import requests
# requests
# headers
# cookies
# robots.txt
# sitemap.xml
# status code
# response

def scan_http(target):
    response = requests.get(target, timeout=5)

    # BASICS
    print("Status:", response.status_code)
    print("URL:", response.url)
    print("Body length:", len(response.text))

    # HEADERS
    headers = dict(response.headers)

    # COOKIES
    cookies = response.cookies.get_dict()
    
    # ROBOTS
    try:
        robots = requests.get(
            f"{target}/robots.txt",
            timeout=5
        )
        print("\nrobots.txt:", robots.status_code)
        if robots.ok:
            print(robots.text)

    except requests.RequestException as e:
        print("robots.txt error:", e)

    # SITEMAP
    try: 
        sitemap = requests.get(
            f"{target}/sitemap.xml",
            timeout=5
        )
        print("\nsitemap.txt:", sitemap.status_code)
        if sitemap.ok:
            print(sitemap.text)

    except requests.RequestException as e:
        print("sitemap.xml error:", e)

    #RETURN
    return {
        "status": response.status_code,
        "url": response.url,
        "body_length": len(response.text),
        "headers": headers,
        "cookies": cookies,
    }

result = scan_http("https://example.com")
print(result)