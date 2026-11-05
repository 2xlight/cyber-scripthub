#!/usr/bin/env python3
"""
=====================================================================
  RECON TOOL v2 - Concurrent Recon Automation (học asyncio + pentest)
=====================================================================
4 module recon chạy SONG SONG (concurrent) nhờ asyncio:

  1) DNS Resolve      - resolve domain/subdomain ra IP
  2) Subdomain Enum   - brute-force {word}.{domain} bằng wordlist, resolve
                         hàng loạt cùng lúc để tìm subdomain đang tồn tại
  3) Port Scan        - TCP connect scan nhiều cổng trên nhiều host cùng lúc
  4) Web Crawl        - bò (crawl) các trang cùng domain, giới hạn độ sâu,
                         dùng mô hình producer-consumer (asyncio.Queue)

THIẾT KẾ: mọi I/O (DNS, socket, HTTP) đều là coroutine không-blocking, nên
1 tiến trình Python DUY NHẤT vẫn có thể xử lý hàng trăm host/cổng/URL cùng
lúc mà không cần multi-thread/multi-process => đây là lý do asyncio "hiệu
quả" hơn code tuần tự (sequential) rất nhiều lần cho tác vụ I/O-bound như
recon.

Yêu cầu:
  - Python 3.10+
  - pip install aiohttp --break-system-packages

CẢNH BÁO PHÁP LÝ / ĐẠO ĐỨC:
  Subdomain enum, port scan, crawl trên hệ thống KHÔNG thuộc quyền sở hữu
  hoặc KHÔNG có văn bản ủy quyền kiểm thử (pentest scope) là hành vi có thể
  vi phạm pháp luật (vd Nghị định/Luật An ninh mạng, CFAA, Computer Misuse
  Act...). Tool này yêu cầu xác nhận thủ công trước khi chạy - xem hàm
  confirm_authorization().

Cách chạy:
  python3 recon_tool_v2.py example.com -w subdomains.txt -p top
  python3 recon_tool_v2.py example.com -p 1-1000 --no-crawl -o report.json
  python3 recon_tool_v2.py example.com -w list.txt -c 300 --max-depth 3
=====================================================================
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

try:
    import aiohttp
except ImportError:
    print("[!] Thiếu thư viện aiohttp. Cài bằng: pip install aiohttp --break-system-packages")
    sys.exit(1)


# =====================================================================
# CẤU HÌNH MẶC ĐỊNH
# =====================================================================
# Top 20 cổng hay gặp nhất trong thực tế (rút gọn từ nmap-services top-1000)
DEFAULT_TOP_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443,
                      445, 993, 995, 1723, 3306, 3389, 5900, 8080, 8443]
DEFAULT_CONCURRENCY = 200      # số task async chạy song song tối đa (Semaphore)
DEFAULT_TIMEOUT = 3.0          # giây, timeout cho mỗi kết nối DNS/TCP
USER_AGENT = "ReconToolV2/1.0 (+authorized-security-testing-only)"


class C:
    """Mã màu ANSI cho output terminal - chỉ để dễ đọc, không ảnh hưởng logic."""
    G = "\033[92m"   # xanh lá: mở / thành công
    R = "\033[91m"   # đỏ: lỗi / đóng
    Y = "\033[93m"   # vàng: cảnh báo
    B = "\033[94m"   # xanh dương: thông tin
    BOLD = "\033[1m"
    X = "\033[0m"    # reset


# =====================================================================
# CẤU TRÚC DỮ LIỆU KẾT QUẢ
# =====================================================================
@dataclass
class SubdomainHit:
    fqdn: str
    ip: str


@dataclass
class PortHit:
    port: int
    banner: str = ""


@dataclass
class HostReport:
    host: str
    ip: Optional[str] = None
    open_ports: list[PortHit] = field(default_factory=list)
    crawled_urls: list[str] = field(default_factory=list)


# =====================================================================
# MODULE 1: DNS RESOLVE
# =====================================================================
async def resolve_host(loop: asyncio.AbstractEventLoop, host: str,
                        timeout: float = DEFAULT_TIMEOUT) -> Optional[str]:
    """
    Resolve 1 hostname ra IP đầu tiên tìm được.

    Dùng loop.getaddrinfo() - đây là API DNS resolution CÓ SẴN trong asyncio:
    nó tự chạy socket.getaddrinfo() (vốn là hàm blocking) ở 1 thread pool nền,
    nên KHÔNG làm nghẽn event loop chính, mà KHÔNG cần cài thêm thư viện DNS
    async như aiodns/pycares (đánh đổi: hơi chậm hơn 1 chút cho hàng chục
    nghìn query so với aiodns, nhưng đủ nhanh và không cần biên dịch thêm gì).
    """
    try:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(host, None, proto=socket.IPPROTO_TCP),
            timeout=timeout,
        )
        return infos[0][4][0]  # infos[0] = (family, type, proto, canonname, sockaddr); sockaddr[0] = IP
    except (socket.gaierror, asyncio.TimeoutError, OSError):
        return None  # NXDOMAIN / không phản hồi kịp -> coi như không tồn tại


# =====================================================================
# MODULE 2: SUBDOMAIN ENUM
# =====================================================================
async def enumerate_subdomains(loop: asyncio.AbstractEventLoop, domain: str,
                                wordlist: list[str], concurrency: int) -> list[SubdomainHit]:
    """
    Thử resolve {word}.{domain} cho TỪNG từ trong wordlist, chạy SONG SONG
    nhưng bị giới hạn bởi asyncio.Semaphore(concurrency) - đây là điểm mấu
    chốt để tool "hiệu quả nhưng không thô bạo": nếu để chạy vô hạn cùng lúc
    (vd wordlist 100k dòng), có thể làm quá tải DNS resolver hoặc bị chặn.
    """
    sem = asyncio.Semaphore(concurrency)
    hits: list[SubdomainHit] = []
    done = 0
    total = len(wordlist)

    async def worker(word: str) -> None:
        nonlocal done
        fqdn = f"{word}.{domain}"
        async with sem:               # chỉ tối đa `concurrency` coroutine "vào" cùng lúc
            ip = await resolve_host(loop, fqdn)
        done += 1
        if ip:
            hits.append(SubdomainHit(fqdn, ip))
            print(f"  {C.G}[+] {fqdn:<40} -> {ip}{C.X}")
        if done % 200 == 0:
            print(f"  {C.B}[*] ... đã thử {done}/{total}{C.X}")

    # asyncio.gather chạy tất cả worker "gần như cùng lúc"; Semaphore bên trong
    # mới là thứ thực sự điều tiết số lượng active tại 1 thời điểm.
    await asyncio.gather(*(worker(w) for w in wordlist))
    return hits


# =====================================================================
# MODULE 3: PORT SCAN
# =====================================================================
async def scan_port(host: str, port: int, timeout: float,
                     sem: asyncio.Semaphore) -> Optional[PortHit]:
    """
    TCP CONNECT SCAN: thực hiện bắt tay TCP đầy đủ (3-way handshake) tới
    host:port bằng asyncio.open_connection(). Đây là kiểu scan "chậm hơn
    nhưng không cần quyền root/raw socket" - khác với SYN scan (nmap -sS)
    vốn cần quyền admin để tự tạo raw packet, chỉ gửi SYN rồi bỏ kết nối
    giữa chừng (nửa bắt tay, kín đáo hơn nhưng cần thư viện/quyền đặc biệt).
    """
    async with sem:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return None  # cổng đóng / bị firewall lọc / không phản hồi kịp timeout

    banner = ""
    try:
        # Banner grabbing: nhiều service (FTP/SSH/SMTP...) tự gửi vài dòng
        # chào hỏi ngay khi connect thành công, đọc thử để nhận diện dịch vụ.
        data = await asyncio.wait_for(reader.read(256), timeout=1.0)
        banner = data.decode(errors="ignore").strip()
    except (asyncio.TimeoutError, OSError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass

    return PortHit(port=port, banner=banner)


async def scan_ports(host: str, ports: list[int], concurrency: int,
                      timeout: float) -> list[PortHit]:
    """Quét toàn bộ `ports` trên 1 host, song song, giới hạn bởi Semaphore riêng."""
    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*(scan_port(host, p, timeout, sem) for p in ports))
    return sorted((r for r in results if r is not None), key=lambda r: r.port)


def parse_ports(port_arg: Optional[str]) -> list[int]:
    """
    Parse chuỗi cổng người dùng nhập, hỗ trợ 3 kiểu, có thể trộn lẫn:
      - None / "top"          -> DEFAULT_TOP_PORTS (20 cổng phổ biến)
      - "22,80,443"           -> danh sách rời rạc
      - "1-1000"              -> dải liên tục
      - "22,80,1000-1010"     -> kết hợp cả hai
    """
    if not port_arg or port_arg.lower() == "top":
        return DEFAULT_TOP_PORTS
    ports: set[int] = set()
    for part in port_arg.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            ports.update(range(int(start), int(end) + 1))
        else:
            ports.add(int(part))
    return sorted(ports)


# =====================================================================
# MODULE 4: WEB CRAWL
# =====================================================================
class _LinkExtractor(HTMLParser):
    """Parser HTML tối giản (stdlib, không cần BeautifulSoup) chỉ để lấy href trong <a>."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)


