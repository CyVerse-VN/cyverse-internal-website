import asyncio
from playwright.async_api import async_playwright

async def inspect_login_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.threads.com/login", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # Check inputs
        inputs = await page.evaluate('''() => {
            const list = [];
            document.querySelectorAll('input').forEach(i => {
                list.push({
                    name: i.getAttribute('name'),
                    type: i.getAttribute('type'),
                    placeholder: i.getAttribute('placeholder'),
                    autocomplete: i.getAttribute('autocomplete')
                });
            });
            return list;
        }''')
        print("Inputs found on /login:", inputs)
        
        buttons = await page.evaluate('''() => {
            const list = [];
            document.querySelectorAll('button, div[role="button"]').forEach(b => {
                list.push(b.innerText.trim());
            });
            return list.filter(Boolean);
        }''')
        print("Buttons found:", buttons[:10])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_login_page())
