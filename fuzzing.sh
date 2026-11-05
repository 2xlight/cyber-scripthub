#!/bin/bash

source "$(dirname "$0")/recon_lib.sh"

QUICKHELP[feroxbuster]="-w ${DEFAULT_WORDLIST} | -x php,txt,html | -d <depth> | -C 404,403 | --silent"
QUICKHELP[arjun]="-m GET|POST | -w <params_wordlist> | -i <file_urls> -oT <out>"
# ffuf đã có preset đầy đủ ở 01 (recon_framework.sh) - copy FFUF_PRESETS
# từ đó qua đây nếu muốn tách riêng, hoặc cứ dùng file 01 cho việc fuzz.

FEROXBUSTER_PRESETS=(
    "Quét cơ bản (tự đệ quy)::feroxbuster -u {TARGET} -w wordlist.txt --silent"
    "Giới hạn độ sâu 2::feroxbuster -u {TARGET} -w wordlist.txt -d 2 --silent"
)
ARJUN_PRESETS=(
    "Tìm tham số GET cơ bản::arjun -u {TARGET} -m GET"
    "Tìm tham số POST cơ bản::arjun -u {TARGET} -m POST"
    "Dùng wordlist tham số tùy chỉnh::arjun -u {TARGET} -w /usr/share/wordlists/seclists/Discovery/Web-Content/burp-parameter-names.txt"
    "Quét hàng loạt từ file URL (đầu ra gau/waybackurls)::arjun -i urls.txt -oT arjun_results.txt"
)


main() {
    read -rp "Target URL > " target
    validate_target "$target" || { echo "> Không hợp lệ."; exit 1; }
    local outdir
    outdir=$(get_target_dir "$target")

    while true; do
        echo
        echo "== FUZZING =="
        echo " Target: $target | Output: $outdir"
        echo "1 > feroxbuster (content discovery, auto-recurse)"
        echo "2 > arjun"
        echo "q > Quit"
        read -rp "Choose > " choice

        case "$choice" in
            1) run_tool_menu "feroxbuster" FEROXBUSTER_PRESETS "$target" "$outdir" ;;
            2) run_tool_menu "arjun" ARJUN_PRESET "$target" "$outdir";;
            q) exit 0 ;;
            *) echo "> Invalid." ;;
        esac
    done
}

main