async def crawl_site(session: aiohttp.ClientSession, start_url: str, max_depth: int,
                      max_pages: int, worker_count: int) -> list[str]:
    """
    BFS crawl giới hạn trong CÙNG domain gốc, dùng mô hình producer-consumer
    kinh điển của asyncio:
      - `queue`    : hàng đợi (url, depth) cần crawl tiếp
      - N "worker" : cùng lấy job từ queue và xử lý song song
      - `visited`  : set chống crawl trùng URL

    Lưu ý về điều kiện dừng: mỗi worker tự thoát khi queue.get() không có gì
    trong 2 giây liên tục. Điều này AN TOÀN (không bỏ sót URL) vì item mới
    chỉ được thêm vào queue bởi 1 worker đang xử lý dở - nghĩa là chừng nào
    còn ít nhất 1 worker đang "bận" thì các worker khác quay lại vẫn còn việc.
    """
    base_netloc = urlparse(start_url).netloc
    queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    visited: set[str] = {start_url}
    found: list[str] = []
    lock = asyncio.Lock()

    await queue.put((start_url, 0))

    async def worker() -> None:
        while True:
            try:
                url, depth = await asyncio.wait_for(queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                return  # hàng đợi rỗng đủ lâu -> coi như crawl xong, worker tự kết thúc

            async with lock:
                if len(found) >= max_pages:
                    queue.task_done()
                    continue

            html = ""
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5),
                                        allow_redirects=True) as resp:
                    ctype = resp.headers.get("Content-Type", "")
                    if resp.status == 200 and "text/html" in ctype:
                        html = await resp.text(errors="ignore")
            except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeDecodeError):
                pass  # bỏ qua URL lỗi, không làm sập cả crawl

            async with lock:
                found.append(url)
            print(f"  {C.B}[crawl]{C.X} {url}  ({len(html)} bytes)")

            if html and depth < max_depth:
                parser = _LinkExtractor()
                parser.feed(html)
                for href in parser.links:
                    abs_url = urljoin(url, href).split("#", 1)[0]  # bỏ phần fragment #...
                    if urlparse(abs_url).netloc != base_netloc:
                        continue  # chỉ đi theo link CÙNG domain, không "leo" ra site khác
                    if abs_url not in visited:
                        visited.add(abs_url)
                        await queue.put((abs_url, depth + 1))

            queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
    await asyncio.gather(*workers)
    return found


