#!/bin/bash

set -uo pipefail 

RESULTS_DIR="results"


DEFAULT_WORDLIST="${DEFAULT_WORDLIST:-/usr/share/wordlists/dirb/common.txt}"

declare -A QUICKHELP
declare -A LIST_INPUT_DEFAULT   # tool nào cần input là FILE list thay vì target đơn

# ================= HÀM DÙNG CHUNG =================

timestamp() { date +"%Y%m%d_%H%M%S"; }

get_target_dir() {
    local safe="${1//[^A-Za-z0-9_-]/_}"
    local dir="${RESULTS_DIR}/${safe}"
    mkdir -p "$dir"
    echo "$dir"
}

validate_target() {
    local target="$1"
    [[ -n "$target" ]]
}

read_with_default() {
    local prompt="$1"
    local default="$2"
    local input
    IFS= read -rp "${prompt} [Enter = ${default}] > " input
    echo "${input:-$default}"
}

confirm_and_run() {
    local cmd="$1"
    local outfile="$2"
    local -a statuses #exit code cua cac pipe

    echo "Input >  "
    echo "  $cmd"
    read -rp "Running? [Y/n] >  " confirm || Return 1
    if [[ "$confirm" =~ ^[Yy]$|^$ ]]; then
        eval "$cmd" | tee "$outfile"
        echo "Ouput >  $outfile"
    else
        echo "> Pass."
    fi
}

# Menu preset cho 1 TOOL cụ thể.
# $1 tool_name | $2 TÊN mảng preset (nameref) | $3 target/input | $4 outdir
run_tool_menu() {
    local tool_name="$1"
    local -n presets_ref="$2"
    local target="$3"
    local outdir="$4"

    echo
    echo "===== ${tool_name^^} ====="
    local i=1
    for entry in "${presets_ref[@]}"; do
        echo "$i > ${entry%%::*}"
        ((i++))
    done
    echo "c > Custom"
    echo "0 > Back"

    read -rp "Choose > " choice
    local cmd=""

    if [[ "$choice" == "0" ]]; then
        return
    elif [[ "$choice" =~ ^[cC]$ ]]; then
        [[ -n "${QUICKHELP[$tool_name]:-}" ]] && echo "Gợi ý: ${QUICKHELP[$tool_name]}"
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
    confirm_and_run "$cmd" "$outfile"
}

# Menu cho 1 NHÓM (category) - liệt kê tool trong nhóm, chọn xong gọi
# run_tool_menu. Tool nào cần list-file (xem LIST_INPUT_DEFAULT) sẽ tự
# hỏi file thay vì dùng target trực tiếp. Tool còn TODO (chưa có mảng
# preset) sẽ báo thay vì làm script crash.
# $1 label nhóm | $2 TÊN mảng "tool::PRESETS_VAR" (nameref) | $3 target | $4 outdir
show_category_menu() {
    local cat_label="$1"
    local -n tools_ref="$2"
    local target="$3"
    local outdir="$4"

    while true; do
        echo
        echo "== $cat_label =="
        local i=1
        for entry in "${tools_ref[@]}"; do
            echo "$i > ${entry%%::*}"
            ((i++))
        done
        echo "0 > Quay lại menu chính"
        read -rp "Chọn tool > " choice
        [[ "$choice" == "0" ]] && return

        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice < i )); then
            local entry="${tools_ref[$((choice-1))]}"
            local tool_name="${entry%%::*}"
            local presets_var="${entry#*::}"

            if ! declare -p "$presets_var" &>/dev/null; then
                echo "> [$tool_name] chưa có preset (TODO) - xem README.md."
                continue
            fi

            if [[ -n "${LIST_INPUT_DEFAULT[$tool_name]:-}" ]]; then
                local list_file
                list_file=$(read_with_default "File input cho $tool_name" \
                            "${outdir}/${LIST_INPUT_DEFAULT[$tool_name]}")
                run_tool_menu "$tool_name" "$presets_var" "$list_file" "$outdir"
            else
                run_tool_menu "$tool_name" "$presets_var" "$target" "$outdir"
            fi
        else
            echo "> Lựa chọn không hợp lệ."
        fi
    done
}

# ================= QUICKHELP =================

QUICKHELP[nmap]="-sn (chỉ discover) | -Pn | -sV | -sC | -p- (full port) | -O | --script vuln | -T4 | -oA <file>"
QUICKHELP[dig]="+short | ANY/A/MX/TXT/NS | -x <ip> (reverse) | @<ns> | +trace"
QUICKHELP[subfinder]="-silent | -all (chậm hơn) | -recursive | -dL <file>"
QUICKHELP[dnsx]="-silent | -a -resp (in IP) | -cname | -wc (lọc wildcard)"
QUICKHELP[httpx]="-silent | -sc -td -title | -fr (follow redirect) | -mc 200,302 | -threads 50"
QUICKHELP[naabu]="-p - (full port) | -top-ports 1000 | -l <file> | -c <n>"
QUICKHELP[feroxbuster]="-w <wordlist> | -x php,txt,html | -d <depth> | -C 404,403 | --silent"
# TODO: thêm entry khi bạn viết preset cho tool còn lại (xem README.md)

# ================= LIST-INPUT TOOLS =================
# Tool nào cần 1 FILE danh sách (không phải target đơn) thì khai tên
# file mặc định ở đây - show_category_menu tự hỏi list_file thay vì
# dùng target trực tiếp.

LIST_INPUT_DEFAULT[dnsx]="subdomains_raw.txt"
LIST_INPUT_DEFAULT[puredns]="subdomains_raw.txt"
LIST_INPUT_DEFAULT[httpx]="subdomains_resolved.txt"
LIST_INPUT_DEFAULT[katana]="http_alive.txt"
LIST_INPUT_DEFAULT[arjun]="urls_all.txt"

