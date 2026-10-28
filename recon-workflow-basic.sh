#!/bin/bash
set -uo pipefail
# [+] phan biet cac loai loi
# ================= MAIN =================

RESULTS_DIR="results"

timestamp() { date +"%Y%m%d_%H%M%S_%N"; } 
#Goi ham date va in ngay gio theo 
#dinh dang nam-thang-ngay_gio-phut-giay_nano


get_target_dir() {
    local safe 
    local dir

    safe=$(printf '%s' "$1" | 
    #in gia tri dau tien cua tham so vao ham
        LC_ALL=C sed 's/[^A-Za-z0-9_-]/_/g') || return 1
    #chuyen sang cho bieu thuc chinh quy regex
    # s/PATTERN/THAY/FLAG
    [[ -n "$safe" ]] || return 1
    #safe rong thi loi
    dir="${RESULTS_DIR}/${safe}_$(timestamp)"

    mkdir -p -- "$dir" || return 1 #Tao neu chua co
    printf '%s\n' "$dir" 
    #VAR=$(get_target_dir "input") in thu muc ra
}

#Test for null
validate_target() {
    local target="${1:-}" 
    #${1:-} khong tham so thi cut
    local re='^[A-Za-z0-9][A-Za-z0-9._:/-]*$'

    [[ -n "${target//[[:space:]]/}" ]] 
    [[ "$t" =~ $re ]] 
    #Xoa sach khoang trang
} # [+] domain, IP, CIDR, URL hoặc đường dẫn file


confirm_and_run() {
    local cmd="$1" #Command
    local outfile="$2" #Path-file
    local confirm #luu bien Y/n cua nguoi dung
    local -a statuses #exit code cua cac pipe
    #$% -> $cmd
    printf '\nCommand > \n  %s\n' "$cmd"
    #In ra cau lenh chuan bi duoc thuc thi
    read -r -p "Running? [Y/n] > " confirm || return 1
    #Luu vao bien confirm

    if [[ "$confirm" =~ ^([Yy]|[Yy][Ee][Ss])?$ ]]; then
    #Kiem tra regex =~ ? (Enter -> Ok)
    # ^ bat dau $ ket thuc
        printf -v qt '%q' "$target" 
        cmd="${template//\{TARGET\}/$qt}"
        ## -v: ghi kết quả vào biến, không cần $(...)
        eval "$cmd" 2>&1 | tee "$outfile"
        
        statuses=("${PIPESTATUS[@]}")
        # [0] eval [1] la tee
        if (( statuses[0] == 0 && statuses[1] == 0 )); then
            printf 'Results >  %s\n' "$outfile"
        else
            printf '> Failed. (exit=%s, tee=%s). Log > %s\n' \
                "${statuses[0]}" "${statuses[1]}" "$outfile" >&2
            return 1
        fi
    else
        echo "> Pass."
    fi
}

# ================= QUICK-HELP CHO CHẾ ĐỘ "TỰ VIẾT LỆNH" =================
# Hiện gợi ý ngắn gọn trước khi người dùng tự nhập option, đỡ phải nhớ hết.
# TODO: bổ sung entry cho: curl whatweb nuclei ffuf gobuster nikto tcpdump httpx
# (xem cheatsheet để lấy nội dung)

declare -A QUICKHELP
QUICKHELP[nmap]="-sn (chỉ discover) | -Pn | -sV | -sC | -p- (full port) | -O | --script vuln | -T4 | -oA <file>"
QUICKHELP[dig]="+short | ANY/A/MX/TXT/NS | -x <ip> (reverse) | @<ns> | +trace"
QUICKHELP[curl]="-I (headers only) | -L (follow redirects) | -s -o /dev/null -w '%{http_code}' (status code) | -X POST -d 'data' | -H 'Header: val' | -k (insecure SSL)"
QUICKHELP[whatweb]="-v (verbose) | -a 3 (aggression level) | --log-json <file> | --no-errors | <url>"
QUICKHELP[nuclei]="-u <url> | -l <list.txt> | -t <template/dir> | -tags cve,rce | -severity critical,high | -silent | -o <file>"
QUICKHELP[ffuf]="-u <url/FUZZ> -w <wordlist> | -mc 200,301,302 | -fc 403,404 | -fs <size> | -H 'Header: val' | -X POST -d 'param=FUZZ'"
QUICKHELP[gobuster]="dir -u <url> -w <wordlist> | dns -d <domain> -w <wordlist> | vhost -u <url> -w <wordlist> | -t <threads> -o <file>"
QUICKHELP[nikto]="-h <url/ip> | -p <ports> | -Tuning <modes> | -ssl | -o <file> -Format txt/html"
QUICKHELP[tcpdump]="-i <interface> | -nn (no resolve) | -s0 (full packet) | -w <file.pcap> | 'port 80' | 'host <ip>'"
QUICKHELP[httpx]="-u <url> | -l <list.txt> | -silent | -mc 200,301 | -title | -tech-detect | -status-code | -o <file>"

