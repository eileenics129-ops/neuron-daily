#!/usr/bin/env python3
"""
neuron-daily fetcher
抓取多源 AI 资讯，生成 data/latest.json
"""

import json
import re
import time
import random
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
from html.parser import HTMLParser

SHANGHAI = timezone(timedelta(hours=8))
TODAY = datetime.now(SHANGHAI).strftime('%Y-%m-%d')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# ─── RSS Sources ──────────────────────────────────────────────
NEWS_SOURCES = [
    {'name': '量子位',       'url': 'https://www.qbitai.com/feed',                'type': 'news'},
    {'name': '机器之心',     'url': 'https://syncedreview.com/feed/',              'type': 'news'},
    {'name': '36氪AI',       'url': 'https://36kr.com/feed',                      'type': 'news'},
    {'name': 'The Verge AI', 'url': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml', 'type': 'news'},
    {'name': 'MIT Tech Review','url':'https://www.technologyreview.com/feed/',     'type': 'news'},
    {'name': 'TechCrunch AI','url': 'https://techcrunch.com/category/artificial-intelligence/feed/', 'type': 'news'},
    {'name': 'VentureBeat AI','url':'https://venturebeat.com/category/ai/feed',  'type': 'news'},
    {'name': 'Hacker News',  'url': 'https://hnrss.org/frontpage?q=AI+LLM+GPT&points=50', 'type': 'news'},
]

BIZ_SOURCES = [
    {'name': 'First Round',  'url': 'https://review.firstround.com/feed.xml',        'type': 'biz'},
    {'name': 'YC Blog',      'url': 'https://www.ycombinator.com/blog/rss.xml',       'type': 'biz'},
    {'name': '虎嗅',         'url': 'https://www.huxiu.com/rss/0.xml',               'type': 'biz'},
    {'name': 'Product Hunt', 'url': 'https://www.producthunt.com/feed?category=artificial-intelligence', 'type': 'biz'},
    {'name': 'SaaStr',       'url': 'https://www.saastr.com/feed/',                  'type': 'biz'},
]

APP_SOURCES = [
    {'name': 'Product Hunt', 'url': 'https://www.producthunt.com/feed?category=artificial-intelligence', 'type': 'app'},
    {'name': 'GitHub Trending', 'url': 'https://mshibanami.github.io/GitHubTrendingRSS/daily/python.xml', 'type': 'app'},
    {'name': 'Indie Hackers', 'url': 'https://www.indiehackers.com/feed.xml',       'type': 'app'},
]

# ─── Helpers ──────────────────────────────────────────────────
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d): self.fed.append(d)
    def get_data(self): return ''.join(self.fed)

def strip_html(html):
    s = MLStripper()
    s.feed(str(html))
    return re.sub(r'\s+', ' ', s.get_data()).strip()

def truncate(text, n=120):
    text = strip_html(text)
    return text[:n] + '…' if len(text) > n else text

def fetch_url(url, timeout=10):
    req = Request(url, headers={'User-Agent': UA, 'Accept': 'application/rss+xml,application/xml,text/xml,*/*'})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f'  ⚠️  fetch failed: {url}: {e}', file=sys.stderr)
        return None

