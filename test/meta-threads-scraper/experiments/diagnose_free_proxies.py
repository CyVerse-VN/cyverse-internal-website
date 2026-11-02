import asyncio
import httpx
import time

URL = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt"

async def test_single_proxy(proxy_url: str):
    t0 = time.time()
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=4.0, verify=False) as client:
            resp = await client.get("http://icanhazip.com")
            if resp.status_code == 200:
                duration = round(time.time() - t0, 2)
                return proxy_url, duration, resp.text.strip()
    except Exception as e:
        return proxy_url, None, type(e).__name__

async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(URL)
        proxies = [l.strip() for l in res.text.splitlines() if l.strip()]

    print(f"Testing 50 HTTP proxies from Proxifly...")
    tasks = [test_single_proxy(p) for p in proxies[:50]]
    results = await asyncio.gather(*tasks)
    
    alive = [r for r in results if r[1] is not None]
    print(f"Alive: {len(alive)}/{len(results)}")
    for p, dur, ip in alive:
        print(f"  [LIVE] {p} -> {dur}s (IP: {ip})")

if __name__ == "__main__":
    asyncio.run(main())
