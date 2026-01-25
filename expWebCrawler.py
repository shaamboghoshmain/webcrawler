import os
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class InteractiveSalesforceCrawler:
    def __init__(self):
        self.pdf_css = """
        <style>
            body { font-family: sans-serif; font-size: 11pt; }
            h1 { color: #005fb2; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
            img { max-width: 100%; border: 1px solid #ddd; margin: 10px 0; }
            .siteforce-content-area .slds-breadcrumb, header, footer { display: none !important; }
        </style>
        """

    def clean_filename(self, text):
        return re.sub(r'[\\/*?:"<>|]', "", text).strip()[:100]

    def get_links_interactive(self, page, start_url):
        print("\n--- STEP 1: LOCATING TABLE OF CONTENTS ---")
        print("Scaning for sidebar... (Please wait 10s for expansion)")
        
        # 1. Expand standard Salesforce trees
        try:
            # Force click any "Expand" button found on the left side of the screen
            page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button[title="Expand"], button[aria-expanded="false"]'));
                buttons.forEach(btn => btn.click());
            }""")
            time.sleep(4) # Wait for expansion
        except: pass

        # 2. Extract Links via Text Heuristic (Find "Table of Contents" -> Get Links below it)
        links = page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a'));
            
            // Filter logic: Must contain 'articleView' AND be visible
            return anchors
                .filter(a => a.href.includes('articleView') && a.offsetParent !== null)
                .map(a => ({
                    text: a.innerText.trim(),
                    href: a.href
                }))
                // Simple dedup
                .filter((v,i,a)=>a.findIndex(v2=>(v2.href===v.href))===i);
        }""")

        # 3. Python-side Strict Filtering (The "Anti-Wander" Filter)
        cleaned_links = []
        base_id = "articleView" 
        
        for link in links:
            # Must contain articleView
            if base_id not in link['href']: continue
            
            # Must NOT be a "release note" or "product" landing page unless it's the target
            if "/products/" in link['href']: continue
            
            cleaned_links.append(link)

        # 4. THE INTERACTIVE CHECK
        print(f"\n[!] I found {len(cleaned_links)} potential chapters.")
        if len(cleaned_links) > 0:
            print("--- First 5 links found ---")
            for l in cleaned_links[:5]:
                print(f"   - {l['text']} ({l['href']})")
            print("...")
        
        user_input = input(f"\n>>> Do you want to generate a PDF for these {len(cleaned_links)} pages? (y/n): ")
        if user_input.lower() != 'y':
            return []
            
        return cleaned_links

    def parse_and_save(self, page, links, save_dir, context):
        if not links: return

        print("\n--- STEP 2: GENERATING PDF ---")
        
        # Combine into one HTML
        full_html = f"<html><head>{self.pdf_css}</head><body>"
        
        # Add links to HTML
        for i, link in enumerate(links):
            print(f"[{i+1}/{len(links)}] Fetching: {link['text']}")
            try:
                # Don't reload if on same page
                if page.url != link['href']:
                    page.goto(link['href'], timeout=45000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1) # Wait for content render

                # Extract Content specifically
                content_html = page.evaluate("""() => {
                    // Try to find the specific content box
                    const content = document.querySelector('.siteforce-content-area') || document.querySelector('article');
                    return content ? content.innerHTML : null;
                }""")

                if content_html:
                    full_html += f"<div class='chapter'><h1>{link['text']}</h1>{content_html}</div><div style='page-break-after:always'></div>"
                else:
                    print("   - Skipped (Content not found/Blocked)")

            except Exception as e:
                print(f"   ! Error: {e}")

        full_html += "</body></html>"

        # Save PDF
        filename = self.clean_filename(links[0]['text']) + ".pdf"
        output_path = os.path.join(save_dir, filename)
        
        print(f"Rendering PDF to: {output_path}")
        
        # Render
        print_page = context.new_page()
        print_page.set_content(full_html)
        print_page.pdf(path=output_path, format="A4")
        print_page.close()
        print("Done.")

    def run(self):
        url = input("Enter URL: ").strip()
        save_dir = input("Save Folder: ").strip()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()
            
            print(f"Navigating to {url}...")
            page.goto(url, timeout=60000)
            time.sleep(5) # Let it load fully
            
            # Close Cookie Banner
            try: page.locator("#onetrust-accept-btn-handler").click(timeout=2000)
            except: pass

            links = self.get_links_interactive(page, url)
            
            if links:
                self.parse_and_save(page, links, save_dir, context)
            else:
                print("Operation cancelled by user.")
                
            browser.close()

if __name__ == "__main__":
    crawler = InteractiveSalesforceCrawler()
    crawler.run()