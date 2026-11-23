import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def reveal_round(page, size):
    answers = []
    for number in range(1, size + 1):
        expect(page.get_by_role("heading", name=f"第 {number} / {size} 題")).to_be_visible()
        page.get_by_role("button", name="看解答").click()
        answers.append(page.locator("#solution").inner_text())
        page.get_by_role("button", name="下一題").click()
    return answers


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

    limited = browser.new_page(viewport={"width": 375, "height": 780})
    limited.goto((Path("dist") / "index.html").resolve().as_uri())
    limit = limited.get_by_role("spinbutton", name="本輪最多幾個詞")
    default_round_count = re.compile(r"^本輪 10 題，")
    expect(limit).to_have_value("10", timeout=3000)
    expect(limited.get_by_text(default_round_count)).to_be_visible()
    limited.get_by_role("checkbox", name="全選類別").uncheck()
    limited.get_by_role("checkbox", name="Obst（水果）").check()
    limited.get_by_role("checkbox", name="Getränke（飲料）").check()
    start = limited.get_by_role("button", name="開始練習")
    for invalid in ("", "0", "-1", "2.5"):
        limit.fill(invalid)
        expect(start).to_be_disabled()
    limit.fill("4")
    expect(limited.get_by_text("本輪 4 題，共有 11 個詞可選", exact=True)).to_be_visible()
    start.click()
    first = reveal_round(limited, 4)
    limited.get_by_role("button", name="重練錯題").click()
    assert set(reveal_round(limited, 4)) == set(first)
    again = limited.get_by_role("button", name="原類別再練")
    again.click()
    second = reveal_round(limited, 4)
    again.click()
    third = reveal_round(limited, 3)
    assert len(set(first + second + third)) == 11
    again.click()
    expect(limited.get_by_role("heading", name="第 1 / 4 題")).to_be_visible()
    limited.get_by_role("button", name="返回課程").click()
    limited.get_by_role("checkbox", name="全部", exact=True).check()
    expect(limit).to_be_disabled()
    expect(limited.get_by_text("本輪 11 題，共有 11 個詞可選", exact=True)).to_be_visible()
    start.click()
    expect(limited.get_by_role("heading", name="第 1 / 11 題")).to_be_visible()

    resumed = browser.new_page()
    resumed.add_init_script("Math.random = () => 0.999")
    resumed.goto((Path("dist") / "index.html").resolve().as_uri())
    resumed.get_by_role("checkbox", name="全選類別").uncheck()
    resumed.get_by_role("checkbox", name="Obst（水果）").check()
    resume_limit = resumed.get_by_role("spinbutton", name="本輪最多幾個詞")
    resume_limit.fill("3")
    resume_start = resumed.get_by_role("button", name="開始練習")
    resume_start.click()
    resumed.get_by_label("單數（含冠詞）").fill("das Obst")
    resumed.get_by_role("button", name="檢查答案").click()
    expect(resumed.get_by_text("答對了")).to_be_visible()
    resumed.get_by_role("button", name="下一題").click()
    resumed.get_by_role("button", name="返回課程").click()
    resume_limit.fill("2")
    expect(resumed.get_by_text("本輪 2 題，共有 3 個詞可選", exact=True)).to_be_visible()
    resume_start.click()
    resumed.get_by_role("button", name="看解答").click()
    expect(resumed.locator("#solution")).to_contain_text("der Apfel")
    resumed.get_by_role("button", name="返回課程").click()
    expect(resumed.get_by_text("本輪 2 題，共有 2 個詞可選", exact=True)).to_be_visible()
    resumed.get_by_role("checkbox", name="Getränke（飲料）").check()
    expect(resumed.get_by_text("本輪 2 題，共有 11 個詞可選", exact=True)).to_be_visible()
    resume_start.click()
    resumed.get_by_role("button", name="看解答").click()
    expect(resumed.locator("#solution")).to_contain_text("das Obst")
    resumed.reload()
    expect(resume_limit).to_have_value("10")
    expect(resumed.get_by_text(default_round_count)).to_be_visible()
    resume_start.click()
    expect(resumed.get_by_role("heading", name="第 1 / 10 題")).to_be_visible()
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