# =====================================================================
# ORCHESTRATION: gộp cả 4 module, CHẠY SONG SONG giữa các host
# =====================================================================
async def run_recon(args: argparse.Namespace) -> dict:
    loop = asyncio.get_running_loop()

    print(f"{C.BOLD}[*] Resolving {args.domain} ...{C.X}")
    root_ip = await resolve_host(loop, args.domain)
    if not root_ip:
        print(f"{C.R}[!] Không resolve được {args.domain}, dừng lại.{C.X}")
        return {}
    print(f"{C.G}[+] {args.domain} -> {root_ip}{C.X}")

    # ---- Module 2: subdomain enum (nếu có wordlist) ----
    subdomain_hits: list[SubdomainHit] = []
    if args.wordlist:
        words = [w.strip() for w in Path(args.wordlist).read_text().splitlines() if w.strip()]
        print(f"\n{C.BOLD}[*] Subdomain enum: {len(words)} candidates "
              f"(concurrency={args.concurrency}){C.X}")
        subdomain_hits = await enumerate_subdomains(loop, args.domain, words, args.concurrency)
        print(f"{C.G}[+] Tìm thấy {len(subdomain_hits)} subdomain đang sống.{C.X}")

    hosts: list[tuple[str, str]] = [(args.domain, root_ip)] + \
        [(h.fqdn, h.ip) for h in subdomain_hits]
    ports = parse_ports(args.ports)

    # ---- Module 3: port scan - CHẠY SONG SONG cho MỌI host cùng lúc ----
    print(f"\n{C.BOLD}[*] Port scan: {len(ports)} cổng x {len(hosts)} host, "
          f"chạy song song ...{C.X}")
    port_tasks = {
        host: asyncio.create_task(scan_ports(host, ports, args.concurrency, DEFAULT_TIMEOUT))
        for host, _ip in hosts
    }
    await asyncio.gather(*port_tasks.values())  # đợi TẤT CẢ host quét xong cùng lúc, không tuần tự

    reports: dict[str, HostReport] = {}
    for host, ip in hosts:
        open_ports = port_tasks[host].result()
        reports[host] = HostReport(host=host, ip=ip, open_ports=open_ports)
        for p in open_ports:
            print(f"  {C.G}[OPEN] {host}:{p.port}{C.X}  {p.banner[:50]}")

    # ---- Module 4: crawl - chỉ với host có cổng web mở, cũng chạy song song ----
    if not args.no_crawl:
        # Ưu tiên chọn 1 cổng web "đại diện" cho mỗi host: 443/8443 (https) trước,
        # rồi 80/8080 (http). QUAN TRỌNG: nếu cổng không phải 80/443 tiêu chuẩn
        # (vd 8080) thì bắt buộc phải ghi rõ ":port" trong URL, nếu không aiohttp
        # sẽ tự nối vào cổng 80/443 mặc định -> sai host hoàn toàn.
        WEB_PORT_PRIORITY = [(443, "https"), (8443, "https"), (80, "http"), (8080, "http")]

        def pick_web_endpoint(r: HostReport) -> Optional[tuple[str, str]]:
            open_ports = {p.port for p in r.open_ports}
            for port, scheme in WEB_PORT_PRIORITY:
                if port in open_ports:
                    netloc = r.host if port in (80, 443) else f"{r.host}:{port}"
                    return scheme, netloc
            return None

        crawl_plan = [(r, pick_web_endpoint(r)) for r in reports.values()]
        crawl_plan = [(r, ep) for r, ep in crawl_plan if ep is not None]

        if crawl_plan:
            print(f"\n{C.BOLD}[*] Crawl {len(crawl_plan)} host có cổng web mở "
                  f"(song song)...{C.X}")
            connector = aiohttp.TCPConnector(limit=args.concurrency, ssl=False)
            async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT},
                                              connector=connector) as session:
                crawl_coros = []
                crawl_targets = []
                for r, (scheme, netloc) in crawl_plan:
                    crawl_targets.append(r)
                    crawl_coros.append(
                        crawl_site(session, f"{scheme}://{netloc}/", args.max_depth,
                                    args.max_pages, worker_count=10)
                    )
                # asyncio.gather chạy crawl của NHIỀU host song song, mỗi host lại
                # tự có N worker riêng bên trong -> 2 tầng concurrency lồng nhau.
                crawl_results = await asyncio.gather(*crawl_coros, return_exceptions=True)
            for r, urls in zip(crawl_targets, crawl_results):
                r.crawled_urls = urls if isinstance(urls, list) else []

    return {
        "target": args.domain,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "hosts": {
            host: {
                "ip": r.ip,
                "open_ports": [{"port": p.port, "banner": p.banner} for p in r.open_ports],
                "crawled_urls": r.crawled_urls,
            }
            for host, r in reports.items()
        },
    }


