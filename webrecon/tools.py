import subprocess
# nmap/sqlmap,... 
#choice
# main()

def run_ffuf(target):
    result = subprocess.run( # out of das system
        [
            "ffuf", # tool name
            "-w", "wordlist.txt", # lib
            "-u", target + "/FUZZ", # target url
            "-of", "json", # file json
            "-o", "ffuf.json" # in 1 file ffuf.json
        ],
        capture_output=True, #capture stderr and stdout
        text=True
    )

    return result.stdout # return for running code
