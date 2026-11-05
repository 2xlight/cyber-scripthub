#!/bin/bash

source "$(dirname "$0")/recon_lib.sh"

QUICKHELP[httpx]="-silent | -sc -td -title (status/tech/title) | -fr (follow redirect) | -mc 200,302 | -threads 50"
# QUICKHELP[katana]="..."
# QUICKHELP[gau]="..."
# QUICKHELP[waybackurls]="..."

HTTPX_PRESETS=(
    "Probe cơ bản (status/title/tech)::httpx -l {TARGET} -sc -td -title -silent"
    "Probe kèm follow redirect::httpx -l {TARGET} -sc -td -title -fr -silent"
)

# TODO: KATANA_PRESETS, GAU_PRESETS, WAYBACKURLS_PRESETS (xem cheatsheet)
# Lưu ý: gau/waybackurls thường nhận thẳng DOMAIN (không cần file list)
# -> có thể giữ nguyên "$target" khi gọi run_tool_menu cho 2 tool này,
# không cần đọc list_file như httpx/katana.
# katana thì nhận cả -u (1 URL) lẫn -list (file) -> tuỳ bạn muốn làm
# preset nào, có thể tách 2 preset riêng cho 2 kiểu input.

main() {
    read -rp "Domain gốc > " target
    validate_target "$target" || { echo "> Không hợp lệ."; exit 1; }
    local outdir
    outdir=$(get_target_dir "$target")
    local default_list="${outdir}/subdomains_resolved.txt"

    while true; do
        echo
        echo "== 03: HTTP PROBING & CRAWLING =="
        echo " Target: $target | Output: $outdir"
        echo "1 > httpx (probe list subdomain đã resolve)"
        echo "2 > katana          [TODO]"
        echo "3 > gau             [TODO]"
        echo "4 > waybackurls     [TODO]"
        echo "q > Thoát"
        read -rp "Chọn > " choice

        case "$choice" in
            1)
                local list_file
                list_file=$(read_with_default "File danh sách host cần probe" "$default_list")
                run_tool_menu "httpx" HTTPX_PRESETS "$list_file" "$outdir"
                ;;
            q) exit 0 ;;
            *) echo "> Chưa làm hoặc không hợp lệ." ;;
        esac
    done
}

main
