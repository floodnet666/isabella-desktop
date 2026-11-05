import urllib.request
import xml.etree.ElementTree as ET
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

caption_url = "https://www.youtube.com/api/timedtext?v=3d7OJwyZwIQ&ei=JyHratf9JciHvPgP1Krz0QY&caps=asr&opi=112496729&exp=xpe&xoaf=5&xowf=1&xospf=1&hl=it&ip=0.0.0.0&ipbits=0&expire=1793819543&sparams=ip,ipbits,expire,v,ei,caps,opi,exp,xoaf&signature=8060CA35280C298B03D1B80B1C753C30CC0CD2E0.96FC23B406A2FADF11A9D9FD1D4B31CA9C331E04&key=yt8&kind=asr&lang=pt&variant=gemini"

try:
    req = urllib.request.Request(caption_url, headers={"User-Agent": "Mozilla/5.0"})
    xml_data = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    root = ET.fromstring(xml_data)
    
    lines = []
    for text_el in root.findall('text'):
        start = float(text_el.attrib.get('start', 0))
        dur = float(text_el.attrib.get('dur', 0))
        content = text_el.text or ""
        # Decodificar entidades HTML
        content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
        content = content.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        minutes = int(start // 60)
        seconds = int(start % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        lines.append((start, timestamp, content))
        
    print(f"Total lines parsed: {len(lines)}")
    
    # Salvar a transcrição completa
    with open(r"D:\isabella-desktop\logs\youtube_transcript_pt.txt", "w", encoding="utf-8") as f:
        for s, ts, text in lines:
            f.write(f"[{ts}] {text}\n")
    print("Salvo em D:\\isabella-desktop\\logs\\youtube_transcript_pt.txt")
    
    # Mostrar trecho de 'Conversação em português' (12:00 até 16:30)
    print("\n================ TRECHO: CONVERSAÇÃO EM PORTUGUÊS (12:00 - 16:30) ================")
    for s, ts, text in lines:
        if 720 <= s <= 1000:
            print(f"[{ts}] {text}")
            
except Exception as e:
    print("Erro:", e)
