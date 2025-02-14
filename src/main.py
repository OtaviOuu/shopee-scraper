import nodriver as uc
from nodriver import *
import json
import base64
from rich.console import Console
import aiofiles


class ShopeeScraper:
    def __init__(self, browser):
        self.browser: Browser = browser
        self.latest_request_id = None
        self.page = None
        self.console = Console()

    async def _response_handler(self, event):
        if "rcmd_items" in event.response.url:
            self.console.print(f"Capturado: {event.response.url}")
            self.latest_request_id = event.request_id

    async def _get_response_body(self, page):
        if not self.latest_request_id:
            self.console.print(f"⚠️ Nenhuma resposta capturada na página {page}")
            return

        cmd = uc.cdp.network.get_response_body(self.latest_request_id)
        response = await self.page.send(cmd)

        if response:
            body, is_base64 = response
            if is_base64:
                body = base64.b64decode(body)
            try:
                data = json.loads(body)
                return data
            except json.JSONDecodeError:
                self.console.print(f"Resposta inválida:\n{body[:500]}...")
                return

    async def scrape(self, url):
        page = 0
        crawl = True
        json_list = []
        try:
            while crawl:
                self.page = await self.browser.get(f"{url}?page={page}")
                self.page.add_handler(
                    cdp.network.ResponseReceived, self._response_handler
                )
                await self.page.wait_for(
                    selector=".shop-search-result-view__item.col-xs-2-4"
                )

                page_data = await self._get_response_body(page)

                if page_data:
                    self.console.print_json(data=page_data)
                    json_list.append(page_data)
                    async with aiofiles.open("./data.json", "w") as f:
                        await f.write(
                            json.dumps(json_list, indent=4, ensure_ascii=False)
                        )
                page += 1
        except TimeoutError:
            self.console.print(f"⚠️ Página {url} não carregada")
            crawl = False
        self.console.print("🏁 Fim da execução")
        await self.browser.stop()


async def main():
    target_store = "https://shopee.com.br/spaceyy_oficial"

    browser = await uc.start(
        headless=False,
        browser_executable_path="/snap/bin/chromium",
        browser_args=["--no-sandbox", "--disable-gpu"],
        user_data_dir="./uc-user-data",
    )

    shopee = ShopeeScraper(browser)
    await shopee.scrape(target_store)
    browser.stop()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
