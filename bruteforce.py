from __future__ import annotations
import sys
import argparse
import time
import requests
import dns.resolver
import dns.exception
import asyncio
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import aiohttp
import dns.asyncresolver
import dns.exception

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389, 8080, 8443]
CRAWL_CONCURRENCY = 5      # số trang crawl cùng lúc - thấp vì đang xin phép crawl 1 site người khác
RESOLVE_CONCURRENCY = 20   # DNS query nhẹ hơn HTTP nhiều -> cho phép cao hơn
SCAN_CONCURRENCY = 50      # connect scan cũng nhẹ -> concurrency cao để quét nhanh
CONNECT_TIMEOUT = 2.0      # chờ tối đa bao lâu cho 1 lần connect port

#CHOICE 1 =======================
def build_resolver(nameservers: list[str] | None = None, timeout: float = 2.0) -> dns.resolver.Resolver:
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    if nameservers:
        resolver.nameservers = nameservers
    return resolver

def resolve_host(resolver: dns.resolver.Resolver, fqdn: str) -> list[str] | None:
    try:
        answer = resolver.resolve(fqdn, "A")
        return [str(ip) for ip in answer]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return None
    except dns.exception.Timeout:
        print(f"  [!] Timeout khi resolve {fqdn}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [!] Lỗi không xác định với {fqdn}: {type(e).__name__}", file=sys.stderr)
        return None

def detect_wildcard(resolver: dns.resolver.Resolver, domain: str) -> list[str] | None:
    probe = f"random-check-not-exist-12345.{domain}"
    return resolve_host(resolver, probe)

def load_wordlist(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def brute_force(domain: str, wordlist: list[str], resolver: dns.resolver.Resolver, wildcard_ips: list[str] | None) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    total = len(wordlist)

    for i, word in enumerate(wordlist, start=1):
        fqdn = f"{word}.{domain}"
        ips = resolve_host(resolver, fqdn)

        if ips is None:
            continue

        if wildcard_ips and set(ips) == set(wildcard_ips):
            continue

        found[fqdn] = ips
        print(f"[+] {fqdn} -> {', '.join(ips)}")

        if i % 100 == 0:
            print(f"    ... đã thử {i}/{total} từ", file=sys.stderr)

    return found

#CHOICE 2 =======================
class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return # chỉ quan tâm thẻ <a>, bỏ qua mọi thẻ khác (img, script...)
        for attr_name, attr_value in attrs: 
        # attrs là list các cặp (tên_attr, giá_trị)
            if attr_name == "href" and attr_value:
                self.links.append(attr_value) 
        # lưu href thô (có thể là link tương đối, chưa xử lý)


async def fetch_page(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status != 200:
                return None
            return await resp.text()                    # đọc toàn bộ body dạng text, tự decode theo charset trả về
    except Exception:
        return None


def normalize_links(base_url: str, raw_links: list[str]) -> set[str]:
    base_host = urlparse(base_url).netloc                 
    # lấy phần "host" của URL gốc, vd "example.com"
    result = set()
    for link in raw_links:
        if link.startswith(("#", "javascript:", "mailto:")):
            continue                                        
        # bỏ anchor nội trang / js handler / email link
        absolute = urljoin(base_url, link)                   
        # ghép link tương đối với base_url -> thành link đầy đủ
        if urlparse(absolute).netloc == base_host:            
        # chỉ giữ link CÙNG domain
            result.add(absolute)
    return result


async def crawl(start_url: str, max_pages: int = 10) -> set[str]:
    visited: set[str] = set()
    all_links: set[str] = set()
    queue: list[str] = [start_url]
    sem = asyncio.Semaphore(CRAWL_CONCURRENCY)

    async def visit_one(session: aiohttp.ClientSession, url: str) -> set[str]:
        async with sem:                                     
            # giới hạn số request HTTP đồng thời
            html = await fetch_page(session, url)
        if not html:
            return set()
        parser = LinkExtractor()
        parser.feed(html)                                    
        # đưa HTML vào parser -> tự gọi handle_starttag() bên trong
        return normalize_links(url, parser.links)

    async with aiohttp.ClientSession() as session:
        while queue and len(visited) < max_pages:
            batch = [u for u in queue if u not in visited][:CRAWL_CONCURRENCY]
            if not batch:
                break
            queue = [u for u in queue if u not in batch]      
            # bỏ batch vừa lấy ra khỏi hàng đợi
            visited.update(batch)                              
            # đánh dấu đã (sắp) thăm NGAY, tránh thăm trùng ở vòng sau

            results = await asyncio.gather(*(visit_one(session, u) for u in batch))
            for links in results:
                all_links.update(links)
                for link in links:
                    if link not in visited and link not in queue:
                        queue.append(link)                     
                        # link mới -> thêm vào hàng đợi để thăm ở vòng kế tiếp

    return all_links


    # ================= GIAI ĐOẠN 2: RESOLVE =================

async def resolve_host(resolver: dns.asyncresolver.Resolver, sem: asyncio.Semaphore,
                        hostname: str) -> tuple[str, list[str]]:
    async with sem:
        try:
            answer = await resolver.resolve(hostname, "A")     # dns.asyncresolver hỗ trợ await trực tiếp (khác dns.resolver đồng bộ)
            return hostname, [str(ip) for ip in answer]
        except (dns.exception.DNSException, Exception):
            return hostname, []                                  # NXDOMAIN/timeout/lỗi khác -> coi như không resolve được


async def resolve_all(hostnames: set[str]) -> dict[str, list[str]]:
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = 2.0
        resolver.lifetime = 2.0
        sem = asyncio.Semaphore(RESOLVE_CONCURRENCY)

        tasks = [resolve_host(resolver, sem, h) for h in hostnames]
        results = await asyncio.gather(*tasks)
        return {host: ips for host, ips in results if ips}          # chỉ giữ host resolve được (list ips không rỗng)

async def scan_port(sem: asyncio.Semaphore, ip: str, port: int) -> bool:
    async with sem:
        try:
            reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port), timeout=CONNECT_TIMEOUT
            )
            writer.close()                                     # đóng ngay, ta chỉ cần biết mở được hay không, không cần giao tiếp thêm
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False