# ================= PRESET COMMAND CHO TỪNG TOOL =================
# Format: "Nhãn hiển thị::command_template"
# {TARGET} sẽ được thay bằng target thực tế lúc chạy.

NMAP_PRESETS=(
    "Basic scan (host discovery)::nmap -Pn {TARGET}"
    "Service / Version::nmap -Pn -sV {TARGET}"
    "Default scripts::nmap -Pn -sC {TARGET}"
    "Full TCP ports::nmap -Pn -p- {TARGET}"
    "Service + Scripts::nmap -Pn -sV -sC {TARGET}"
)

DIG_PRESETS=(
    "A record::dig {TARGET} A +short"
    "Tất cả record thường dùng::dig {TARGET} ANY"
    "Reverse lookup::dig -x {TARGET}"
)

CURL_PRESETS=(
    "Headers only::curl -I {TARGET}"
    "Follow redirects::curl -L {TARGET}"
    "Get HTTP status code::curl -s -o /dev/null -w '%{http_code}' {TARGET}"
    "POST request::curl -X POST -d '{DATA}' {TARGET}"
)

WHATWEB_PRESETS=(
    "Basic scan::whatweb {TARGET}"
    "Verbose scan::whatweb -v {TARGET}"
    "Aggressive scan::whatweb -a 3 {TARGET}"
    "Export to JSON::whatweb --log-json {OUTPUT} {TARGET}"
)

NUCLEI_PRESETS=(
    "Basic vuln scan::nuclei -u {TARGET} -silent"
    "Scan by CVE tags::nuclei -u {TARGET} -tags cve -silent"
    "Critical & High severity::nuclei -u {TARGET} -severity critical,high -silent"
    "Scan from list::nuclei -l {TARGET_FILE} -silent"
)

FFUF_PRESETS=(
    "Directory fuzzing::ffuf -u {TARGET}/FUZZ -w {WORDLIST}"
    "Directory with extensions::ffuf -u {TARGET}/FUZZ -w {WORDLIST} -e .php,.html,.txt"
    "Virtual host fuzzing::ffuf -u {TARGET} -w {WORDLIST} -H 'Host: FUZZ.{DOMAIN}'"
    "Filter 404 status::ffuf -u {TARGET}/FUZZ -w {WORDLIST} -fc 404"
)

GOBUSTER_PRESETS=(
    "Directory mode::gobuster dir -u {TARGET} -w {WORDLIST}"
    "DNS mode::gobuster dns -d {TARGET} -w {WORDLIST}"
    "Vhost mode::gobuster vhost -u {TARGET} -w {WORDLIST}"
)

NIKTO_PRESETS=(
    "Basic web scan::nikto -h {TARGET}"
    "SSL/TLS scan::nikto -h {TARGET} -ssl"
    "Scan specific port::nikto -h {TARGET} -p {PORTS}"
    "Tuning scan (vulnerabilities)::nikto -h {TARGET} -Tuning 123"
)

TCPDUMP_PRESETS=(
    "Capture port 80 (HTTP)::tcpdump -i {INTERFACE} -nn -s0 -w {OUTPUT} 'port 80'"
    "Capture port 443 (HTTPS)::tcpdump -i {INTERFACE} -nn -s0 -w {OUTPUT} 'port 443'"
    "Capture specific host::tcpdump -i {INTERFACE} -nn -s0 -w {OUTPUT} 'host {TARGET}'"
)