def parse_rss(raw):
    """Parse RSS/Atom, return list of {title, link, summary, published}"""
    items = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return items

    ns = {'atom': 'http://www.w3.org/2005/Atom',
          'content': 'http://purl.org/rss/1.0/modules/content/'}

    # Atom
    if root.tag.endswith('}feed') or root.tag == 'feed':
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            title = entry.findtext('{http://www.w3.org/2005/Atom}title', '')
            link_el = entry.find('{http://www.w3.org/2005/Atom}link')
            link = link_el.get('href','') if link_el is not None else ''
            summary = entry.findtext('{http://www.w3.org/2005/Atom}summary','') or \
                      entry.findtext('{http://www.w3.org/2005/Atom}content','')
            published = entry.findtext('{http://www.w3.org/2005/Atom}published','') or \
                        entry.findtext('{http://www.w3.org/2005/Atom}updated','')
            items.append({'title': strip_html(title), 'url': link,
                          'summary': truncate(summary), 'time': published[:10] if published else ''})
        return items

    # RSS 2.0
    for item in root.findall('.//item'):
        title   = item.findtext('title','')
        link    = item.findtext('link','')
        desc    = item.findtext('description','') or item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded','')
        pubdate = item.findtext('pubDate','')
        # parse pubdate nicely
        time_str = ''
        if pubdate:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pubdate).astimezone(SHANGHAI)
                time_str = dt.strftime('%m-%d')
            except Exception:
                time_str = pubdate[:10]
        items.append({'title': strip_html(title), 'url': link,
                      'summary': truncate(desc), 'time': time_str})
    return items

def is_ai_related(text):
    keywords = ['AI', 'ai', '人工智能', 'LLM', 'GPT', 'Claude', 'Gemini',
                'ChatGPT', '大模型', '机器学习', 'machine learning',
                'neural', 'openai', 'anthropic', 'agent', 'diffusion',
                'foundation model', '语言模型', 'deepmind', 'mistral',
                'llama', 'model', 'inference', '智能', 'automation', '自动化']
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)

def fetch_source(source, max_items=8):
    print(f'  Fetching {source["name"]}...', file=sys.stderr)
    raw = fetch_url(source['url'])
    if not raw:
        return []
    items = parse_rss(raw)
    # Filter for AI relevance for general feeds
    if source['name'] in ('36氪AI', '虎嗅', 'Hacker News', 'GitHub Trending'):
        items = [i for i in items if is_ai_related(i['title'] + ' ' + i['summary'])]
    # Inject source name
    for item in items:
        item['source'] = source['name']
    return items[:max_items]

# ─── Main ──────────────────────────────────────────────────────
def main():
    print(f'🧠 Neuron Daily — {TODAY}', file=sys.stderr)

    news_items = []
    biz_items  = []
    app_items  = []

    # News
    print('📰 Fetching news sources...', file=sys.stderr)
    for src in NEWS_SOURCES:
        items = fetch_source(src, max_items=5)
        news_items.extend(items)
        time.sleep(0.3)

    # Biz
    print('💡 Fetching biz sources...', file=sys.stderr)
    for src in BIZ_SOURCES:
        items = fetch_source(src, max_items=4)
        biz_items.extend(items)
        time.sleep(0.3)

    # Apps (product hunt already fetched, dedupe)
    print('🎮 Fetching app sources...', file=sys.stderr)
    seen_urls = set()
    for src in APP_SOURCES:
        items = fetch_source(src, max_items=5)
        for item in items:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                app_items.append(item)
        time.sleep(0.3)

    # Dedupe by url within each category
    def dedupe(lst):
        seen = set()
        out = []
        for item in lst:
            key = item.get('url','') or item.get('title','')
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    news_items = dedupe(news_items)[:20]
    biz_items  = dedupe(biz_items)[:12]
    app_items  = dedupe(app_items)[:12]

    data = {
        'date':    TODAY,
        'updated': datetime.now(SHANGHAI).isoformat(),
        'sources': len(NEWS_SOURCES) + len(BIZ_SOURCES) + len(APP_SOURCES),
        'news':    news_items,
        'biz':     biz_items,
        'apps':    app_items,
    }

    out_path = os.path.join(OUTPUT_DIR, 'latest.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Also save dated archive
    archive_path = os.path.join(OUTPUT_DIR, f'{TODAY}.json')
    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'✅ Done: {len(news_items)} news, {len(biz_items)} biz, {len(app_items)} apps', file=sys.stderr)
    print(f'   Saved to {out_path}', file=sys.stderr)

if __name__ == '__main__':
    main()
