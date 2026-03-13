# 每日神经元 · Neuron Daily

> 每天更新最值得关注的 AI 资讯、商业化点子和好玩新应用

## 🌐 访问地址

**https://neuron-daily.vercel.app**（部署后生效）

## 📁 项目结构

```
neuron-daily/
├── public/
│   ├── index.html        # 静态站前端
│   └── data/
│       ├── latest.json   # 每日最新数据
│       └── YYYY-MM-DD.json  # 历史归档
├── scripts/
│   ├── fetch.py          # 内容抓取脚本
│   └── deploy.sh         # 一键部署脚本
└── vercel.json           # Vercel 配置
```

## 📰 内容来源

**AI 资讯**
- 量子位、机器之心、36氪 AI
- The Verge AI、MIT Technology Review
- TechCrunch AI、VentureBeat AI、Hacker News

**商业化点子**
- a16z、YC Blog、虎嗅、Product Hunt

**好玩新应用**
- Product Hunt AI、GitHub Trending

## 🚀 本地运行

```bash
# 抓取内容
python3 scripts/fetch.py

# 部署（需要设置 GITHUB_TOKEN 环境变量）
GITHUB_TOKEN=xxx bash scripts/deploy.sh
```

## ⚙️ 自动更新

通过 OpenClaw cron 每天早 10:00 (Asia/Shanghai) 自动执行。
