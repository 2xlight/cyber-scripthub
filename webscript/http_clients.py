#!/usr/bin/env python3

from __future__ import annotations
import time
import asyncio

import requests
import httpx #pip install httpx
import aiohttp


URLS = [
    "https://example.com",
    "https://www.python.org",
    "https://httpstat.us/200",
]


def probe_with_requests(urls: list[str]) -> None:
    """Sync, chạy lần lượt từng URL - đơn giản nhưng CHẬM khi urls nhiều."""
    start = time.time()
    for url in urls:
        try:
            r = requests.get(url, timeout=5)
            print(f"[requests] {url} -> {r.status_code}")
        except requests.RequestException as e:
            print(f"[requests] {url} -> lỗi: {type(e).__name__}")
    print(f"requests: {time.time() - start:.2f}s\n")


def probe_with_httpx_sync(urls: list[str]) -> None:
    """httpx bản sync - API gần như y hệt requests."""
    start = time.time()
    with httpx.Client(timeout=5) as client:
        for url in urls:
            try:
                r = client.get(url)
                print(f"[httpx-sync] {url} -> {r.status_code}")
            except httpx.HTTPError as e:
                print(f"[httpx-sync] {url} -> lỗi: {type(e).__name__}")
    print(f"httpx sync: {time.time() - start:.2f}s\n")


async def probe_with_httpx_async(urls: list[str]) -> None:
    """httpx bản async - chạy SONG SONG thay vì lần lượt -> nhanh hơn hẳn."""
    start = time.time()
    async with httpx.AsyncClient(timeout=5) as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for url, resp in zip(urls, responses):
            if isinstance(resp, Exception):
                print(f"[httpx-async] {url} -> lỗi: {type(resp).__name__}")
            else:
                print(f"[httpx-async] {url} -> {resp.status_code}")
    print(f"httpx async: {time.time() - start:.2f}s\n")


async def probe_with_aiohttp(urls: list[str]) -> None:
    """aiohttp - cũng async, cú pháp dùng session.get() khác httpx 1 chút."""
    start = time.time()
    async with aiohttp.ClientSession() as session:
        async def fetch(url):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return url, resp.status
            except aiohttp.ClientError as e:
                return url, f"lỗi: {type(e).__name__}"

        results = await asyncio.gather(*(fetch(u) for u in urls))
        for url, status in results:
            print(f"[aiohttp] {url} -> {status}")
    print(f"aiohttp: {time.time() - start:.2f}s\n")


if __name__ == "__main__":
    probe_with_requests(URLS)
    probe_with_httpx_sync(URLS)
    asyncio.run(probe_with_httpx_async(URLS))
    asyncio.run(probe_with_aiohttp(URLS))

    # Với danh sách chỉ 3 URL, chênh lệch thời gian sync vs async chưa
    # rõ. Thử với 30-50 URL (vd subdomain đã probe từ recon.sh) sẽ
    # thấy async nhanh hơn hẳn vì không phải CHỜ tuần tự từng request.

    # TODO tự thử: đổi URLS thành list đọc từ file
    # "subdomains_resolved.txt", so sánh thời gian probe_with_requests()
    # vs probe_with_aiohttp() với vài chục URL thật.
