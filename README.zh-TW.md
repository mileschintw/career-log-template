[English](README.md) | 繁體中文

# career-log：給 Claude Code、Codex、Cursor 和 Antigravity 用的 AI 職涯日誌與履歷產生器

![Claude Code: tested](https://img.shields.io/badge/Claude_Code-tested-2ea44f) ![Codex: should work](https://img.shields.io/badge/Codex-should_work-blue) ![Cursor: should work](https://img.shields.io/badge/Cursor-should_work-blue) ![Antigravity: should work](https://img.shields.io/badge/Antigravity-should_work-blue)

![macOS](https://img.shields.io/badge/macOS-supported-2ea44f) ![Windows](https://img.shields.io/badge/Windows-supported-2ea44f) ![Linux](https://img.shields.io/badge/Linux-supported-2ea44f)

[![觀看 career-log-template 一分鐘影片導覽](https://gitdiagram.com/video-badge.svg)](https://gitdiagram.com/mileschintw/career-log-template/video)

這是一個 GitHub template，用 git 保存職涯日誌（也就是「brag document」），再讓你的 AI coding agent 把它變成量身打造的履歷、求職信、申請表答案和面試準備。它寫出的每一句話都能追溯到一筆有日期的記錄，所以 agent 不會憑空捏造，你記下的事也不會遺失。

- **手上有什麼就全部交給它。** 不必自己把經歷打進去。把舊履歷和 CV、自我介紹、報告、LinkedIn 匯出檔和 AI 聊天記錄交給 agent，或讓它讀取你要登入才看得到的網站。它會把這些併成每段經歷一筆條目。
- **不用學指令。** 呼叫 skill，用你自己的話、任何語言說你想做什麼。它會依你的要求選對模式，一步步帶你完成。
- **在任何專案裡隨時記錄。** PR 合併、專案收尾，或有其他值得記下的事，在你當下所在的 session 說「log this to my career log」。它會加上一行有日期的記錄並 commit，不會打斷你手上的工作。
- **規則可以由你改寫。** [writing.md](skills/career-log/writing.md) 裡的寫作規則是預設值。你在 `direction.md` 寫下的偏好與它不同時，以你的為準；你在使用過程中說出的偏好，skill 也會記下來，所以規則會隨著使用越來越貼近你。你的背景也是設定的一部分，而不是內建的假設：需不需要簽證贊助、雇主怎麼排序、每個履歷版本以什麼為重點（見[你的設定](#你的設定)）。
- **你的作業系統、你的 agent。** 支援 macOS、Windows 和 Linux，可搭配 Claude Code、Codex、Cursor 和 Antigravity 使用。目前只有 [Claude Code](https://claude.com/claude-code) 完整測過；其他應該大致可用，但沒在 Windows 上測過。

![career-log：工作當下就記下來，之後從記錄寫出量身打造的履歷](docs/social-preview/social-preview.svg)

## 快速開始

1. 在 GitHub 按 **Use this template** 建立自己的 repo，並設為 **Private**：這裡會放你的個人經歷。
2. 把它 clone 到電腦上，在 repo 根目錄開你的 coding agent，對它說「照 SETUP.md 幫我設定這台電腦」。它會設定 git 身分、把 skill 連到你的 agent 讀取的 skill 資料夾（SETUP.md 第 4 步）、問你這台電腦要裝哪些選用工具（做履歷 PDF 的 LaTeX 工具、讀網站的 `playwright-cli`），只裝在你的使用者帳號下，並跑檢查。
3. 手上有什麼就交出來。把舊履歷和 CV（PDF、`.tex`、Word）、自我介紹、報告和 LinkedIn 匯出檔放進 `sources/inbox/`，說「import my old resumes」。AI 聊天記錄就說「import my ChatGPT history」（或 Claude、Gemini、Perplexity），agent 會告訴你怎麼匯出；下載下來的檔案原樣放進來就好，壓縮或解壓縮都可以，agent 會自己找到裡面的匯出檔。已登入的網站就說出網站名稱；agent 會用 `playwright-cli` 讀取，第一次用到時它會提議幫你安裝，除非你在 setup 已經選了要或不要（SETUP.md 第 5 步），或改用它自己的瀏覽器工具。
4. 之後在任何專案完成一件值得記的事，說「log this to my career log」；要投履歷時，貼職缺網址說「apply to <網址>」；要一份可重複使用的版本，就說「write a backend engineer resume」。

你對新 Log 的第一個請求會先啟動 setup，setup 完成前其他功能都不會執行：一輪五個問題，每題都有建議答案，可以直接接受。目標職位，以及工作身分和其他硬性條件（任一題都可以跳過，留空），記錄語言（英文），這台電腦要不要裝 `playwright-cli`（要），以及要不要把英文首頁 `README.md` 精簡成你自己記錄的索引（要：保留使用方式、你的設定、條目、檔案、上游和授權，刪掉其餘部分，並刪除這份中文翻譯）。見[你的設定](#你的設定)。

**系統管理員視窗。** setup 只裝在你的使用者帳號下，只有兩個步驟需要系統管理員權限：Mac 上沒有 Homebrew 時，它會安裝 Homebrew，這時會跳出系統的密碼視窗；Windows 上沒有 PDF 工具需要的 Visual C++ runtime 時，會跳出 UAC 視窗，它可能停在工作列上一個閃爍的盾牌按鈕後面。任何一個視窗跳出前，agent 都會先告訴你。請在電腦前回應它：你的密碼是交給作業系統，絕不會進到對話裡。在 Linux 上，需要 sudo 的步驟會印出來，讓你在自己的終端機執行。排程或無人執行的時候永遠不會跳出視窗。

你可以用任何語言跟你的 agent 對話。記錄預設用英文寫（想改就直接說），每份產出各自選語言。範例資料在 `skills/career-log/examples/`，只是格式示範，不會被當成你的經歷。

## 功能

- **職涯日誌 / brag document**：每份工作、專案或課程一個 Markdown 檔，內含待併入的有日期記錄，外加一份行為面試題的故事庫。
- **客製化履歷**：一頁的 LaTeX 履歷（ATS 友善的 PDF），由 `tools/resume.py` 編譯並檢查版面。可以針對單一職缺做一份（agent 會查這家公司做什麼產品、用什麼技術，決定履歷以什麼為重點）、每個目標職位各做一份，或做一份通用版；每份都由第二個 agent 審閱（agent 支援的話會在背景進行，草稿一編譯好就先給你看），審閱通過之前不會存檔。第一次要某個職位的版本時，agent 會問你這份要以什麼為重點，並把答案存進 `direction.md`。
- **適合度判斷與技能缺口**：問你適不適合某個職缺，就會得到投或不投的判斷，不寫任何東西：拿你的硬性條件（例如工作身分）對照職缺、這個職位在你的目標裡排第幾，以及每項職缺要求和工作內容分成有記錄證明、程度不足、只是自稱，或缺口。想要的話，再針對缺口給一份以專案為主的學習計畫。一批職缺的話，則產出技能缺口熱圖和同樣的學習計畫。
- **投遞職缺**：說「apply to <職缺網址>」就直接做履歷，再依你的記錄回答申請表上的開放式問題。你可以把問題貼上來，或由 agent 在職缺本身的頁面上找（Ashby、Greenhouse）；問題藏在多步驟的申請流程後面時（Workday 之類），它會請你貼上來。表單其他欄位和投遞追蹤交給你自己的工具。針對單一職缺做的履歷，會和職缺、答案存在一起。之後的申請會沿用它的措辭和答案，除非你存成 Archived：只留作你寄出內容的記錄，不再沿用。你自己上傳的可重複使用版本，則用 git 歷史和投遞日期找回當時那份檔案（上傳時保留它的檔名）。
- **面試準備**：根據雇主會讀到的資料整理準備包，再進行模擬面試。
- **行為面試題**：準備一題或貼上一整串題目，不需要先有申請。agent 會列出你的日誌裡適合這類題目的故事，問你要用哪一個；日誌裡沒有的更好故事，會連同來源記進它的條目。你確認之後，它會為每種題目類型存下 Talking points：一句開場白和指向你記錄的提示句，下次遇到同類題目時就能直接用，並會先核對自那之後有沒有記錄被改過。
- **雇主排序**：先依你的硬性條件，再依你自己的排序方式（領域契合度、規模、薪資等），排序徵才博覽會的名單或職缺清單。
- **職缺掃描**：從你的職缺來源（你登入的求職網站、GitHub 上公開的職缺清單）收集新職缺，去掉已申請或已拒絕的，其餘先對照你的條目清單初篩，最好的幾個再做完整的適合度判斷並排名，存成一份報告。開啟自動撰稿時，前幾名會在草稿分支上備好履歷和回答，並列出每個代你做的判斷，等你接受後才成為申請。可以手動執行，也可以設成排程任務；它從不替你申請，也從不替你登入。
- **匯入**：把舊履歷和 CV（PDF、Word、LaTeX）、自我介紹、報告、LinkedIn 匯出檔、AI 聊天記錄（ChatGPT、Claude.ai、Gemini、Perplexity）和已登入的網站，併成每段經歷一筆條目。讀取網站，以及沒有匯出功能的 Perplexity，會用 `playwright-cli`（選用；agent 會提議安裝）或 agent 自己的瀏覽器工具。
- **來源追溯**：每份產出都附一張表，把每項陳述連到它的來源記錄。

## 寫作規則從哪裡來

[writing.md](skills/career-log/writing.md) 的每條規則都在小括號裡註明來源，分成兩種。

**公開的指南**，任何人都能查證：
- [r/EngineeringResumes wiki](https://www.reddit.com/r/EngineeringResumes/wiki/index/) 和它的 [sample bullet points](https://www.reddit.com/r/EngineeringResumes/wiki/sample-bullet-points/)（`r/ER`）：一頁、條列項目（bullet）的寫法（XYZ、STAR）、開頭動詞、Skills 區塊。
- [r/EngineeringResumes LaTeX 範本](https://github.com/r-engineeringresumes/resume-templates)（`r/ER`，MIT）：`tools/resume.py` 編譯並檢查的履歷版面。
- [humanizer](https://github.com/blader/humanizer)，根據 Wikipedia 的 [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)（`humanizer`）：AI 痕跡檢查。
- [r/cscareerquestions 履歷指南](https://www.reddit.com/r/cscareerquestions/comments/1577dm9/the_ultimate_guide_to_writing_your_resuume_for/)，作者是會審閱履歷的資深工程師（`r/csCQ`）：採用兩條規則，即什麼時候列 GPA，以及優先挑有真實使用者的專案。
- [Tech Interview Handbook 履歷指南](https://www.techinterviewhandbook.org/resume/)（`TIH`）：採用兩條規則，即縮寫要寫出全稱，以及用純文字檢查 ATS 的讀取。它的格式建議與 r/ER 衝突，其餘不採用。

**從真實求職得到的經驗**，是一般指南沒寫到的。來源是作者用這個 skill 準備真實申請時做的判斷（`practice`），以及招募人員、用人團隊的工程師和同儕的建議（`feedback`）。舉幾條：
- 條列先寫你做了什麼，數字放在後面：以數字開頭，讀者就找不到你的貢獻。（同儕的建議）
- 學生或應屆畢業生，畢業日期放在讀者一眼就看得到的地方。（招募人員的篩選順序，由同儕轉述）
- Skills 列出的技能，也要出現在某條條列裡：招募人員先拿 Skills 對照職缺，再找用到這些技能的經歷。（同一位招募人員的看法）
- 軟實力以 1–3 項證據寫進技術條列，不另開條列。（用人團隊工程師的建議）
- 指標的名稱要寫出確切量測的東西（「p95 queue wait」，而不是「p95 latency」）。（真實申請的審閱流程抓到的）
- 職缺用了概括性的詞時，把那個詞寫進條列，放在具體工具旁邊。（真實申請的關鍵字掃描分數偏低）
- 成果指標勝過「抓到多少失敗」的指標，測試數量也不算影響力。（作者撰寫時的判斷）

和這裡的每條規則一樣，這些都是你可以改寫的預設值（見本頁開頭）。

## 口說規則從哪裡來

[speaking.md](skills/career-log/speaking.md) 處理你在行為面試中口頭回答的內容，它的每條規則都在小括號裡註明來源。來源都是公開的指南，任何人都能查證：
- [Tech Interview Handbook 行為面試指南](https://www.techinterviewhandbook.org/behavioral-interview/)和它的[資深求職者指南](https://www.techinterviewhandbook.org/behavioral-interview-senior-candidates/)（`TIH`）：3–5 個核心故事、以學到的教訓收尾、資深職位或複雜的故事先講影響、呈現規模、準備重點而不是講稿、同一個故事調整後回答多種題目。
- [Hello Interview 行為面試課程](https://www.hellointerview.com/learn/behavioral/overview/introduction)（`HI`，部分內容需付費）：背景只給最少的必要資訊、3–5 個核心故事加上 5–7 個補缺口的故事、以教訓作為自然的結尾。
- [interviewing.io 對一家大型科技公司行為面試的指南](https://interviewing.io/guides/amazon-behavioral-interview)和 [Meta 如何評估行為面試](https://interviewing.io/blog/how-software-engineering-behavioral-interviews-are-evaluated-meta)（`iio`）：80% 的回答講你自己的部分、一個重點可能被追問 10–15 分鐘、以人數和團隊數呈現規模。
- 同一家公司官方的[面試建議](https://aboutamazon.com/news/workplace/amazon-interview-best-tips)和[面試常見錯誤](https://aboutamazon.com/news/workplace/amazon-jobs-interview-mistakes)（`employer`）：說「我」，不說「我們」；每個回答四分鐘以內；每題用不同的成就。
- Jacob Kaplan-Moss 談[「你帶過的專案」這一題](https://jacobian.org/2021/feb/9/interview-questions-project-you-led/)（`jacobian`）：面試官針對一個專案會問的追問。
- Wes Kao，[背景故事要短](https://newsletter.weskao.com/p/in-job-interviews-keep-your-backstory)（`Kao`）：背景 2–3 句、10–15 秒。

從真實面試得到的經驗（`practice`、`feedback`）會在出現時加進來。和寫作規則一樣，這些都是你可以改寫的預設值。

## 適用範圍與限制

這個 skill 是為**北美風格的英文履歷**設計的：一頁、遵循 [writing.md](skills/career-log/writing.md) 的規則、使用內附的 LaTeX 範本。你可以用任何語言跟 agent 對話，記錄也可以用任何語言寫；適用範圍指的是它產出的履歷。

其他語言和履歷風格要等三項規劃中的功能：自訂履歷範本、Typst 範本，以及 CJK（中文、日文、韓文）履歷。即使這些功能完成，其他語言或風格的履歷**效果可能仍不如**北美英文履歷。這些功能會延伸這套為北美風格建立並測試的設計，也不會另外加入針對其他市場調整的規則。

**模型。** `write`（履歷與申請問答）在 Claude Code 中用 Claude 模型測試的結果：

| 模型 | `write` |
|---|---|
| Opus、Sonnet | 已測試。建議用 Sonnet 或更高階的模型。 |
| Haiku | 可以用，但 humanizer 步驟不可靠（3 次測試有 2 次跳過，即使用 extra-high effort 也一樣），而且在 medium 和 high effort 下，子代理常常設定錯誤。 |

不論哪個模型，agent 有時都會漏寫啟動審查或 humanizer 子代理前的那行說明；子代理本身仍會執行。Sonnet 有時也會把子代理設定錯，但比 Haiku 少。

## 使用方式

呼叫 skill，說你想做什麼。`career-log` skill（在 [`skills/career-log/`](skills/career-log/SKILL.md)）連到你的 agent 讀取的 skill 資料夾之後（見 [SETUP.md](SETUP.md) 第 4 步），在 Claude Code、Codex、Cursor 或 Antigravity 的任何 session 都能用，並會依你的要求選模式。下表列出你可以要求的事。引號裡的句子只是範例，怎麼說都行。

| 你可以要求 | 模式 |
|---|---|
| "log this to my career log" | **log**：在某筆條目的待整理記錄加一行有日期的記錄 |
| "consolidate the <project> entry" | **consolidate**：補齊每個段落，針對缺口追問你 |
| "prep me for the <company> interview" | **interview**：根據對方會讀到的資料整理準備包，再進行模擬面試 |
| "help me prepare 'tell me about a conflict'"、"here are my BQs" | **stories**：每道行為面試題和你一起挑故事，補齊條目缺的內容，並為每種題目類型存下你確認過的 Talking points |
| "how well do I fit <posting URL>"、"what should I learn for these postings" | **fit**：判斷一個職缺投或不投，每項要求對應到能證明它的記錄；或針對多個職缺產出技能缺口熱圖。需要的話，再針對缺口給一份以專案為主的學習計畫 |
| "rank these career fair employers" | **rank**：依你的硬性條件和排序方式分級，並為每個沒被排除的雇主準備一句開場白 |
| "scan for new postings"、"scan twice a day"、"accept the <company> draft" | **scan**：從你的職缺來源找新職缺，去重、做適合度判斷並排名，存成報告；開啟自動撰稿時為前幾名備好草稿，並產生一頁結果儀表板。之後在這個或之後的工作階段接受或拒絕 |
| "apply to <posting URL>"、"write a backend engineer resume" | **write**：針對該職缺、目標職位或通用版的履歷，以及職缺開放式問題的答案。給雇主看的草稿會由第二個 agent 審閱，並附來源追溯表 |
| "import my old resumes"（檔案放在 `sources/inbox/`，或已登入的網站） | **import**：把舊文件併入條目 |
| "import my ChatGPT history"（或 Claude、Gemini、Perplexity） | **import**：告訴你怎麼匯出，逐一篩選每段對話，只複製你挑的那些；原始匯出檔不進 git |
| "audit my career log" | **audit**：列出缺少的故事、缺口和矛盾 |

日常保養：`log` 只是先記下來；請不時 consolidate 各條目，把待整理的記錄放進對應的段落，agent 也會針對缺口問你。`log` 和 `write` 會在某個條目該整理時提醒你，`audit` 則會排出哪些條目最該先整理。檔案裡不保留歷程，歷程交給 git。

建議安裝 GitHub CLI（`gh`），並為你的 Log 設好 GitHub remote。有 remote 時，你用的每台電腦都會拉到同一份 Log，`scan` 也會把草稿放在之後任何工作階段都打得開的分支上；沒有的話，草稿只留在產生它的那台電腦。有 `gh` 時，agent 會透過 API 讀 GitHub 上的內容（公開的職缺清單、作為來源的你自己的 repo 和 pull request），而不是讀網頁。

建議安裝 [humanizer](https://github.com/blader/humanizer) skill。不論有沒有裝，這個 skill 都會自己檢查 AI 寫作痕跡（[writing.md](skills/career-log/writing.md)）；裝了 humanizer 的話，每份要給雇主看的產出也會再跑一次 humanizer。

## 你的設定

skill 的部分行為取決於你是誰，而不是一般的履歷規則：需要簽證贊助的職位算不算出局、雇主排序時什麼優先、某個職位的履歷以什麼為重點。這些都不是寫死的，而是存在你 Log 裡兩個你可以查看的檔案：`direction.md` 放你想要什麼（Direction），`config.toml` 放 skill 怎麼運作（Config）。

| 項目 | 影響什麼 | 存在哪裡 | 還沒設定時 |
|---|---|---|---|
| 目標職位 | 適合度判斷裡，職缺的職位在你的目標中排第幾；雇主排序時，領域契合度拿什麼來比 | `direction.md › Target roles, ranked` | 空的：適合度判斷不給排名、一批職缺時把每個職缺看得一樣重，雇主排序則依你的記錄顯示的領域，結果裡都會註明 |
| 工作身分 | 適合度判斷的投或不投，以及雇主排序要查什麼（簽證贊助、公民身分、安全許可） | `direction.md › Constraints` | 空的：適合度判斷不因它擋下職缺，會列出職缺的相關要求讓你自己確認；雇主排序不因它把雇主排除；面試準備把這題列為沒準備；結果裡都會註明。針對職缺做履歷時不會因此停下：它會引述職缺裡和簽證贊助有關的文字，讓你自己確認 |
| 其他硬性條件（地點、到職日、職級） | 同樣影響投或不投 | `direction.md › Constraints` | 沒有限制 |
| 雇主排序方式 | 過了硬性條件之後，`rank` 怎麼排雇主 | `direction.md › Employer preferences` | 先看領域契合度，再看規模和薪資；排序結果會註明 |
| 履歷版本的重點 | 每個目標版本先放哪些記錄、略過哪些，以及往回收錄幾年（預設約五年） | `direction.md › What to emphasise, by target` | 最符合那個目標的記錄；草稿會註明 |
| 寫作偏好 | 改寫 [writing.md](skills/career-log/writing.md) 裡的規則 | `direction.md › Writing preferences for applications` | 照 writing.md |
| 記錄語言 | Log 檔案用什麼語言寫 | `config.toml` 的 `record_language` | 英文 |
| 面試官資料 | 面試準備要不要讀只有登入會員才看得到的面試官資料（LinkedIn） | `config.toml` 的 `interviewer_profiles` | `never`：只讀公開頁面 |
| 首頁 | 這一頁有沒有精簡成個人索引 | `config.toml` 的 `front_page` | `full` |
| 掃描範圍 | `scan` 收集幾天內張貼的職缺；排程執行可以另設 | `config.toml` 的 `window` 和 `scheduled_window` | 7 天；排程執行相同 |
| 掃描數量 | `scan` 初篩幾個職缺，其中幾個做完整的適合度判斷，報告列前幾名 | `config.toml` 的 `screen_budget`、`fit_budget` 和 `n` | 初篩 40 個，判斷 15 個，列前 10 名 |
| 自動撰稿 | `scan` 要不要為前幾名職缺撰寫履歷和回答，以及幾個 | `config.toml` 的 `auto_write` 和 `m` | `off`；開啟時 5 個（最多 20） |
| 掃描來源 | `scan` 讀哪些求職網站和清單，以及上次怎麼讀 | `scan-sources.md` | 第一次掃描時詢問 |
| 這台電腦的 `playwright-cli` | skill 能不能讀需要執行腳本或登入的網頁 | `~/.career-log/machine.toml`，在 repo 之外 | setup 時會問你；換一台電腦時，第一次有模式需要時會問你 |

`profile.md` 裡的事實也會影響產出，但它們是記錄，不是設定：例如投遞類型不同、畢業日期也不同時，只有 `profile.md › Education` 和它的 Conflicts 有記錄才會用到。

**快速或進階。** 快速 setup 就是上面那一輪。想看到每一項、以目前的值為預選並修改任何一項，就說要進階 setup。從匯入的資料（舊履歷、聊天記錄）裡找到的工作身分或目標職位，不會直接套用：匯入報告會列出來，由你透過 setup 採用。

**怎麼修改。** 在對話裡用你自己的話說就好：「我不需要簽證贊助」、「雇主排序以薪資優先」、「之後記錄都用中文寫」。agent 會把它對應到會改變的項目，逐項給你看改之前和改之後，你說好才連同日期寫進去並 commit。「沒有」也是答案：「沒有限制」會像其他答案一樣記下來。只針對這一次請求說的話（「這次先不要放那份實習」）只改這一次，不會記下來。

## 條目

條目索引只放在英文版 [README.md](README.md#entries)，你每記一筆，skill 就會更新它。

## 檔案

- [`profile.md`](profile.md)：聯絡方式、學歷、語言、技能摘要
- [`stories.md`](stories.md)：行為面試題類型 → 故事，以及常見申請題 → 素材
- `stories/`：Talking points，每種行為面試題類型一個檔，你確認後才存；`stories/wordings/` 依題型逐字記下你被問過的每道題，讓下一道題能對上它的題型
- [`applications.md`](applications.md)：徵才博覽會、招募人員聯絡記錄、在申請之外寄出的履歷版本，以及在 `outputs/applications/` 底下沒有資料夾的申請
- [`direction.md`](direction.md)：目標職位、雇主偏好、限制條件、要強調的重點、語言
- `config.toml`：skill 在這個 Log 怎麼運作（記錄語言、面試官資料、首頁、掃描設定），由 setup 寫入；預設值在 `tools/config.default.toml`
- `scan-sources.md`：`scan` 讀的職缺來源，第一次掃描時寫入
- `entries/`：每段經歷一個檔案；太長的經歷拆成一個系列（series），每部分一個檔案（[範本](entries/_template.md)）
- `outputs/`：產出的文件，除了儀表板，每份都附來源追溯表：`applications/`（每個申請一個資料夾，送出後就不再更動）、`resumes/`（每個履歷方向一份持續更新的檔案，舊版本留在 git 歷史裡）、`reports/`（加上日期的排名、掃描報告和其他報告）和 `dashboard/`（掃描儀表板，由 `dashboard.py` 重新產生）
- [`SETUP.md`](SETUP.md)：每台電腦的設定（macOS、Windows、Linux）
- `tools/`：機器設定腳本和 `check.py`（skill 每次處理要求前檢查這台電腦的腳本）、`resume.py`（編譯並檢查履歷版面；用法見 [latex.md](skills/career-log/latex.md)）、`chat_export.py`（篩選並擷取 AI 聊天匯出檔，以及摘錄代理工作階段；用法見 [import-chats.md](skills/career-log/modes/import-chats.md) 和 [excerpts.md](skills/career-log/excerpts.md)）和它在 `tools/tests/` 的測試、`scan.py`（`scan` 的機械步驟：報告命名、去重、初篩的排序與重用、清理、待處理清單）、`dashboard.py`（從 Log 產生掃描儀表板頁面），以及 `export-template.sh`（從你的 repo 建出可分享的 Template）
- `skills/career-log/`：skill 本身、它的[寫作標準](skills/career-log/writing.md)、[口說標準](skills/career-log/speaking.md)和[範例](skills/career-log/examples/README.md)
- `sources/`：匯入的原始檔、代理工作階段的摘錄、匯入收件匣（`inbox/`）、[匯入記錄](sources/import-log.md)和[來源代號](sources/keys.md)
- [`GLOSSARY.md`](GLOSSARY.md) 和 [`docs/adr/`](docs/adr/)：這個 repo 的詞彙和設計決策

## 上游

這個 repo 是從 https://github.com/mileschintw/career-log-template 這個 Template 建立的。聊天匯出格式改了或某個步驟壞了，請到那裡回報：開 issue（用「Chat export format changed」表單）或發 pull request。Issue 是公開的：只附欄位名稱和結構，絕不附你的記錄。import 模式會幫你草擬回報，貼出前會先問你（[import-chats.md](skills/career-log/modes/import-chats.md) 第 8 步）。

## 授權

MIT，見 [LICENSE](LICENSE)。範例履歷改自 [r/EngineeringResumes 範本](https://github.com/r-engineeringresumes/resume-templates)（MIT）。
