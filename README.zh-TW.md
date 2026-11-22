[English](README.md) | 繁體中文

# career-log：給 Claude Code、Codex、Cursor 和 Antigravity 用的 AI 職涯日誌與履歷產生器

![Claude Code: tested](https://img.shields.io/badge/Claude_Code-tested-2ea44f) ![Codex: should work](https://img.shields.io/badge/Codex-should_work-blue) ![Cursor: should work](https://img.shields.io/badge/Cursor-should_work-blue) ![Antigravity: should work](https://img.shields.io/badge/Antigravity-should_work-blue)

![macOS](https://img.shields.io/badge/macOS-supported-2ea44f) ![Windows](https://img.shields.io/badge/Windows-supported-2ea44f) ![Linux](https://img.shields.io/badge/Linux-supported-2ea44f)

[![觀看 career-log-template 一分鐘影片導覽](https://gitdiagram.com/video-badge.svg)](https://gitdiagram.com/mileschintw/career-log-template/video)

這是一個 GitHub template，用 git 保存職涯日誌（也就是「brag document」），再讓你的 AI coding agent 把它變成量身打造的履歷、求職信、申請表答案和面試準備。它寫出的每一句話都能追溯到一筆有日期的記錄，所以 agent 不會憑空捏造，你記下的事也不會遺失。

- **手上有什麼就交給它：** 舊履歷、LinkedIn 匯出檔、AI 聊天記錄。不必自己把經歷打進去。
- **不用學指令：** 用你自己的話、任何語言說你想做什麼。
- **在任何專案裡記錄：** 說「log this to my career log」，它就加上一行有日期的記錄，不會打斷你手上的工作。

![career-log：工作當下就記下來，之後從記錄寫出量身打造的履歷](docs/social-preview/banner.svg)

## 快速開始

1. 在 GitHub 按 **Use this template**，並把你的 repo 設為 **Private**：這裡會放你的個人經歷。
2. 把它 clone 下來，在 repo 裡開你的 coding agent，對它說：**「introduce this repo and set me up」**（用中文說也可以）。它會告訴你它能做什麼、設定這台電腦（只裝在你的使用者帳號下），並問你幾個問題，每題都附建議答案。
3. 把手上有的交給它（「import my old resumes」），再提出你要的東西（「apply to <職缺網址>」）。不知道下一步做什麼？問它「what next?」。

## 支援

- **作業系統：** macOS、Windows 和 Linux。
- **Agent：** 已在 [Claude Code](https://claude.com/claude-code) 測過（Opus 和 Sonnet；建議用 Sonnet 以上）。Codex、Cursor 和 Antigravity 應該可用，但沒有測過。
- **模型測試結果：** 各模式的測試結果，以及為什麼不支援 Haiku：[ADR 0008](docs/adr/0008-sonnet-is-the-lowest-supported-model.md)（英文）。
- **履歷：** 北美風格的一頁英文履歷。你和你的記錄可以用任何語言。

**更多：** [guide](docs/guide.md)（英文）列出每個模式和範例說法、設定項目、檔案地圖，以及寫作規則的來源；[SETUP.md](SETUP.md) 是每台電腦的設定。

## 條目

條目索引只放在英文版 [README.md](README.md#entries)，你每記一筆，skill 就會更新它。

## Engine repo

這個 repo 是從 https://github.com/mileschintw/career-log-template 這個 Template 建立的，而 Template 是 Engine repo（https://github.com/mileschintw/career-log-engine）的匯出。聊天匯出格式改了或某個步驟壞了，請到 Engine repo 回報：開 [issue](https://github.com/mileschintw/career-log-engine/issues) 或發 pull request。每個修正都在那裡做，Template 不收。Issue 是公開的：只附欄位名稱和結構，絕不附你的記錄。import 模式會幫你草擬回報，貼出前會先問你（[import-chats.md](skills/career-log/modes/import-chats.md) 第 8 步）。

## 升級

要把這個 Log 升到較新的 Template，請跟你的 agent 說「升級到最新的 Template」。upgrade 模式（[upgrade.md](skills/career-log/modes/upgrade.md)）會抓下那個版本、換掉 Engine（skill、`tools/` 和 Template 附的其他檔案）、跟你一起依序跑中間每個版本的升級指引（某個版本要改你記錄的格式，就在指引裡做，並先問你），每個版本的步驟各 commit 一次。它只從乾淨的 working tree 開始，在你對整個升級說好之前什麼都不 push；在那之前，你都可以讓 Log 回到升級開始前的那個 commit。每個版本改了什麼，寫在 Template 的 [Releases](https://github.com/mileschintw/career-log-template/releases) 頁面。

兩個版本之間，Engine repo 會發布 **Dev build**：它的 [`builds`](https://github.com/mileschintw/career-log-engine/tree/builds) 分支上的 tag `v<next version>-dev.<n>`。沒有任何一個保證穩定。

你改過的 Engine 檔會怎樣：

- **你編輯過的檔案**會被換成新版本的。接著 agent 會一個檔案一個檔案問你要不要把你的修改合併回去，並讓你看每一處合併後的改動落在哪裡。你的版本也留在 git 歷史裡。
- **衝突**是新版本改到和你同樣的幾行。檔案裡會用衝突標記把兩邊都留著；agent 會逐一給你看兩邊，由你選你的、新版本的，或兩者混合。每個衝突都解決之前，什麼都不會 commit。
- **新版本拿掉的檔案**會被刪除。如果你改過它，agent 會給你看你的版本，問你要留下當成你自己的檔案，還是放掉。
- **你自己加的檔案**（你自己的模式或工具）會留著。如果某個版本在同一個路徑放了自己的檔案，就由新版本的取代，agent 會提議把你的搬到別的路徑。
- **你刪掉的檔案**會照新版本的樣子回來。
- **你自己加的 `.gitignore` 行**會直接放回去，不會問你。

升級支援 0.2.0 起的 Log。比它更舊的 Log 要照 [v0.3.2 的說明](https://github.com/mileschintw/career-log-template/releases/tag/v0.3.2)先升到 v0.3.2，再從 0.3.2 升一次。

## 授權

MIT，見 [LICENSE](LICENSE)。範例履歷改自 [r/EngineeringResumes 範本](https://github.com/r-engineeringresumes/resume-templates)（MIT）。
