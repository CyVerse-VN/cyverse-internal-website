import asyncio
import httpx
import time

PROXIFLY_HTTP_URL = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt"
PROXIFLY_HTTPS_URL = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/https/data.txt"

async def test_single_proxy(proxy_url: str, test_target: str = "https://httpbin.org/ip", timeout: float = 3.0):
    t0 = time.time()
    try:
        async with httpx.AsyncClient(proxies=proxy_url, timeout=timeout) as client:
            resp = await client.get(test_target)
            if resp.status_code == 200:
                duration = round(time.time() - t0, 2)
                return proxy_url, duration
    except Exception:
        pass
    return None

async def find_working_proxies(limit_to_check: int = 50, need_working: int = 5):
    print("Fetching proxy list from Proxifly CDN...")
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(PROXIFLY_HTTPS_URL)
        proxies = [line.strip() for line in res.text.splitlines() if line.strip()]

    print(f"Downloaded {len(proxies)} proxies from Proxifly. Testing top {limit_to_check}...")
    
    candidates = proxies[:limit_to_check]
    tasks = [test_single_proxy(p) for p in candidates]
    
    results = await asyncio.gather(*tasks)
    working = [r for r in results if r is not None]
    working.sort(key=lambda x: x[1])  # sort by latency
    
    print(f"\nFound {len(working)} working proxies out of {limit_to_check} tested:")
    for p, latency in working[:need_working]:
        print(f"  [ALIVE] {p} (Response: {latency}s)")
    return [p for p, _ in working[:need_working]]

if __name__ == "__main__":
    asyncio.run(find_working_proxies(limit_to_check=60, need_working=5))
