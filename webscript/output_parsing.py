#!/usr/bin/env python3

from __future__ import annotations
import re


# Giả lập output nmap -oG - (greppable) - mỗi host 1 dòng, dễ parse
# hơn NHIỀU so với output -oN (text đẹp cho người đọc, khó parse).
SAMPLE_GREPABLE = (
    "Host: 10.0.0.5 ()\tPorts: 22/open/tcp//ssh///, 80/open/tcp//http///, "
    "443/closed/tcp//https///\n"
    "Host: 10.0.0.6 ()\tPorts: 3306/open/tcp//mysql///\n"
)

# Giả lập output nmap -oN (text thường - khó parse hơn, minh hoạ vì
# sao nên tránh parse kiểu này nếu tool có sẵn định dạng dễ hơn)
SAMPLE_NORMAL = """
PORT     STATE  SERVICE
22/tcp   open   ssh
80/tcp   open   http
443/tcp  closed https
"""


def parse_nmap_greppable(text: str) -> dict[str, list[dict]]:
    """Parse -oG: tách host + list port (state, protocol, service)."""
    result: dict[str, list[dict]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("Host:"):
            continue
        host_match = re.match(r"Host:\s+(\S+)", line)
        if not host_match:
            continue
        host = host_match.group(1)

        ports_part = line.split("Ports:", 1)[-1] if "Ports:" in line else ""
        ports = []
        for entry in ports_part.split(","):
            fields = entry.strip().split("/")
            if len(fields) >= 4 and fields[0]:
                ports.append({
                    "port": fields[0],
                    "state": fields[1],
                    "proto": fields[2],
                    "service": fields[4] if len(fields) > 4 else "",
                })
        result[host] = ports
    return result


def parse_nmap_normal(text: str) -> list[dict]:
    """
    Parse -oN bằng regex neo đúng định dạng "PORT/proto  STATE  SERVICE".
    Dễ vỡ hơn bản greppable nếu nmap đổi format ở version khác.
    """
    pattern = re.compile(r"^(\d+)/(\w+)\s+(\S+)\s+(\S+)", re.MULTILINE)
    return [
        {"port": m.group(1), "proto": m.group(2), "state": m.group(3), "service": m.group(4)}
        for m in pattern.finditer(text)
    ]


def parse_dig_short(text: str) -> list[str]:
    """Parse output của `dig target.com A +short` - mỗi dòng 1 IP."""
    return [line.strip() for line in text.splitlines() if line.strip()]


if __name__ == "__main__":
    print("== Parse -oG (nên ưu tiên dùng kiểu này) ==")
    parsed = parse_nmap_greppable(SAMPLE_GREPABLE)
    for host, ports in parsed.items():
        open_ports = [p["port"] for p in ports if p["state"] == "open"]
        print(f"  {host}: port mở = {open_ports}")

    print("\n== Parse -oN bằng regex (khi buộc phải làm vậy) ==")
    for entry in parse_nmap_normal(SAMPLE_NORMAL):
        print(f"  {entry}")

    print("\n== Parse dig +short ==")
    dig_output = "1.2.3.4\n5.6.7.8\n"
    print(f"  {parse_dig_short(dig_output)}")

    # TODO tự thử: chạy `nmap -Pn -F -oG - <target thật>`, lưu output
    # vào file rồi đọc bằng parse_nmap_greppable() thay vì dữ liệu giả.
