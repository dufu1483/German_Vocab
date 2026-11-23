import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get("PLAYWRIGHT_CHANNEL"))
    page = browser.new_page(viewport={"width": 375, "height": 780})
    page.goto((Path("dist") / "index.html").resolve().as_uri())
    page.get_by_role("checkbox", name="全選類別").uncheck(timeout=3000)
    page.get_by_role("checkbox", name="Obst（水果）").check()
    page.get_by_role("button", name="開始練習").click()
    for _ in range(4):
        page.get_by_role("button", name="看解答").click()
        page.get_by_role("button", name="下一題").click()
    expect(page.get_by_text("第一次全對 0 / 4")).to_be_visible()
    page.get_by_role("button", name="重練錯題").click()
    expect(page.get_by_text("第 1 / 4 題")).to_be_visible()
    browser.close()

    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    handler = partial(SimpleHTTPRequestHandler, directory=Path.cwd())
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            desktop = playwright.chromium.launch(channel=os.environ.get("PLAYWRIGHT_CHANNEL"))
            page = desktop.new_page()
            page.add_init_script("Math.random = () => 0.999")
            page.goto(f"http://127.0.0.1:{server.server_port}/dist/index.html")
            page.get_by_role("checkbox", name="全選類別").uncheck()
            page.get_by_role("checkbox", name="Obst（水果）").check()
            with page.expect_response(lambda response: response.url.endswith(".mp3") and response.ok):
                page.get_by_role("button", name="開始練習").click()
            expect(page.get_by_label("複數（含 die）")).to_be_hidden()
            page.get_by_label("單數（含冠詞）").fill("das Obst")
            page.get_by_role("button", name="檢查答案").click()
            page.get_by_role("button", name="下一題").click()
            page.get_by_label("單數（含冠詞）").fill("der apfel")
            page.get_by_label("複數（含 die）").fill("die  A\u0308pfel")
            page.get_by_role("button", name="檢查答案").click()
            expect(page.get_by_label("單數（含冠詞）")).to_have_attribute("aria-invalid", "true")
            expect(page.get_by_label("複數（含 die）")).to_have_attribute("aria-invalid", "false")
            page.get_by_label("單數（含冠詞）").fill("der Apfel")
            page.get_by_role("button", name="檢查答案").click()
            expect(page.get_by_text("答對了")).to_be_visible()

            failure = desktop.new_page()
            failure.route("**/*.mp3", lambda route: route.abort())
            failure.goto(f"http://127.0.0.1:{server.server_port}/dist/index.html")
            failure.get_by_role("button", name="開始練習").click()
            expect(failure.get_by_role("status")).to_contain_text("音檔播放失敗")
            failure.unroute("**/*.mp3")
            with failure.expect_response(lambda response: response.url.endswith(".mp3") and response.ok):
                failure.get_by_role("button", name="重試播放").click()
            desktop.close()
        finally:
            server.shutdown()
