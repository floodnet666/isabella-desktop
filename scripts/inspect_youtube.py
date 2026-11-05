import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = "https://www.youtube.com/watch?v=3d7OJwyZwIQ"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    
    title_m = re.search(r'<title>(.*?)</title>', html)
    print("TITLE:", title_m.group(1) if title_m else "N/A")
    
    desc_m = re.search(r'"shortDescription":"(.*?)"', html)
    if desc_m:
        raw_desc = desc_m.group(1).encode('utf-8').decode('unicode_escape', errors='replace')
        print("\nDESCRIPTION:\n", raw_desc)
        
    # Procurar por legendas / captions tracks
    caption_m = re.search(r'"captionTracks":\[(.*?)\]', html)
    if caption_m:
        print("\nCAPTION TRACKS FOUND!")
        tracks = re.findall(r'"baseUrl":"(.*?)"', caption_m.group(1))
        for t in tracks[:3]:
            print("Track URL:", t.replace('\\u0026', '&'))
            
except Exception as e:
    print("Error:", e)
