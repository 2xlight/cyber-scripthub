#!/usr/bin/env python3

from __future__ import annotations
import subprocess


def run_simple(cmd: list[str]) -> str:
    """
    Cách cơ bản nhất: chạy xong mới lấy được output (không stream).
    Dùng cho lệnh chạy nhanh, output không quá lớn.
    """
    result = subprocess.run(
        cmd,
        capture_output=True,   # bắt cả stdout và stderr
        text=True,             # trả về str thay vì bytes
        timeout=30,             # tránh treo vô hạn nếu tool bị đứng
    )
    if result.returncode != 0:
        print(f"[!] Lệnh lỗi (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def run_safe_with_check(cmd: list[str]) -> str | None:
    """
    check=True: tự raise CalledProcessError nếu lệnh exit khác 0,
    tiện khi muốn code dừng ngay lúc lỗi thay vì tự if/else.
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=30, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[!] {cmd[0]} thất bại: {e.stderr.strip()}")
        return None
    except subprocess.TimeoutExpired:
        print(f"[!] {cmd[0]} timeout.")
        return None


def run_streaming(cmd: list[str]) -> int:
    """
    Popen: đọc output theo THỜI GIAN THỰC (từng dòng), hữu ích cho
    lệnh chạy lâu như nmap full port - không phải đợi xong mới thấy gì.
    """
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,   # line-buffered
    )
    for line in process.stdout:
        print(f"  > {line.rstrip()}")
    process.wait()
    return process.returncode


if __name__ == "__main__":
    # Ví dụ chạy thử với lệnh có sẵn trên mọi máy Linux (không cần
    # cài pentest tool để test file này):
    print("--- run_simple ---")
    print(run_simple(["echo", "hello from subprocess"]))

    print("--- run_safe_with_check (lỗi cố ý) ---")
    run_safe_with_check(["ls", "/duong-dan-khong-ton-tai"])

    print("--- run_streaming ---")
    # Giả lập 1 tool chạy lâu, in output theo thời gian thực (thay
    # cho "ping"/"nmap" - không phải máy nào cũng có sẵn 2 lệnh này):
    run_streaming(["bash", "-c", "for i in 1 2 3; do echo line $i; sleep 0.3; done"])

    # Áp dụng thực tế cho recon:
    # run_streaming(["nmap", "-Pn", "-sV", "target.com"])
    # run_safe_with_check(["subfinder", "-d", "target.com", "-silent"])

    # TODO tự thử: viết hàm run_with_retry() tự động chạy lại 1 lần
    # nếu bị TimeoutExpired.
