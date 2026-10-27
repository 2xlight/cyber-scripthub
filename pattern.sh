#!/bin/bash

set -uo pipefail  

demo_basic_pipe() {
    echo "Basic pipe"
    seq 1 5 | grep -E '[24]'
    # print 1 \n2 \n3 \n4 \n5
    # recon: subfinder -d target.com -silent | httpx -silent
}

demo_tee_branch() {
    echo "== 2) tee: vừa lưu ra file, vừa cho đi tiếp trong pipe =="
    seq 1 5 | tee /tmp/demo_numbers.txt | grep 3
    echo "   (đã lưu toàn bộ 1-5 vào /tmp/demo_numbers.txt, không chỉ dòng match)"
    # recon: subfinder -d target.com -silent | tee subs.txt | dnsx -silent
}

demo_xargs_parallel() {
    echo "== 3) xargs -P: chạy N tiến trình SONG SONG từ 1 danh sách =="
    seq 1 5 | xargs -P 3 -I{} bash -c 'echo "  task {} bắt đầu"; sleep 1; echo "  task {} xong"'
    # recon: cat ips.txt | xargs -P 10 -I{} nmap -Pn -F {} -oN "results/{}.txt"
    # LƯU Ý: -P càng cao càng nhanh nhưng càng dễ bị target/mạng phản
    # ứng (rate limit, IDS...) - chọn số hợp lý theo phạm vi được phép test.
}

demo_process_substitution() {
    echo "== 4) Process substitution: dùng output lệnh như 1 file ảo =="
    diff <(seq 1 5) <(seq 1 5 | sed 's/3/THREE/')
    # recon: diff <(sort subs_lan1.txt) <(sort subs_lan2.txt)  # so sánh 2 lần quét
}

demo_while_read_loop() {
    echo "== 5) while read: xử lý từng dòng AN TOÀN (kể cả dòng có khoảng trắng) =="
    printf 'alpha\nbeta gamma\ndelta\n' | while IFS= read -r line; do
        echo "  xử lý dòng: [$line]"
    done
    # recon: while IFS= read -r host; do nmap -Pn -F "$host"; done < hosts.txt
    # Vì sao IFS= và -r: tránh bash tự cắt khoảng trắng đầu/cuối dòng và
    # tránh hiểu nhầm dấu "\" trong dòng thành ký tự escape.
}

demo_full_chain() {
    echo "== 6) Chuỗi pipeline thật (chỉ in ra - cần cài tool mới chạy được) =="
    cat <<'EOF'
    subfinder -d target.com -silent \
      | dnsx -silent \
      | httpx -silent -mc 200,301,302 \
      | tee alive.txt \
      | nuclei -tags cve,misconfig -silent
EOF
}

main() {
    demo_basic_pipe; echo
    demo_tee_branch; echo
    demo_xargs_parallel; echo
    demo_process_substitution; echo
    demo_while_read_loop; echo
    demo_full_chain
}

main

