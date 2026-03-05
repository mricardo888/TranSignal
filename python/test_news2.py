import requests
import xml.etree.ElementTree as ET

url = "https://news.google.com/rss/search?q=%28%22Monterrey%22%20OR%20%22Houston%22%20OR%20%22Guangzhou%22%20OR%20%22San%20Antonio%22%29%20%28supply%20chain%20OR%20logistics%20OR%20shipping%20OR%20disruption%20OR%20port%20OR%20semiconductor%29&hl=en-US&gl=US&ceid=US:en"
try:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}, timeout=8)
    print("Status:", resp.status_code)
    print("Text length:", len(resp.text))
    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    print("Channel:", channel is not None)
    if channel:
        items = channel.findall("item")
        print("Items count:", len(items))
except Exception as e:
    print("Exception:", e)
