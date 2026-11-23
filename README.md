# 德文名詞聽寫

保留 `dist/index.html` 和旁邊的 `audio/` 資料夾，直接開啟 HTML 就能練習。

## 發布和新增課程

1. 將專案上傳到 GitHub 的 `main` 分支。在 **Settings → Pages → Build and deployment** 選 **GitHub Actions**。
2. 到 **Actions → Deploy German practice** 執行第一次部署。
3. 日後在 GitHub 的 `courses/` 目錄上傳新 TSV。檔名是課程名稱。欄名可從現有詞表複製，每列依序填類別、朗讀文字、含冠詞的單數、含冠詞的複數、中文詞義。空缺的詞形留空，答案變體以 `|` 分隔。
4. 提交到 `main` 後，Actions 會檢查詞表、補齊音檔，再發布。每個答案都須有正確冠詞，同一課的相同資料只需填一次。若詞表有誤，建置會回報檔名與行號。
5. Actions 會將音檔存到 `tts-audio` 分支，第一次執行時會自動建立。只在 `main` 更新課程；`tts-audio` 需要允許 GitHub Actions 寫入。產音或保存失敗時，GitHub Pages 會繼續提供上一個成功發布的版本。

## 在本機重新打包

```sh
python -m pip install -r requirements.txt
python build.py
python -m unittest discover -s tests
```

如已安裝 Python Playwright 及 Chromium，可執行 `python tests/browser_check.py`。Windows 也可設定環境變數 `PLAYWRIGHT_CHANNEL=msedge` 使用已安裝的 Edge。

新音檔由 gTTS 連線產生，已打包的音檔可直接播放。變更中文詞義或答案時，只要朗讀文字相同，就能重用音檔。
