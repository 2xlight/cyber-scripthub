#!/usr/bin/env python3

from __future__ import annotations
import asyncio
import aiohttp


# Semaphore giới hạn số lượng request/tiến trình chạy đồng thời.
# Không giới hạn -> asyncio.gather bắn hết N request cùng lúc, dễ bị
# target/WAF chặn hoặc làm chính máy mình quá tải (quá nhiều socket).
CONCURRENCY_LIMIT = 10


async def probe_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, host: str) -> dict:
    async with sem:   # chỉ cho tối đa CONCURRENCY_LIMIT task chạy cùng lúc
        url = host if host.startswith("http") else f"https://{host}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return {"host": host, "status": resp.status, "ok": True}
        except Exception as e:
            return {"host": host, "error": type(e).__name__, "ok": False}


async def probe_all(hosts: list[str]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with aiohttp.ClientSession() as session:
        tasks = [probe_one(session, sem, h) for h in hosts]
        return await asyncio.gather(*tasks)


async def run_external_tool(cmd: list[str], sem: asyncio.Semaphore) -> tuple[list[str], str]:
    """
    Chạy 1 tiến trình bên ngoài (vd nmap) bất đồng bộ - khác
    subprocess.run thường (block hoàn toàn), cái này cho phép nhiều
    tiến trình chạy song song mà không cần thread/multiprocessing.
    """
    async with sem:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await proc.communicate()
        return cmd, stdout.decode(errors="ignore")


async def demo_external_tools_parallel(hosts: list[str]) -> None:
    """Giả lập chạy 1 external tool cho từng host, song song có giới hạn."""
    sem = asyncio.Semaphore(3)
    tasks = [
        run_external_tool(["bash", "-c", f"echo scanning {h}; sleep 0.5; echo done {h}"], sem)
        for h in hosts
    ]
    for cmd, output in await asyncio.gather(*tasks):
        print(f"--- {' '.join(cmd[:1])} ... ---")
        print(output.strip())
    # recon thật: run_external_tool(["nmap", "-Pn", "-F", host], sem)


if __name__ == "__main__":
    demo_hosts = ["example.com", "python.org", "wikipedia.org"]

    print("== 1) HTTP probe song song (aiohttp + Semaphore) ==")
    results = asyncio.run(probe_all(demo_hosts))
    for r in results:
        print(r)

    print("\n== 2) Chạy nhiều external tool song song qua asyncio subprocess ==")
    asyncio.run(demo_external_tools_parallel(demo_hosts))

    # TODO tự thử: đọc hosts từ file (vd output httpx của recon.sh),
    # chạy probe_all(), rồi lọc/in ra những host status != 200.
