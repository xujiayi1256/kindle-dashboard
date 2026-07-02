# Kindle Dashboard

把闲置 Kindle 变成家里的信息屏：日期、农历、节气、节假日倒计时、上海天气、降水、AQI、紫外线指数。

## 功能

- 公历日期、星期、农历
- 今日节气 / 下一个节气
- 距离春节、国庆、中秋等倒计时
- 上海实时天气、体感、湿度、降水提示
- 空气质量 AQI
- 紫外线指数
- 国务院节假日与调休提醒

## 本地运行

```bash
cd kindle-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入和风天气配置

python render.py
open output/dashboard.png
```

## 部署到 GitHub（自动每 30 分钟更新）

### 1. 创建 GitHub 仓库并推送代码

```bash
cd kindle-dashboard
git add .
git commit -m "Initial Kindle dashboard"
gh repo create kindle-dashboard --public --source=. --push
```

如果没有 `gh` CLI，也可以在 GitHub 网页新建空仓库后：

```bash
git remote add origin https://github.com/你的用户名/kindle-dashboard.git
git branch -M main
git push -u origin main
```

### 2. 配置 Secrets

打开仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加：

| Secret | 说明 |
|--------|------|
| `QWEATHER_API_HOST` | 和风控制台里的 API Host，如 `https://abc123.qweatherapi.com` |
| `QWEATHER_KID` | JWT 凭据 ID |
| `QWEATHER_PROJECT_ID` | 项目 ID（JWT 的 `sub`） |
| `QWEATHER_PRIVATE_KEY` | Ed25519 私钥全文（PEM 格式，换行保留） |

> **推荐用 KID + 私钥自动生成 JWT**，因为 JWT 有效期短，适合 GitHub Actions 定时任务。  
> 也可临时设置 `QWEATHER_JWT`（手动生成的 token），但过期后需重新更新 Secret。

私钥示例格式：

```
-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEI...
-----END PRIVATE KEY-----
```

在 GitHub Secret 里粘贴时，保持完整 PEM 内容即可。

### 3. 启用 Actions

推送代码后，打开仓库 **Actions** 标签页：

1. 点击 **Render Kindle Dashboard**
2. 点击 **Run workflow** 手动触发一次
3. 成功后仓库里会出现 `output/dashboard.png`

之后每 30 分钟自动更新一次。

### 4. Kindle 访问地址

图片 URL（把用户名换成你的）：

```
https://raw.githubusercontent.com/你的用户名/kindle-dashboard/main/output/dashboard.png
```

越狱 Kindle 后，用 [kindle-dash](https://github.com/pascalw/kindle-dash) 等客户端指向这个 URL 即可。

## 环境变量

见 `.env.example`。Kindle 型号确认后，用 `eips -i` 查看分辨率，再设置 `KINDLE_WIDTH` / `KINDLE_HEIGHT`。

## 项目结构

```
kindle-dashboard/
├── render.py              # 入口
├── data_sources.py        # 天气、节假日、农历数据
├── render_dashboard.py    # 图片渲染
├── auth.py                # 和风 JWT
├── config.py
├── output/dashboard.png   # 生成的图片
└── .github/workflows/render.yml
```
