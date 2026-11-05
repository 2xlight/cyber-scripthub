#!/bin/bash

source "$(dirname "$0")/recon_lib.sh"

QUICKHELP[naabu]="-p - (full port) | -top-ports 1000 | -l <file> (nhiều host) | -c <n> (concurrency)"
QUICKHELP[nmap]="-sV -sC | -Pn | -oA <file>  (có thể copy preset từ 01 nếu muốn dùng lại nguyên)"
# QUICKHELP[masscan]="..."
# QUICKHELP[rustscan]="..."

NAABU_PRESETS=(
    "Top port mặc định::naabu -host {TARGET} -silent"
    "Full port::naabu -host {TARGET} -p - -silent"
)
NMAP_PRESETS=(
    "Basic scan (host discovery)::nmap -Pn {TARGET}"
    "Service / Version::nmap -Pn -sV {TARGET}"
    "Default scripts::nmap -Pn -sC {TARGET}"
    "Full TCP ports::nmap -Pn -p- {TARGET}"
    "Service + Scripts::nmap -Pn -sV -sC {TARGET}"
)
# TODO: MASSCAN_PRESETS, RUSTSCAN_PRESETS (xem cheatsheet, đặc biệt lưu ý
# phần cảnh báo --rate của masscan trong cheatsheet).
#
# Chaining quan trọng của phase này: naabu/masscan/rustscan chỉ LỌC
# NHANH port nào đang mở, không chính xác bằng nmap ở bước service/
# version detection. Sau khi có file port mở (vd ports_open.txt), bước
# tiếp theo nên là 1 lệnh dạng:
#   nmap -Pn -sV -sC -p $(cat "$outdir/ports_open.txt" | paste -sd, -) {TARGET}
# tức lấy list port từ file, nối bằng dấu phẩy, đưa thẳng vào nmap -p
# để nmap CHỈ quét đúng port đã biết mở -> vừa nhanh vừa chính xác.
# Có thể thêm hẳn 1 preset/lựa chọn menu riêng cho việc này (nó không
# phải command 1-dòng đơn giản như các preset khác nên cần build cmd
# bằng code thay vì string tĩnh trong mảng PRESETS).

main() {
    read -rp "Target (host/IP) > " target
    validate_target "$target" || { echo "> Không hợp lệ."; exit 1; }
    local outdir
    outdir=$(get_target_dir "$target")

    while true; do
        echo
        echo "== 04: PORT SCANNING =="
        echo " Target: $target | Output: $outdir"
        echo "1 > naabu (nhanh, lọc port mở)"
        echo "2 > masscan       [TODO]"
        echo "3 > rustscan      [TODO]"
        echo "4 > nmap sâu theo port đã lọc  [TODO - xem ghi chú trên]"
        echo "q > Thoát"
        read -rp "Chọn > " choice

        case "$choice" in
            1) run_tool_menu "naabu" NAABU_PRESETS "$target" "$outdir" ;;
            q) exit 0 ;;
            *) echo "> Chưa làm hoặc không hợp lệ." ;;
        esac
    done
}

main
