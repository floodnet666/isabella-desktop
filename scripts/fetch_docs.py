import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"D:\isabella-desktop\logs\liquid_docs_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

for m in re.finditer(r'LFM3-Audio', html):
    start = max(0, m.start() - 200)
    end = min(len(html), m.end() + 800)
    clean = re.sub(r'\\u003c.*?\\u003e', ' ', html[start:end])
    clean = clean.replace('\\"', '"').replace('\\n', '\n')
    print('==================== MATCH ====================')
    print(clean)
