#!/usr/bin/env python3
import os, re, time, json, requests
from urllib.parse import urlparse

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))
OUT_FILE = os.getenv("OUT_FILE", "dist/all.rsc")

AWS_URL = os.getenv("AWS_URL", "https://ip-ranges.amazonaws.com/ip-ranges.json")
GCP_URL = os.getenv("GCP_URL", "https://www.gstatic.com/ipranges/goog.json")

# Optional: pin Azure weekly JSON to skip scraping (recommended for maximum stability)
AZURE_URL = os.getenv("AZURE_URL", "").strip()

AZURE_CONFIRMATION_URLS = [
    "https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519",
    "https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519&culture=en-us&country=US",
]

UA = {"User-Agent": "cloud-ipv4-gh-action/1.0", "Accept-Encoding": "identity"}

def http_json(url: str) -> dict:
    r = requests.get(url, headers={**UA, "Accept":"application/json"}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()

def discover_azure_url() -> str:
    if AZURE_URL:
        u = AZURE_URL
        if not urlparse(u).netloc.endswith("download.microsoft.com"):
            raise RuntimeError("AZURE_URL must point to download.microsoft.com")
        if not re.search(r"ServiceTags_Public_.*\.json$", u):
            raise RuntimeError("AZURE_URL must be a ServiceTags_Public_*.json file")
        return u
    pat = re.compile(r'https://download\.microsoft\.com/[^"]*ServiceTags_Public_[^"]*\.json', re.I)
    for conf in AZURE_CONFIRMATION_URLS:
        h = requests.get(conf, headers={
            **UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=HTTP_TIMEOUT, allow_redirects=True)
        h.raise_for_status()
        html = h.text
        m = pat.search(html)
        if m:
            return m.group(0)
        m2 = re.search(r'https:\\/\\/download\.microsoft\.com\\/[^"]*ServiceTags_Public_[^"]*\.json', html)
        if m2:
            return m2.group(0).replace("\\/", "/")
    raise RuntimeError("Could not locate Azure ServiceTags_Public JSON link on Microsoft site. "
                       "Set AZURE_URL to the direct download.microsoft.com JSON.")

def aws_ipv4() -> list[str]:
    data = http_json(AWS_URL)
    return [e["ip_prefix"] for e in data.get("prefixes", []) if "ip_prefix" in e]

def gcp_ipv4() -> list[str]:
    data = http_json(GCP_URL)
    return [e["ipv4Prefix"] for e in data.get("prefixes", []) if "ipv4Prefix" in e]

def azure_ipv4() -> list[str]:
    url = discover_azure_url()
    data = http_json(url)
    out = []
    for item in data.get("values", []):
        props = item.get("properties", {})
        for p in props.get("addressPrefixes", []):
            if ":" not in p:
                out.append(p)
    return out

def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set(); out = []
    for x in items:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    a = aws_ipv4()
    g = gcp_ipv4()
    z = azure_ipv4()
    allv4 = dedupe_keep_order(a + g + z)

    ts = int(time.time())
    lines = [
        f'# cloud-ipv4 export at {ts}; providers=aws,gcp,azure; count={len(allv4)}',
        '/ip/firewall/address-list/remove [find list="CloudAll"]',
    ]
    lines += [f'/ip/firewall/address-list/add list="CloudAll" address={p} comment="cloud-ipv4"' for p in allv4]

    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {OUT_FILE} with {len(allv4)} prefixes.")

if __name__ == "__main__":
    main()
