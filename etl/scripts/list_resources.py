"""Liste les ressources d'un jeu data.gouv.fr : python list_resources.py <slug>"""
import sys

import httpx

slug = sys.argv[1]
data = httpx.get(f"https://www.data.gouv.fr/api/1/datasets/{slug}/", follow_redirects=True, timeout=60).json()
print(data["title"], "-", data.get("last_modified"))
for r in data["resources"]:
    print(f"- {r['title']} | {r.get('format')} | {r.get('filesize')} o | {r['url']}")