HTTPX_PRESETS=(
    "Quick probe (title & status)::echo {TARGET} | httpx -title -status-code -silent"
    "Detect technology::echo {TARGET} | httpx -tech-detect -silent"
    "Probe from file list::cat {TARGET_FILE} | httpx -silent -mc 200,301,302"
)

# ================= HÀM MENU DÙNG CHUNG CHO MỌI TOOL =================

run_tool_menu() {
    local tool_name="$1"        # vd: "nmap" - dùng để show help + tên lệnh mặc định
    local -n presets_ref="$2"   # nameref: TÊN biến mảng preset, vd NMAP_PRESETS (không có $)
    local target="$3"
    local outdir="$4"

    echo
    echo "===== ${tool_name^^} ====="
    local i=1
    for entry in "${presets_ref[@]}"; do
        echo "$i > ${entry%%::*}"
        ((i++))
    done
    echo "c >  Custom"
    echo "0 >  MAIN MENU"

    read -rp "Input > " choice
    local cmd=""

    if [[ "$choice" == "0" ]]; then
        return
    elif [[ "$choice" =~ ^[cC]$ ]]; then
        [[ -n "${QUICKHELP[$tool_name]:-}" ]] && echo "Guessing: ${QUICKHELP[$tool_name]}"
        read -rp "Option cho $tool_name > " custom_opts
        cmd="$tool_name $custom_opts $target"
    elif [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice < i )); then
        local entry="${presets_ref[$((choice-1))]}"
        local template="${entry#*::}"
        cmd="${template//\{TARGET\}/$target}"
    else
        echo "> Lựa chọn không hợp lệ."
        return
    fi

    local outfile="${outdir}/${tool_name}_$(timestamp).txt"
    #timestamp() { date +"%Y%m%d_%H%M%S"; } 
    #results/example.com/nmap_20261025_191300.txt
    confirm_and_run "$cmd" "$outfile"
}

# ================= MAIN LOOP =================

main() {
    read -rp "Target (IP / dải IP / CIDR / domain) > " target
    if ! validate_target "$target"; then
        echo "> Target is invalid."
        exit 1
    fi
    local outdir
    outdir=$(new_target_dir "$target")

    while true; do
        echo
        echo "================================"
        echo " Target : $target"
        echo " Output : $outdir"
        echo "================================"
        echo "1  > nmap"
        echo "2  > dig"
        echo "3  > curl"
        echo "4  > whatweb"
        echo "5  > nuclei"
        echo "6  > ffuf"
        echo "7  > gobuster"
        echo "8  > nikto"
        echo "9  > tcpdump"
        echo "10 > httpx"
        echo "t  > Changing target"
        echo "q  > EXIT"

        read -rp "Choose tool > " tool_choice
        case "$tool_choice" in
            1) run_tool_menu "nmap" NMAP_PRESETS "$target" "$outdir" ;;
            2) run_tool_menu "dig"  DIG_PRESETS  "$target" "$outdir" ;;
            3) run_tool_menu "curl"  CURL_PRESETS  "$target" "$outdir" ;;
            4) run_tool_menu "whatweb"  WHATWEB_PRESETS  "$target" "$outdir" ;;
            5) run_tool_menu "nuclei"  NUCLEI_PRESETS  "$target" "$outdir" ;;
            6) run_tool_menu "ffuf"  FFUF_PRESETS  "$target" "$outdir" ;;
            7) run_tool_menu "gobuster"  GOBUSTER_PRESETS  "$target" "$outdir" ;;
            8) run_tool_menu "nikto"  NIKTO_PRESETS  "$target" "$outdir" ;;
            9) run_tool_menu "tcpdump"  TCPDUMP_PRESETS  "$target" "$outdir" ;;
            10) run_tool_menu "httpx"  HTTPX_PRESETS  "$target" "$outdir" ;;
            t)
                read -rp "New target > " target
                validate_target "$target" || { echo "> Invalid."; continue; }
                outdir=$(new_target_dir "$target")
                ;;
            q) echo "EXIT."; exit 0 ;;
            *) echo "> Invalid." ;;
        esac
    done
}

main