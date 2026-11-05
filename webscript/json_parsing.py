#!/usr/bin/env python3

from __future__ import annotations
import json


# Giả lập output kiểu httpx -json (mỗi dòng 1 JSON object)
SAMPLE_JSONL = """
{"url": "https://a.target.com", "status_code": 200, "title": "A Site"}
{"url": "https://b.target.com", "status_code": 403, "title": "Forbidden"}
{"url": "https://c.target.com", "status_code": 200, "title": "C Site", "tech": ["nginx", "php"]}
not a json line - giả lập dòng log lẫn vào output thật
""".strip()


def parse_jsonl(text: str) -> list[dict]:
    """Cách ĐÚNG để đọc JSONL: parse từng dòng riêng, bỏ qua dòng lỗi."""
    results = []
    for line_num, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError as e:
            # thực tế output tool đôi khi có dòng log/warning lẫn vào
            # -> không nên để 1 dòng lỗi làm crash cả chương trình
            print(f"[!] Bỏ qua dòng {line_num} (không phải JSON hợp lệ): {e}")
    return results


def parse_jsonl_file(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return parse_jsonl(f.read())


def extract_alive_200(records: list[dict]) -> list[str]:
    """Lọc field an toàn bằng .get() - tránh KeyError nếu tool đổi field."""
    return [r["url"] for r in records if r.get("status_code") == 200]


def demo_wrong_way(text: str) -> None:
    """Minh hoạ lỗi hay gặp: cố json.loads() nguyên cả file JSONL."""
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[minh hoạ lỗi] json.loads() cả file JSONL -> lỗi: {e}")


if __name__ == "__main__":
    demo_wrong_way(SAMPLE_JSONL)
    print()

    records = parse_jsonl(SAMPLE_JSONL)
    print(f"\nĐọc được {len(records)} record hợp lệ")

    for r in records:
        # .get() với giá trị mặc định - an toàn hơn r["tech"] (có thể KeyError)
        tech = ", ".join(r.get("tech", [])) or "(không rõ)"
        print(f"  {r['url']:30s} status={r.get('status_code')} tech={tech}")

    print("\nURL trả 200:", extract_alive_200(records))

    # Áp dụng thực tế:
    # records = parse_jsonl_file("results/target.com/httpx_20260101.json")

    # TODO tự thử: viết hàm gộp kết quả từ 2 file JSONL (vd httpx.json
    # và nuclei.jsonl) theo field chung "url"/"host", loại trùng.