# ================= PRESET COMMAND =================
# {TARGET} sẽ được thay bằng target/list_file thực tế lúc chạy.

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

SUBFINDER_PRESETS=(
    "Passive cơ bản::subfinder -d {TARGET} -silent"
    "Dùng tất cả nguồn (chậm hơn)::subfinder -d {TARGET} -all -silent"
)

DNSX_PRESETS=(
    "Resolve, loại NXDOMAIN::dnsx -l {TARGET} -silent"
    "Resolve kèm in IP::dnsx -l {TARGET} -a -resp -silent"
)

HTTPX_PRESETS=(
    "Probe cơ bản (status/title/tech)::httpx -l {TARGET} -sc -td -title -silent"
    "Probe kèm follow redirect::httpx -l {TARGET} -sc -td -title -fr -silent"
)

NAABU_PRESETS=(
    "Top port mặc định::naabu -host {TARGET} -silent"
    "Full port::naabu -host {TARGET} -p - -silent"
)

FEROXBUSTER_PRESETS=(
    "Quét cơ bản (tự đệ quy)::feroxbuster -u {TARGET} -w ${DEFAULT_WORDLIST} --silent"
    "Giới hạn độ sâu 2::feroxbuster -u {TARGET} -w ${DEFAULT_WORDLIST} -d 2 --silent"
)

# TODO: các mảng dưới đây CHƯA khai báo -> tool tương ứng trong CAT_*
# bên dưới sẽ hiện "[TODO] xem README.md" khi chọn. Chỉ cần khai báo
# đúng format "Nhãn::command_template" là tool đó chạy được ngay,
# không cần sửa gì ở phần engine phía trên:
#   CURL_PRESETS WHATWEB_PRESETS NUCLEI_PRESETS NIKTO_PRESETS
#   TCPDUMP_PRESETS (đọc README - cần cân nhắc thêm cho việc chạy nền)
#   AMASS_PRESETS ASSETFINDER_PRESETS PUREDNS_PRESETS
#   KATANA_PRESETS GAU_PRESETS WAYBACKURLS_PRESETS
#   MASSCAN_PRESETS RUSTSCAN_PRESETS
#   FFUF_PRESETS GOBUSTER_PRESETS ARJUN_PRESETS

# ================= NHÓM (CATEGORY) =================
# Format: "tool_name::TÊN_MẢNG_PRESET"

CAT_01_DISCOVERY=(
    "nmap::NMAP_PRESETS"
    "dig::DIG_PRESETS"
    "curl::CURL_PRESETS"
    "whatweb::WHATWEB_PRESETS"
    "nuclei::NUCLEI_PRESETS"
    "nikto::NIKTO_PRESETS"
    "tcpdump::TCPDUMP_PRESETS"
)

CAT_02_SUBDOMAIN=(
    "subfinder::SUBFINDER_PRESETS"
    "amass::AMASS_PRESETS"
    "assetfinder::ASSETFINDER_PRESETS"
    "dnsx::DNSX_PRESETS"
    "puredns::PUREDNS_PRESETS"
)

CAT_03_HTTP=(
    "httpx::HTTPX_PRESETS"
    "katana::KATANA_PRESETS"
    "gau::GAU_PRESETS"
    "waybackurls::WAYBACKURLS_PRESETS"
)

CAT_04_PORTSCAN=(
    "naabu::NAABU_PRESETS"
    "masscan::MASSCAN_PRESETS"
    "rustscan::RUSTSCAN_PRESETS"
)

CAT_05_FUZZING=(
    "ffuf::FFUF_PRESETS"
    "gobuster::GOBUSTER_PRESETS"
    "feroxbuster::FEROXBUSTER_PRESETS"
    "arjun::ARJUN_PRESETS"
)

# ================= MAIN =================

main() {
    read -rp "Target chính (domain/IP) > " target
    validate_target "$target" || { echo "> Không hợp lệ."; exit 1; }
    local outdir
    outdir=$(get_target_dir "$target")

    while true; do
        echo
        echo "================================"
        echo " RECON FRAMEWORK"
        echo " Target: $target | Output: $outdir"
        echo "================================"
        echo "1 > 01 - Host/Port cơ bản (nmap, dig...)"
        echo "2 > 02 - Subdomain recon"
        echo "3 > 03 - HTTP probing & crawling"
        echo "4 > 04 - Port scanning"
        echo "5 > 05 - Fuzzing"
        echo "t > Đổi target"
        echo "q > Thoát"
        read -rp "Chọn nhóm > " cat_choice

        case "$cat_choice" in
            1) show_category_menu "01: HOST/PORT CƠ BẢN"    CAT_01_DISCOVERY "$target" "$outdir" ;;
            2) show_category_menu "02: SUBDOMAIN RECON"     CAT_02_SUBDOMAIN "$target" "$outdir" ;;
            3) show_category_menu "03: HTTP PROBING/CRAWL"  CAT_03_HTTP      "$target" "$outdir" ;;
            4) show_category_menu "04: PORT SCANNING"       CAT_04_PORTSCAN  "$target" "$outdir" ;;
            5) show_category_menu "05: FUZZING"             CAT_05_FUZZING   "$target" "$outdir" ;;
            t)
                read -rp "Target mới > " target
                validate_target "$target" || { echo "> Không hợp lệ."; continue; }
                outdir=$(get_target_dir "$target")
                ;;
            q) echo "Thoát."; exit 0 ;;
            *) echo "> Không hợp lệ." ;;
        esac
    done
}

main