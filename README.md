# BMI 計算器

使用 Flask 製作的成人 BMI 網頁計算器。輸入身高（公分）和體重（公斤）後，頁面會顯示 BMI（小數點後一位）、體位分類與生活建議。

主畫面的計算表單提供選填的姓名欄位，填寫後會在計算結果顯示姓名；未填姓名仍可正常計算。送出後會保留欄位內容，方便修改或更正輸入，姓名不會儲存至資料庫。

## 啟動

需安裝 Python 3.9 以上版本。在專案資料夾執行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

接著開啟 http://127.0.0.1:5000/ 。若 PowerShell 不允許啟用虛擬環境，也可以使用 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` 和 `.\.venv\Scripts\python.exe app.py`。

## 計算方式

BMI = 體重（公斤）÷ 身高（公尺）²。分類採臺灣成人體位參考標準：低於 18.5 為體重過輕、18.5 至未滿 24 為健康體位、24 至未滿 27 為體重過重、27 以上為肥胖。頁面以顯示至小數點後一位的 BMI 進行分類。

體重過輕、過重或肥胖時，BMI 數值與體位分類文字會以紅色顯示；健康體位維持原有顏色。

這只是成人體位參考，不能取代專業醫療評估，也不適用於兒童、青少年或孕婦。

## 兵役體位初步判斷

輸入有效身高與體重並計算後，頁面會另列中華民國兵役體位初步參考、採計身高與體重、兵役 BMI、判斷理由及規則來源。修改輸入後重新計算，即同步更新；輸入無效時不產生結果。

規則依[全國法規資料庫《體位區分標準》](https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=F0040018)民國 112 年 5 月 30 日（2023-05-30）修正發布之附件[附表一：身高體重體位區分標準表](https://law.moj.gov.tw/LawClass/LawGetFile.ashx?FileId=0000342747&lan=C)（PDF 第 86 頁／表列第 88 頁），查核日為 2026-10-27。這是隨程式提供的固定規則，不會在每次計算時連線更新；法規修正時須重新查核並更新規則、來源版本與邊界測試。

依附表附記，身高捨去不足 1 公分的尾數，體重捨去小數第一位後的尾數，使用採計值計算 BMI 後，以四捨五入取小數一位。此處使用十進位四捨五入，與既有健康 BMI 的計算及分類分開，頁面會明確顯示差異原因。若捨去尾數後身高或體重為 0，仍可顯示有效的健康 BMI，但不提供兵役判斷。

| 採計身高 | 兵役 BMI | 初步參考體位 |
| --- | --- | --- |
| 154 公分以下或 196 公分以上 | 不限 | 免役體位 |
| 155 至 195 公分 | 小於 15 或大於 35 | 免役體位 |
| 155 至 157 公分 | 15 至 35（含端點） | 替代役體位 |
| 158 至 195 公分 | 15 至未滿 16.5，或大於 32 至 35 | 替代役體位 |
| 158 至 195 公分 | 16.5 至 32（含端點） | 常備役體位 |

僅供役齡男子依身高、體重初步參考，不涵蓋疾病、其他體檢項目、役期或徵集資格，也不是完整體位判定。正式體位仍以主管機關體檢及判定為準；適用日期、身分或規則版本不符時，請向戶籍地役政單位確認。

執行測試：`python -m unittest discover -s tests`

## Agent Skill：create user story and AC

儲存庫提供 `.github/skills/create-user-story-and-ac/SKILL.md`，可使用 `/create-user-story-and-ac` 並附上 GitHub Project 網址，檢查所有 Ready 項目，依標題補上缺少的 User Story 與 Acceptance Criteria。新增的內容預設使用繁體中文，AC 使用 `- [ ]` checklist。

此 Skill 會保留既有描述與已完成的章節，只補缺漏；更新前會重新讀取內容，更新後會讀回確認，不會變更項目狀態或實作功能。原有 `github-project-ready-descriptions` Skill 仍限於補上整份空白描述。

## 部署到 Azure Web App

`.github/workflows/deploy-azure.yml` 在 `main` 分支的應用程式、測試或 workflow 異動時執行，也可以從 GitHub Actions 手動觸發。流程會在 Windows runner 上執行測試、下載官方 Python 3.14.8 可嵌入版本，將 Python 與相依套件一起部署到 `NTUSTweb00`（資源群組 `NTUSTlab2026`）。站點透過 `web.config` 的 IIS HttpPlatformHandler 啟動 `serve.py`，以 Waitress 提供 Flask 服務。

此方法使用**隨部署包提供的 Python**，不依賴 Windows App Service 內建 Python 執行環境；HttpPlatformHandler 必須在目標站點可用。`NTUSTweb00` 目前是 Windows Web App，部署時會確認作業系統。

在 GitHub 儲存庫 **Settings → Secrets and variables → Actions** 確認：

- Repository secret `AZURE_CREDENTIALS`：Azure 服務主體的 `clientId`、`clientSecret`、`subscriptionId`、`tenantId` 組成的 JSON。此 Secret 已設定，不要把內容寫進程式碼。

請確認該服務主體對 `NTUSTweb00` 具有部署權限（例如該站點的 **Website Contributor**）。推送符合上述條件的 `main` 分支異動，或從 GitHub Actions 手動執行工作流程即可部署。

### dev 分支部署到 test slot

`.github/workflows/deploy-azure-test2.yml` 在 `dev` 分支每次 push 時執行，也支援手動觸發。流程沿用正式環境的測試與打包步驟，但只部署到 `test` slot，不會部署到 production slot。

此流程使用 Repository variables `AZURE_WEBAPP_NAME`、`AZURE_RESOURCE_GROUP` 與既有的 Secret `AZURE_CREDENTIALS`。請先在目標 Web App 建立名為 `test` 的 deployment slot，並確認服務主體具有該 slot 的部署權限。此流程與 `deploy-azure-test.yml` 共用 `azure-bmi-test` 併發群組，避免同時部署到同一個 slot。

### fb 分支部署與 SonarCloud 掃描

`.github/workflows/deploy-azure-test.yml` 在 `fb` 分支 push 或手動觸發時執行。流程依序執行 unit test、SonarCloud 掃描、打包與 Azure test slot 部署；測試或掃描步驟失敗時，不繼續部署。掃描使用 `SonarSource/sonarqube-scan-action@v8.3.0`，Python 分析版本與測試及部署環境一致為 3.14，並取得完整 Git 歷史供分析使用。此設定未啟用等待 Quality Gate 結果，掃描提交成功不代表 Quality Gate 已通過。

執行前，請在 SonarCloud 建立對應專案並停用該專案的 Automatic Analysis，改用 CI-based analysis；在 GitHub Repository secrets 設定 `SONAR_TOKEN`（具有分析權限的 token）、`SONAR_PROJECTKEY`（專案 key）與 `SONAR_ORGKEY`（組織 key）。此流程同樣需要 `AZURE_CREDENTIALS` secret、`AZURE_WEBAPP_NAME` 與 `AZURE_RESOURCE_GROUP` variables。