# =====================================================================
# CLI
# =====================================================================
def confirm_authorization(domain: str, skip: bool) -> bool:
    """Chặn chạy nhầm/chạy bừa: bắt người dùng gõ lại đúng tên domain để xác nhận."""
    if skip:
        return True
    print(f"\n{C.Y}[!] Bạn sắp quét subdomain/port/crawl trên: {domain}{C.X}")
    print(f"{C.Y}    Chỉ tiếp tục nếu bạn CÓ QUYỀN kiểm thử hợp pháp trên mục tiêu này.{C.X}")
    answer = input(f"    Gõ lại chính xác '{domain}' để xác nhận: ").strip()
    return answer == domain


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Recon Tool v2 - crawl + resolve + port scan + subdomain enum (concurrent)")
    p.add_argument("domain", help="Domain mục tiêu, vd: example.com")
    p.add_argument("-w", "--wordlist", help="File wordlist subdomain, mỗi dòng 1 từ")
    p.add_argument("-p", "--ports", help="'top' | '80,443' | '1-1000' (mặc định: top 20 cổng)")
    p.add_argument("-c", "--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                    help=f"Số task song song tối đa (mặc định {DEFAULT_CONCURRENCY})")
    p.add_argument("--max-depth", type=int, default=2, help="Độ sâu crawl tối đa")
    p.add_argument("--max-pages", type=int, default=50, help="Số trang tối đa mỗi host khi crawl")
    p.add_argument("--no-crawl", action="store_true", help="Bỏ qua bước crawl")
    p.add_argument("-o", "--output", help="File JSON output (mặc định tự đặt tên)")
    p.add_argument("-y", "--yes", action="store_true", help="Bỏ qua bước xác nhận ủy quyền")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()

    if not confirm_authorization(args.domain, args.yes):
        print(f"{C.R}[!] Không xác nhận được quyền kiểm thử. Dừng chương trình.{C.X}")
        sys.exit(1)

    start = time.monotonic()
    report = asyncio.run(run_recon(args))
    elapsed = time.monotonic() - start

    if not report:
        sys.exit(1)

    print(f"\n{C.BOLD}[+] Hoàn tất trong {elapsed:.1f}s{C.X}")
    for host, data in report["hosts"].items():
        print(f"\n== {host} ({data['ip']}) ==")
        for p in data["open_ports"]:
            print(f"   [OPEN] {p['port']:<6} {p['banner'][:60]}")
        if data["crawled_urls"]:
            print(f"   Crawled {len(data['crawled_urls'])} URL(s)")

    out_path = Path(args.output or f"recon_{args.domain}_{int(time.time())}.json")
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n{C.G}[+] Báo cáo JSON đã lưu: {out_path}{C.X}")


if __name__ == "__main__":
    main()
