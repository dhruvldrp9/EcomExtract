import requests

html = requests.get(
    'https://www.mobvoi.com/us/pages/ticwatchpro5',
    headers={'User-Agent': 'EcomExtractBot/1.0'},
    timeout=20,
).text

needles = [
    '__INITIAL_STATE__',
    '__NUXT__',
    'window.__',
    'application/ld+json',
    'price',
    'sku',
    'product',
    'offer',
    'variant',
    'buy',
    'cart',
]

for needle in needles:
    pos = html.lower().find(needle.lower())
    print('NEEDLE', needle, '=>', pos)
    if pos != -1:
        start = max(0, pos - 200)
        end = min(len(html), pos + 500)
        print(html[start:end].replace('\n', ' ')[:700])
        print('---')