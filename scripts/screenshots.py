"""Take full-page screenshots of the running app (for UI review and the README).

Run the server first, then:  python scripts/screenshots.py [out_dir] [run_id ...]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
out = Path(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
out.mkdir(parents=True, exist_ok=True)
pages = {"dashboard": "/", "new-run": "/run", "bulk": "/bulk", "inbox": "/inbox", "reference": "/reference"}
pages.update({f"run-{rid}": f"/runs/{rid}" for rid in sys.argv[2:]})

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    for name, path in pages.items():
        page.goto(BASE + path, wait_until="networkidle")
        page.wait_for_timeout(1500 if path.startswith("/runs/") else 600)
        page.screenshot(path=str(out / f"{name}.png"), full_page=True)
        print("saved", out / f"{name}.png")
    browser.close()
