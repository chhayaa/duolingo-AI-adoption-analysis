"""
Generate high-fidelity PDF versions of the iMeUsWe analysis HTML reports.
Uses Playwright (Chromium) to render HTML exactly as it appears in a browser,
then prints to PDF — preserving all CSS styling, flexbox layouts, colors, etc.
"""

import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def convert_html_to_pdf(html_path: str, pdf_path: str):
    """Convert an HTML file to a pixel-perfect PDF using headless Chromium."""
    file_url = Path(html_path).resolve().as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(file_url, wait_until="networkidle")
        await page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={
                "top": "0.6in",
                "bottom": "0.6in",
                "left": "0.5in",
                "right": "0.5in",
            },
        )
        await browser.close()

    print(f"  Saved: {pdf_path}")


async def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    reports = [
        {
            "html": os.path.join(output_dir, "iMeUsWe_AI_Chatbot_Analysis_Report.html"),
            "pdf": os.path.join(output_dir, "iMeUsWe_AI_Chatbot_Analysis_Report.pdf"),
            "name": "Main Analysis Report",
        },
        {
            "html": os.path.join(output_dir, "How_This_Analysis_Was_Built.html"),
            "pdf": os.path.join(output_dir, "How_This_Analysis_Was_Built.pdf"),
            "name": "Technical Walkthrough",
        },
    ]

    print("Generating high-fidelity PDFs using Chromium...\n")

    for report in reports:
        print(f"Converting: {report['name']}")
        if not os.path.exists(report["html"]):
            print(f"  SKIPPED — HTML file not found: {report['html']}")
            continue
        await convert_html_to_pdf(report["html"], report["pdf"])

    print("\nDone. PDFs match the HTML styling exactly.")


if __name__ == "__main__":
    asyncio.run(main())
