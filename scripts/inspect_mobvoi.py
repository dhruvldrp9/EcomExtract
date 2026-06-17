import requests

url = 'https://www.mobvoi.com/us/pages/ticwatchpro5'
resp = requests.get(url, headers={'User-Agent': 'EcomExtractBot/1.0'}, timeout=15)
resp.raise_for_status()
html = resp.text
print(html[:8000])