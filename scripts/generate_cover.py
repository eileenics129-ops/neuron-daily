#!/usr/bin/env python3
"""
generate_cover.py — 根据今日头条生成封面图，保存到 public/images/
用法：python3 scripts/generate_cover.py [top_headline]
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime, timezone, timedelta

SHANGHAI = timezone(timedelta(hours=8))
TODAY = datetime.now(SHANGHAI).strftime('%Y-%m-%d')

SKILL_DIR = os.path.expanduser('~/.openclaw/skills/mulerouter-skills')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'images')
os.makedirs(OUT_DIR, exist_ok=True)

def make_prompt(headline: str) -> str:
    """把中文头条转成英文图像提示词（硬编码模板，不依赖 LLM）"""
    # 根据关键词选择视觉主题
    themes = {
        '机器人': 'a sleek humanoid robot with glowing joints in a dark lab',
        'robot': 'a sleek humanoid robot with glowing joints in a dark lab',
        '大模型': 'a massive glowing neural network sphere floating in space',
        'LLM': 'a massive glowing neural network sphere floating in space',
        '融资': 'stacks of glowing gold coins transforming into circuit boards',
        '投资': 'stacks of glowing gold coins transforming into circuit boards',
        '芯片': 'an extreme close-up of a glowing microchip with electric arcs',
        'chip': 'an extreme close-up of a glowing microchip with electric arcs',
        '马斯克': 'a rocket launching through a digital neural network sky',
        'GPT': 'streams of glowing text particles forming a human brain shape',
        'AI编辑': 'a robot journalist typing on a holographic keyboard',
        '数学': 'beautiful mathematical equations dissolving into light particles',
    }

    visual = 'a glowing neural network brain with electric orange pulse lines radiating outward'
    for kw, desc in themes.items():
        if kw.lower() in headline.lower():
            visual = desc
            break

    return (
        f"Editorial illustration for an AI tech news magazine cover. "
        f"Main visual: {visual}. "
        f"Color palette: deep dark navy background (#0a0a0f), electric orange accents (#ff6b2b), "
        f"subtle grid texture, dramatic volumetric lighting. "
        f"Style: cinematic sci-fi concept art, sharp clean edges, high contrast, "
        f"professional editorial photography meets digital art. "
        f"No text, no letters, no words, no numbers."
    )

def generate(headline: str) -> str | None:
    prompt = make_prompt(headline)
    print(f'🎨 Generating cover for: {headline[:40]}...', file=sys.stderr)
    print(f'   Prompt: {prompt[:80]}...', file=sys.stderr)

    result = subprocess.run(
        ['uv', 'run', 'python',
         'models/google/nano-banana-2/generation.py',
         '--prompt', prompt,
         '--aspect-ratio', '16:9'],
        cwd=SKILL_DIR,
        capture_output=True, text=True, timeout=180
    )

    if result.returncode != 0:
        print(f'❌ Generation failed: {result.stderr[-300:]}', file=sys.stderr)
        return None

    # 从输出里找图片 URL
    for line in result.stdout.splitlines():
        if 'https://' in line and ('.png' in line or '.jpg' in line or '.webp' in line):
            url = line.strip().split()[-1]
            print(f'✅ Image URL: {url}', file=sys.stderr)
            return url

    print(f'❌ No URL found in output:\n{result.stdout[-500:]}', file=sys.stderr)
    return None

def download(url: str, dated_path: str, latest_path: str) -> bool:
    import urllib.request
    try:
        urllib.request.urlretrieve(url, dated_path)
        shutil.copy(dated_path, latest_path)
        size = os.path.getsize(dated_path)
        print(f'✅ Saved: {dated_path} ({size//1024}KB)', file=sys.stderr)
        return True
    except Exception as e:
        print(f'❌ Download failed: {e}', file=sys.stderr)
        return False

if __name__ == '__main__':
    headline = sys.argv[1] if len(sys.argv) > 1 else '今日AI大事件：大模型与机器人的新突破'
    url = generate(headline)
    if url:
        dated = os.path.join(OUT_DIR, f'cover-{TODAY}.png')
        latest = os.path.join(OUT_DIR, 'cover-latest.png')
        download(url, dated, latest)
    else:
        sys.exit(1)
