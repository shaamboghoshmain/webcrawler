import os
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class SalesforceCleanCrawler:
    def __init__(self):
        self.chapters = []
        self.visited_urls = set()
        
        # --- CONFIGURATION ---
        self.MAX_DEPTH = 5
        self.MAX_PAGES = 200
        self.current_page_count = 0
        
        self.KEYWORDS = [
            "business rules engine", "bre", 
            "decision matrix", "decision matrices",
            "decision table", 
            "expression set", 
            "lookup table",
            "decision explainer",
            "calculation matrix"
        ]
        
        # "Nuclear" CSS to force clean printing
        self.pdf_css = """
        <style>
            @page { margin: 2cm; size: A4; }
            body { 
                font-family: Helvetica, Arial, sans-serif; 
                font-size: 11pt; 
                line-height: 1.6; 
                color: #000;
                background-color: #fff;
            }
            /* Force everything to flow vertically */
            * { 
                position: static !important; 
                float: none !important; 
                height: auto !important; 
                width: auto !important; 
                overflow: visible !important;
                max-width: 100% !important;
            }
            /* Styling */
            h1 { color: #005fb2; font-size: 24pt; border-bottom: 2px solid #ccc; padding-bottom: 10px; margin-top: 50px; page-break-before: always; }
            h2 { color: #333; font-size: 18pt; margin-top: 30px; border-bottom: 1px solid #eee; }
            h3 { font-size: 14pt; margin-top: 20px; color: #555; }
            p { margin-bottom: 15px; text-align: justify; }
            li { margin-bottom: 5px; }
            img { display: block; margin: 20px auto; border: 1px solid #ddd; box-shadow: 2px 2px 5px #eee; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; page-break-inside: auto; }
            tr { page-break-inside: avoid; page-break-after: auto; }
            th, td { border: 1px solid #444; padding: 8px; text-align: left; vertical-align: top; }
            th { background-color: #f0f0f0; font-weight: bold; }
            a { color: #005fb2; text-decoration: none; }
            .source-link { font-size: 9pt; color: #777; margin-bottom: 30px; font-style: italic; }
            
            /* Hide Interface Junk */
            header, footer, nav, iframe, button, .slds-button { display: none !important; }
        </style>
        """

    def sanitize_filename(self, text):
        return re.sub(r'[\\/*?:"<>|]', "", text).strip()[:100]

    def is_relevant(self, text, url):
        blob = (text + " " + url).lower()
        if any(x in blob for x in ["/products/", "/login", "release notes", "known issues", "trust.salesforce"]): return False
        if any(kw in blob for kw in self.KEYWORDS): return True
        if "id=ind.bre" in blob or "id=ind.decision" in blob or "id=ind.expression" in blob: return True
        return False

    def clean_html(self, soup):
        """
        Removes all classes, IDs, and styles to prevent layout overlap.
        """
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'button', 'nav', 'form', 'iframe', 'footer', 'header']):
            tag.decompose()
            
        # Remove Salesforce specific junk containers
        for div in soup.find_all("div", class_=lambda x: x and ('feedback' in x or 'breadcrumb' in x or 'toolbar' in x)):
            div.decompose()
            
        # Strip all attributes except 'src' for images and 'href' for links
        # This ensures no CSS class interferes with our PDF layout
        for tag in soup.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in ['src', 'href', 'rowspan', 'colspan']:
                    del tag[attr]
                    
        return str(soup)

    def crawl_page(self, page, url, depth):
        if url in self.visited_urls: return None
        if self.current_page_count >= self.MAX_PAGES: return None

        self.visited_urls.add(url)
        
        indent = "    " * depth
        print(f"{indent}-> [Depth {depth}] Fetching: {url} ...")

        try:
            page.goto(url, timeout=60000)
            
            # Wait for content
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_selector(".siteforce-content-area, article", state="visible", timeout=15000)
            except: 
                print(f"{indent}   ! Wait timeout. Proceeding with best effort.")

            # Clean UI
            try: page.locator("#onetrust-accept-btn-handler").click(timeout=1000)
            except: pass

            # Extract HTML
            content_locator = page.locator(".siteforce-content-area, article, [role='main']").first
            if not content_locator.is_visible():
                content_locator = page.locator("body") # Fallback

            html_raw = content_locator.inner_html()
            soup = BeautifulSoup(html_raw, 'html.parser')
            
            # Get Title
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Untitled"
            
            # --- CLEANING ---
            clean_html = self.clean_html(soup)
            
            # Fix Images
            # We must re-parse the clean HTML to fix image links easily
            soup_clean = BeautifulSoup(clean_html, 'html.parser')
            for img in soup_clean.find_all('img'):
                if img.get('src'):
                    img['src'] = urljoin(url, img['src'])
            
            final_html = str(soup_clean)

            # Find Child Links
            child_links = []
            if depth < self.MAX_DEPTH:
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_child_url = urljoin(url, href)
                    
                    if "articleView" in full_child_url and full_child_url != url and "#" not in href:
                        if full_child_url not in self.visited_urls:
                            if self.is_relevant(a.get_text(strip=True), full_child_url):
                                child_links.append(full_child_url)

                child_links = list(dict.fromkeys(child_links))
                if child_links:
                    print(f"{indent}   * Found {len(child_links)} relevant sub-topics.")

            self.current_page_count += 1
            return {
                'data': {'title': title, 'url': url, 'html': final_html},
                'children': child_links
            }

        except Exception as e:
            print(f"{indent}   ! Error: {e}")
            return None

    def process_queue_dfs(self, page, start_url):
        stack = [(start_url, 0)]
        while stack:
            if self.current_page_count >= self.MAX_PAGES: break
            url, depth = stack.pop()
            result = self.crawl_page(page, url, depth)
            
            if result:
                self.chapters.append(result['data'])
                for child in reversed(result['children']):
                    stack.append((child, depth + 1))

    def generate_pdf(self, output_path, browser_context):
        if not self.chapters: return
        print(f"\n -> Compiling PDF ({len(self.chapters)} chapters)...")
        
        full_html = f"<html><head>{self.pdf_css}</head><body>"
        
        full_html += f"""
        <div style="text-align: center; padding-top: 200px;">
            <h1 style="border: none; font-size: 36pt;">Salesforce Documentation</h1>
            <p><strong>Pages Scanned:</strong> {len(self.chapters)}</p>
            <p><strong>Generated:</strong> {time.strftime('%Y-%m-%d')}</p>
        </div>
        <div style="page-break-after: always;"></div>
        """
        
        # TOC
        full_html += "<h1>Table of Contents</h1><ul>"
        for i, ch in enumerate(self.chapters):
            full_html += f"<li><a href='#chap{i}'>{ch['title']}</a></li>"
        full_html += "</ul><div style='page-break-after: always;'></div>"

        # Content
        for i, ch in enumerate(self.chapters):
            full_html += f"<div id='chap{i}'>"
            full_html += f"<div class='source-link'>Source: {ch['url']}</div>"
            full_html += ch['html']
            full_html += "</div><div style='page-break-after: always;'></div>"
        
        full_html += "</body></html>"

        temp_file = os.path.abspath("temp_clean_export.html")
        with open(temp_file, "w", encoding="utf-8") as f: f.write(full_html)

        try:
            page = browser_context.new_page()
            page.goto(f"file:///{temp_file}")
            # Wait a long time for images to load
            page.wait_for_load_state("networkidle", timeout=120000) 
            page.pdf(path=output_path, format="A4", margin={"top":"2cm","bottom":"2cm","left":"2cm","right":"2cm"}, print_background=True)
            print(f" -> Success! PDF saved to: {output_path}")
        except Exception as e:
            print(f"Error printing PDF: {e}")
        finally:
            page.close()
            if os.path.exists(temp_file): os.remove(temp_file)

    def run(self):
        start_url = input("Enter Hub URL: ").strip()
        save_dir = input("Enter output folder: ").strip()
        
        if not os.path.exists(save_dir):
            try: os.makedirs(save_dir)
            except: save_dir = "."

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1400, "height": 1000})
            page = context.new_page()

            print(f" -> Starting Clean Harvester (Max Depth {self.MAX_DEPTH})...")
            self.process_queue_dfs(page, start_url)

            if self.chapters:
                safe_name = self.sanitize_filename(self.chapters[0]['title'])
                out_path = os.path.join(save_dir, f"{safe_name}_Clean.pdf")
                self.generate_pdf(out_path, context)
            else:
                print("No chapters found.")

            browser.close()

if __name__ == "__main__":
    crawler = SalesforceCleanCrawler()
    crawler.run()