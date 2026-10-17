[English](README.md) | 繁體中文

# career-log：給 Claude Code、Codex、Cursor 和 Antigravity 用的 AI 職涯日誌與履歷產生器

![macOS](https://img.shields.io/badge/macOS-supported-2ea44f) ![Windows](https://img.shields.io/badge/Windows-supported-2ea44f) ![Linux](https://img.shields.io/badge/Linux-supported-2ea44f) ![Claude Code: tested](https://img.shields.io/badge/Claude_Code-tested-2ea44f) ![Codex: should work](https://img.shields.io/badge/Codex-should_work-blue) ![Cursor: should work](https://img.shields.io/badge/Cursor-should_work-blue) ![Antigravity: should work](https://img.shields.io/badge/Antigravity-should_work-blue)

這是一個 GitHub template，用 git 保存職涯日誌（也就是「brag document」），再讓你的 AI coding agent 把它變成量身打造的履歷、求職信、申請表答案和面試準備。它寫出的每一句話都能追溯到一筆有日期的記錄，不會憑空捏造，也不會忘記。

- **手上有什麼就全部交給它。** 不必自己把經歷打進去。把舊履歷和 CV、自我介紹、報告、LinkedIn 匯出檔和 AI 聊天記錄交給 agent，或讓它用瀏覽器讀取你已登入的網站。它會把這些併成每段經歷一筆條目。
- **不用學指令。** 呼叫 skill，用你自己的話、任何語言說你想做什麼。它會依你的要求選對模式，一步步帶你完成。
- **在任何專案裡隨時記錄。** PR 合併、專案收尾，或有其他值得記下的事，在你當下所在的 session 說「log this to my career log」。它會加上一行有日期的記錄並 commit，不會打斷你手上的工作。
- **規則可以由你改寫。** [writing.md](skills/career-log/writing.md) 裡的寫作規則是預設值。你在 `direction.md` 寫下的偏好與它不同時，以你的為準；你在使用過程中說出的偏好，skill 也會記下來，所以規則會隨著使用越來越貼近你。
- **你的作業系統、你的 agent。** 支援 macOS、Windows 和 Linux，可搭配 Claude Code、Codex、Cursor 和 Antigravity 使用。目前只有 [Claude Code](https://claude.com/claude-code) 完整測過；其他應該大致可用，但沒在 Windows 上測過。

![career-log：工作當下就記下來，之後從記錄寫出量身打造的履歷](docs/social-preview/social-preview.svg)

## 功能

- **職涯日誌 / brag document**：每份工作、專案或課程一個 Markdown 檔，內含有日期的記錄，外加一份行為面試題的故事庫。
- **客製化履歷**：一頁的 LaTeX 履歷（ATS 友善的 PDF），由 `tools/resume.py` 編譯並檢查版面，依每個職缺調整。
- **投遞職缺**：貼上職缺網址，就會得到適合度判斷、依職缺調整的履歷和申請表答案，再由第二個 agent 審閱。
- **面試準備**：根據雇主會讀到的資料整理準備包，再進行模擬面試。
- **技能缺口分析**：橫跨多個職缺的技能缺口熱圖，以及以專案為主的學習計畫。
- **雇主排序**：依簽證贊助、領域契合度和公司規模，排序徵才博覽會的名單或職缺清單。
- **匯入**：把舊履歷和 CV（PDF、Word、LaTeX）、自我介紹、報告、LinkedIn 匯出檔、AI 聊天記錄（ChatGPT、Claude.ai、Gemini、Perplexity）和已登入的網站，併成每段經歷一筆條目。讀取網站，以及沒有匯出功能的 Perplexity，需要有瀏覽器工具的 agent。
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
- 條列先寫你做了什麼，數字放在後面：以數字開頭的條列，會讓人看不出你做了什麼。（同儕的建議）
- 畢業日期放在讀者一眼就看得到的地方。（招募人員的篩選順序，由同儕轉述）
- Skills 列出的技能，也要出現在某條條列裡：招募人員先拿 Skills 對照職缺，再找用到這些技能的經歷。（同一位招募人員的看法）
- 軟實力以 1–3 項證據寫進技術條列，不另開條列。（用人團隊工程師的建議）
- 指標的名稱要寫出確切量測的東西（「p95 queue wait」，而不是「p95 latency」）。（真實申請的審閱流程抓到的）
- 職缺用了概括性的詞時，把那個詞寫進條列，放在具體工具旁邊。（真實申請的關鍵字掃描分數偏低）
- 成果指標勝過「抓到多少失敗」的指標，測試數量也不算影響力。（作者撰寫時的判斷）

和這裡的每條規則一樣，這些都是你可以改寫的預設值（見本頁開頭）。

## 適用範圍與限制

這個 skill 是為**北美風格的英文履歷**設計的：一頁、遵循 [writing.md](skills/career-log/writing.md) 的規則、使用內附的 LaTeX 範本。你可以用任何語言跟 agent 對話，記錄也可以用任何語言寫；適用範圍指的是它產出的履歷。

其他語言和履歷風格要等三項規劃中的功能：自訂履歷範本、Typst 範本，以及 CJK（中文、日文、韓文）履歷。即使這些功能完成，其他語言或風格的履歷**效果可能仍不如**北美英文履歷。這些功能會延伸同一套以這種風格建立並測試的設計，而不是另外加入針對其他市場調整的規則。

## 快速開始

1. 在 GitHub 按 **Use this template** 建立自己的 repo，並設為 **Private**：這裡會放你的個人經歷。
2. 把它 clone 到電腦上，在 repo 根目錄開你的 coding agent，對它說「照 SETUP.md 幫我設定這台電腦」。它會設定 git 身分、把 skill 連到你的 agent 讀取的 skill 資料夾（SETUP.md 第 4 步）、安裝 LaTeX 工具並跑檢查。
3. 手上有什麼就交出來。把舊履歷和 CV（PDF、`.tex`、Word）、自我介紹、報告和 LinkedIn 匯出檔放進 `sources/inbox/`，說「import my old resumes」。AI 聊天記錄就說「import my ChatGPT history」（或 Claude、Gemini、Perplexity），agent 會告訴你怎麼匯出。已登入的網站就說出網站名稱；這部分需要有瀏覽器工具的 agent。
4. 之後在任何專案完成一件值得記的事，說「log this to my career log」；要投履歷時，貼職缺網址說「apply to <網址>」。

你可以用任何語言跟你的 agent 對話。記錄預設用英文寫（可在 `direction.md` 改），每份產出各自選語言。範例資料在 `skills/career-log/examples/`，只是格式示範，不會被當成你的經歷。

## 使用方式

呼叫 skill，說你想做什麼。`career-log` skill（在 [`skills/career-log/`](skills/career-log/SKILL.md)）連到你的 agent 讀取的 skill 資料夾之後（見 [SETUP.md](SETUP.md) 第 4 步），在上述任何 agent 的任何 session 都能用，並會依你的要求選模式。下表列出你可以要求的事，僅供參考，不是指令清單：引號裡的句子只是範例，怎麼說都行。

| 你可以要求 | 模式 |
|---|---|
| "log this to my career log" | **log**：在某筆條目加一行有日期的記錄 |
| "consolidate the <project> entry" | **consolidate**：補齊每個段落，針對缺口追問你 |
| "apply to <posting URL>" | **apply**：適合度判斷、針對職缺改寫的履歷和申請表答案、第二個 agent 審閱 |
| "prep me for the <company> interview" | **interview**：根據對方會讀到的資料整理準備包，再進行模擬面試 |
| "what should I learn for these postings" | **upskill**：以證據為本的技能缺口熱圖，以及以專案為主的學習計畫 |
| "rank these career fair employers" | **rank**：依簽證贊助、領域契合度、規模分級，並為每個排名前面的雇主準備一句開場白 |
| "write resume bullets for <role>" | **write**：產出文件，並附來源追溯表 |
| "import my old resumes"（檔案放在 `sources/inbox/`，或透過 agent 的瀏覽器讀取已登入的網站） | **import**：把舊文件併入條目 |
| "import my ChatGPT history"（或 Claude、Gemini、Perplexity） | **import**：告訴你怎麼匯出，逐一篩選每段對話，只複製你挑的那些；原始匯出檔不進 git |
| "audit my career log" | **audit**：列出缺少的故事、缺口和矛盾 |

建議安裝 [humanizer](https://github.com/blader/humanizer) skill。不論有沒有裝，這個 skill 都會自己檢查 AI 寫作痕跡（[writing.md](skills/career-log/writing.md)）；裝了 humanizer 的話，每份要給雇主看的產出也會再跑一次 humanizer。

## 條目

條目索引只放在英文版 [README.md](README.md#entries)，你每記一筆，skill 就會更新它。

## 檔案

- [`profile.md`](profile.md)：聯絡方式、學歷、語言、技能摘要
- [`stories.md`](stories.md)：行為面試題類型 → 故事，以及常見申請題 → 素材
- [`applications.md`](applications.md)：這個 repo 準備過材料的申請、徵才博覽會和招募人員聯絡記錄
- [`direction.md`](direction.md)：目標職位、雇主偏好、限制條件、要強調的重點、語言
- `entries/`：每段經歷一個檔案（[範本](entries/_template.md)）
- `outputs/`：產出的文件，每份都附來源追溯表：`applications/`（每個申請一個資料夾，送出後就不再更動）、`resumes/`（每個履歷方向一份持續更新的檔案，舊版本留在 git 歷史裡）和 `reports/`（加上日期的排名和其他報告）
- [`SETUP.md`](SETUP.md)：每台電腦的設定（macOS、Windows、Linux）
- `tools/`：LaTeX 安裝腳本和 `resume.py`（編譯並檢查履歷版面）；用法見 [latex.md](skills/career-log/latex.md)
- `skills/career-log/`：skill 本身、它的[寫作標準](skills/career-log/writing.md)和[範例](skills/career-log/examples/README.md)
- `sources/`：匯入的原始檔、匯入收件匣（`inbox/`）、[匯入記錄](sources/import-log.md)和[來源代號](sources/keys.md)
- [`GLOSSARY.md`](GLOSSARY.md) 和 [`docs/adr/`](docs/adr/)：這個 repo 的詞彙和設計決策

## 上游

這個 repo 是從 https://github.com/mileschintw/career-log-template 這個 Template 建立的。聊天匯出格式改了或某個步驟壞了，請到那裡回報：開 issue（用「Chat export format changed」表單）或發 pull request。Issue 是公開的：只附欄位名稱和結構，絕不附你的記錄。import 模式會幫你草擬回報，貼出前會先問你（[import-chats.md](skills/career-log/modes/import-chats.md) 第 8 步）。

## 授權

MIT，見 [LICENSE](LICENSE)。範例履歷改自 [r/EngineeringResumes 範本](https://github.com/r-engineeringresumes/resume-templates)（MIT）。
