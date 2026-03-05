from orchestrator import fetch_supply_chain_news, _urlquote, urllib, ET, ERP_PROFILES
def debug_news(company_key):
    erp = ERP_PROFILES[company_key]
    locations = []
    for sup in erp["suppliers"].values():
        locations.append(sup["city"])
        hub = sup.get("transit_hub", "")
        if "Port of" in hub:
            locations.append(hub.replace("Port of", "").strip().split(" ")[0])
    locations.append(erp["warehouse"]["city"])

    seen = set()
    unique_locs = []
    for loc in locations:
        if loc and loc not in seen:
            seen.add(loc)
            unique_locs.append(loc)
        if len(unique_locs) >= 5:
            break

    loc_query = " OR ".join(f'"{loc}"' for loc in unique_locs)
    query = f'({loc_query}) (supply chain OR logistics OR shipping OR disruption OR port OR semiconductor)'
    url = f"https://news.google.com/rss/search?q={_urlquote(query)}&hl=en-US&gl=US&ceid=US:en"
    print("URL:", url)
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_bytes = resp.read()
            print("Bytes:", len(xml_bytes))
        root = ET.fromstring(xml_bytes)
        channel = root.find("channel")
        print("Channel:", channel is not None)
    except Exception as e:
        print("Exception:", e)

debug_news("🚗 TexMex Components — Mexico (Multi-source)")
