#!/bin/bash

source "$(dirname "$0")/recon_lib.sh"

QUICKHELP[subfinder]="-silent | -all (dùng hết nguồn, chậm hơn) | -recursive | -dL <file> (nhiều domain)"
QUICKHELP[dnsx]="-silent | -a -resp (in cả IP) | -cname (tìm subdomain takeover) | -wc (lọc wildcard)"
# QUICKHELP[amass]="..."
# QUICKHELP[assetfinder]="..."
# QUICKHELP[puredns]="..."

SUBFINDER_PRESETS=(
    "Passive cơ bản::subfinder -d {TARGET} -silent"
    "Dùng tất cả nguồn (chậm hơn)::subfinder -d {TARGET} -all -silent"
)

DNSX_PRESETS=(
    "Resolve, loại NXDOMAIN::dnsx -l {TARGET} -silent"
    "Resolve kèm in IP::dnsx -l {TARGET} -a -resp -silent"
)

# TODO: tự định nghĩa AMASS_PRESETS, ASSETFINDER_PRESETS, PUREDNS_PRESETS
# (xem cheatsheet). Lưu ý: dnsx/puredns nhận INPUT là 1 FILE danh sách
# subdomain (không phải domain đơn) -> khi gọi run_tool_menu cho các
# tool này, truyền biến $list_file thay vì $target (xem case "4" bên dưới).
#
# TODO: subfinder/amass/assetfinder mỗi cái ghi ra 1 file log riêng
# (qua confirm_and_run). Trước khi resolve bằng dnsx, cần gộp lại + dedup:
#   cat "$outdir"/{subfinder,amass,assetfinder}_*.txt 2>/dev/null \
#     | sort -u > "$outdir/subdomains_raw.txt"
# Có thể thêm 1 lựa chọn menu riêng để tự động hoá bước gộp này.

main() {
    read -rp "Domain gốc > " target
    validate_target "$target" || { echo "> Không hợp lệ."; exit 1; }
    local outdir
    outdir=$(get_target_dir "$target")

    while true; do
        echo
        echo "== 02: SUBDOMAIN RECON =="
        echo " Target: $target | Output: $outdir"
        echo "1 > subfinder (passive)"
        echo "2 > amass          [TODO]"
        echo "3 > assetfinder    [TODO]"
        echo "4 > dnsx (resolve file đã gộp)"
        echo "5 > puredns        [TODO]"
        echo "q > Thoát"
        read -rp "Chọn > " choice

        case "$choice" in
            1) run_tool_menu "subfinder" SUBFINDER_PRESETS "$target" "$outdir" ;;
            4)
                local list_file
                list_file=$(read_with_default "File danh sách subdomain cần resolve" \
                            "${outdir}/subdomains_raw.txt")
                run_tool_menu "dnsx" DNSX_PRESETS "$list_file" "$outdir"
                ;;
            q) exit 0 ;;
            *) echo "> Chưa làm hoặc không hợp lệ." ;;
        esac
    done
}

main