async def scan_host(sem: asyncio.Semaphore, ip: str) -> list[int]:
        tasks = [scan_port(sem, ip, port) for port in COMMON_PORTS]  # tạo 1 task quét CHO MỖI port, chạy cùng lúc bằng gather bên dưới
        results = await asyncio.gather(*tasks)
        return [port for port, is_open in zip(COMMON_PORTS, results) if is_open]


    # ================= ORCHESTRATION =================

async def run_pipeline(start_url: str, max_pages: int = 10) -> None:
        print(f"[1/3] Crawling {start_url} (tối đa {max_pages} trang) ...")
        links = await crawl(start_url, max_pages=max_pages)
        hostnames = {urlparse(link).netloc.split(":")[0] for link in links}
        hostnames.add(urlparse(start_url).netloc.split(":")[0])       # luôn thêm chính host gốc, kể cả khi crawl không ra link nào
        print(f"      Tìm thấy {len(links)} link, {len(hostnames)} hostname khác nhau: {hostnames}")

        print(f"[2/3] Resolving {len(hostnames)} hostname ...")
        resolved = await resolve_all(hostnames)
        print(f"      Resolve được {len(resolved)}/{len(hostnames)} hostname.")

        print(f"[3/3] Scanning port trên các IP đã resolve (concurrent) ...")
        all_ips = {ip for ips in resolved.values() for ip in ips}      # gộp hết IP lại, loại trùng (nhiều host có thể chung 1 IP)
        scan_sem = asyncio.Semaphore(SCAN_CONCURRENCY)
        scan_results = dict(zip(
            all_ips,
            await asyncio.gather(*(scan_host(scan_sem, ip) for ip in all_ips))
        ))

        print("\n=== KẾT QUẢ ===")
        for host, ips in resolved.items():
            for ip in ips:
                open_ports = scan_results.get(ip, [])
                print(f"  {host:35s} {ip:15s} port mở: {open_ports if open_ports else '(không có / bị chặn)'}")

#============= MENU ==============
def subdomain_bruteforce():
    print("Running Subdomain Brute-force...")
    domain = input("> Input Domain: ").strip()
    wordlist_path = input("> Input wordlist file path: ").strip()
    ns_input = input("> Input nameserver: ").strip()
    
    nameservers = ns_input.split() if ns_input else ["8.8.8.8", "1.1.1.1"]
    timeout_input = input("> Input timeout (giây, mặc định 2.0): ").strip()
    timeout = float(timeout_input) if timeout_input else 2.0

    resolver = build_resolver(nameservers, timeout)
    try:
        wordlist = load_wordlist(wordlist_path)
    except FileNotFoundError:
        print(f"File not exist > {wordlist_path}")
        return

    print(f"{len(wordlist)} > {wordlist_path}")
    print("Testing Wildcard...")

    wildcard_ips = detect_wildcard(resolver, domain)
    if wildcard_ips:
        print(f"Domain: {domain} > Wilcard: {wildcard_ips}")
    else:
        print("Not found.")

    print(f"Subdomain brute-force {len(wordlist)} > {domain}...\n")
    results = brute_force(domain, wordlist, resolver, wildcard_ips)

    print(f"Subdomain: {len(results)}")


def crawl_resolve_scan():
    print("Running Web Crawler & Port Scanner...")
    start_url = input("Input Target URL: ").strip()
    if not start_url:
        print("> Invalid")
        return
        
    max_pages_input = input("Input max pages (<= 10): ").strip()
    max_pages = int(max_pages_input) if max_pages_input.isdigit() else 10

    try:
        asyncio.run(run_pipeline(start_url, max_pages))
    except Exception as e:
        print(f"ERROR: {e}")
        
        #TODO tự thử:
        #   1) Thêm giới hạn max_depth cho crawl (hiện chỉ giới hạn theo
        #      TỔNG SỐ trang, chưa giới hạn theo độ sâu).
        #   2) Đổi COMMON_PORTS thành range đầy đủ 1-1024, so sánh thời
        #      gian chạy khi tăng/giảm SCAN_CONCURRENCY.
        #   3) Gộp thêm bước JSON parsing / logging đã học ở bài trước
        #      để lưu kết quả ra file thay vì chỉ print().


    if __name__ == "__main__":
        main()


if __name__ == "__main__":
    while True:
        print("\n=== MENU ===")
        print("1 - Subdomain Brute-force")
        print("2 - Web Crawler & Port Scanner")
        print("0 - Exit")
        
        luon_chon = input("Input: ").strip()
        match luon_chon:
            case "1":
                subdomain_bruteforce()
            case "2":
                crawl_resolve_scan()
            case "0":
                print("Goodbye.")
                break
            case _:
                print("Invalid.")