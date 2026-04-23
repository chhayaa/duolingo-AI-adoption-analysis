"""Convert the positioning report HTML to PDF using Playwright."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def convert_html_to_pdf(html_path: str, pdf_path: str) -> None:
    abs_html = Path(html_path).resolve()
    if not abs_html.exists():
        print(f"ERROR: HTML file not found: {abs_html}")
        return

    file_url = abs_html.as_uri()
    print(f"Loading: {file_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.pdf(
            path=pdf_path,
            format="A4",
            margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
            print_background=True,
        )
        browser.close()

    print(f"PDF saved to: {pdf_path}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(script_dir, "output", "positioning_report.html")
    pdf_file = os.path.join(script_dir, "output", "positioning_report.pdf")
    convert_html_to_pdf(html_file, pdf_file)
