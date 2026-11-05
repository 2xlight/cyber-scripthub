#!/bin/bash

set -uo pipefail

RESULTS_DIR="results"
declare -A QUICKHELP   # mỗi phase script tự thêm entry riêng sau khi source

timestamp() { date +"%Y%m%d_%H%M%S"; }

# QUAN TRỌNG: khác với new_target_dir() ở 01 (tạo thư mục MỚI kèm
# timestamp mỗi lần chạy), hàm này trả về CÙNG 1 thư mục cho 1 target,
# không có timestamp. Lý do: phase 03 cần đọc lại file output của
# phase 02, phase 04/05 cần đọc lại output của 02/03... nếu mỗi lần
# chạy ra 1 thư mục khác nhau thì phase sau không tìm thấy gì cả.
# Timestamp vẫn được giữ lại ở TÊN FILE (xem confirm_and_run) để
# không mất lịch sử các lần chạy.
get_target_dir() {
    local safe
    safe=$(echo "$1" | tr '/: ' '___')
    local dir="${RESULTS_DIR}/${safe}"
    mkdir -p "$dir"
    echo "$dir"
}

# TODO: mở rộng regex nếu cần (xem ghi chú ở recon_framework.sh bản 01)
validate_target() {
    local target="$1"
    [[ -n "$target" ]]
}

# Đọc input, cho phép Enter để dùng giá trị mặc định.
# Dùng để "nối" input file mặc định = output file của phase trước, vd:
#   list_file=$(read_with_default "File subdomain cần resolve" \
#               "${outdir}/subdomains_raw.txt")
read_with_default() {
    local prompt="$1"
    local default="$2"
    local input
    read -rp "${prompt} [Enter = ${default}] > " input
    echo "${input:-$default}"
}

confirm_and_run() {
    local cmd="$1"
    local outfile="$2"
    echo
    echo "Lệnh:"
    echo "  $cmd"
    read -rp "Chạy lệnh này? [Y/n] > " confirm
    if [[ "$confirm" =~ ^[Yy]$|^$ ]]; then
        eval "$cmd" | tee "$outfile"
        echo "> Đã lưu: $outfile"
    else
        echo "> Bỏ qua."
    fi
}

# Menu dùng chung cho mọi tool - y hệt bản ở 01 (recon_framework.sh).
# $1 tool_name | $2 TÊN biến mảng preset (nameref, không có $) | $3 target/input | $4 outdir
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
    echo "c > Tự viết lệnh (custom)"
    echo "0 > Quay lại"

    read -rp "Chọn > " choice
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
