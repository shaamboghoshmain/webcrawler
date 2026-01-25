import os
import time
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class SalesforceDeepCrawler:
    def __init__(self):
        self.chapters = []
        self.visited_urls = set()
        
        # --- CONFIGURATION ---
        self.MAX_DEPTH = 4       # Increased from 2 to 4 to catch nested pages
        self.MAX_PAGES = 300     # Safety limit to prevent infinite crawling
        self.MAX_WORDS = 800000  # Increased word buffer
        self.current_page_count = 0
        
        self.pdf_css = """
        <style>
            body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #222; }
            h1 { color: #005fb2; font-size: 24pt; border-bottom: 2px solid #005fb2; padding-bottom: 10px; margin-top: 0; page-break-before: always; }
            h2 { color: #005fb2; font-size: 18pt; margin-top: 25px; }
            h3 { font-size: 14pt; color: #333; margin-top: 20px; }
            img { max-width: 100%; height: auto; margin: 15px 0; border: 1px solid #ddd; }
            pre { background: #f4f6f9; border: 1px solid #d8dde6; padding: 10px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; font-size: 9pt; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 9pt; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f3f2f2; }
            a { color: #005fb2; text-decoration: none; }
            .chapter-meta { font-size: 9pt; color: #777; margin-bottom: 20px; font-style: italic; border-bottom: 1px solid #eee; padding-bottom: 5px; }
            
            /* HIDE UI ELEMENTS */
            header, footer, nav, .siteforce-header, .siteforce-footer { display: none !important; }
            .siteforce-sidebar-container, .slds-sidebar { display: none !important; }
            .slds-breadcrumb, .cHelpFeedback, .feedback-component { display: none !important; }
            #onetrust-banner-sdk, #onetrust-consent-sdk, .onetrust-pc-dark-filter { display: none !important; }
            button, .slds-button, iframe { display: none !important; }
        </style>
        """

    def sanitize_filename(self, text):
        return re.sub(r'[\\/*?:"<>|]', "", text).strip()[:100]

    def crawl_page(self, page, url, depth):
        """
        Visits a URL, extracts content, and finds child links.
        """
        if url in self.visited_urls:
            return None
        
        if self.current_page_count >= self.MAX_PAGES:
            return None

        self.visited_urls.add(url)
        self.current_page_count += 1

        indent = "    " * depth
        print(f"{indent}-> [Depth {depth}] Fetching: {url} ...")

        try:
            # 1. Navigate
            page.goto(url, timeout=60000)
            
            # 2. Stabilize (Wait for Network Idle)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except: pass 

            # 3. Clean UI (Cookie Banner)
            try:
                page.locator("#onetrust-accept-btn-handler").click(timeout=1000)
            except: pass
            
            # 4. Inject CSS
            page.add_style_tag(content=self.pdf_css)

            # 5. Find Content Container
            # We try multiple selectors to ensure we catch the body
            selectors = [".siteforce-content-area", "article", "[role='main']", ".slds-text-longform"]
            content_locator = None
            for sel in selectors:
                if page.locator(sel).first.is_visible():
                    content_locator = page.locator(sel).first
                    break
            
            if not content_locator:
                print(f"{indent}   ! Content container not found. Scanning body.")
                content_locator = page.locator("body")

            # 6. Extract HTML & Title
            html_content = content_locator.inner_html()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Untitled"
            
            # 7. Clean HTML (Remove junk)
            for tag in soup(['script', 'style', 'button', 'nav', 'form', 'iframe']): tag.decompose()
            for div in soup.find_all("div", class_=lambda x: x and ('feedback' in x or 'breadcrumb' in x)): div.decompose()
            
            # Fix Images
            for img in soup.find_all('img'):
                if img.get('src'):
                    img['src'] = urljoin(url, img['src'])

            # 8. Find Child Links (if not at max depth)
            child_links = []
            if depth < self.MAX_DEPTH:
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_child_url = urljoin(url, href)
                    
                    # Filter: Must be Salesforce Article, not self, not anchor
                    if "articleView" in full_child_url and full_child_url != url and "#" not in href:
                        if full_child_url not in self.visited_urls:
                            # Basic check to avoid clearly unrelated links (like 'login' or 'home')
                            if "/s/login" not in full_child_url and "/s/home" not in full_child_url:
                                child_links.append(full_child_url)

                # Remove duplicates while preserving order
                child_links = list(dict.fromkeys(child_links))
                if child_links:
                    print(f"{indent}   * Found {len(child_links)} nested links.")

            return {
                'data': {
                    'title': title,
                    'url': url,
                    'html': str(soup)
                },
                'children': child_links
            }

        except Exception as e:
            print(f"{indent}   ! Error: {e}")
            return None

    def process_queue_dfs(self, page, start_url):
        """
        Depth-First Search to keep "Book" ordering.
        """
        # Stack: (url, depth)
        stack = [(start_url, 0)]
        
        while stack:
            # Check limits inside loop
            if self.current_page_count >= self.MAX_PAGES:
                print("\n!!! Max Page Limit Reached (300 pages). Finishing up... !!!")
                break

            url, depth = stack.pop()
            
            result = self.crawl_page(page, url, depth)
            
            if result:
                self.chapters.append(result['data'])
                
                # Add children to stack (Reverse so first child is processed first)
                children = result['children']
                for child_url in reversed(children):
                    stack.append((child_url, depth + 1))

    def generate_pdf(self, output_path, browser_context):
        if not self.chapters: return
        print(f"\n -> Compiling PDF ({len(self.chapters)} chapters)...")
        
        html = f"<html><head>{self.pdf_css}</head><body>"
        
        # Cover
        html += f"""
        <div style="text-align: center; padding-top: 200px;">
            <h1 style="border: none; font-size: 36pt;">Salesforce Documentation</h1>
            <h2>{self.chapters[0]['title']}</h2>
            <p><strong>Source:</strong> {self.chapters[0]['url']}</p>
            <p><strong>Generated:</strong> {time.strftime('%Y-%m-%d')}</p>
        </div>
        <div style="page-break-after: always;"></div>
        """
        
        # TOC
        html += "<h1>Table of Contents</h1><ul>"
        for i, ch in enumerate(self.chapters):
            html += f"<li><a href='#chap{i}'>{ch['title']}</a></li>"
        html += "</ul><div style='page-break-after: always;'></div>"

        # Content
        for i, ch in enumerate(self.chapters):
            html += f"<div id='chap{i}'>"
            html += f"<div class='chapter-meta'>Source: {ch['url']}</div>"
            html += ch['html']
            html += "</div><div style='page-break-after: always;'></div>"
        
        html += "</body></html>"

        temp_file = os.path.abspath("temp_deep_export.html")
        with open(temp_file, "w", encoding="utf-8") as f: f.write(html)

        try:
            page = browser_context.new_page()
            page.goto(f"file:///{temp_file}")
            # Give it time to render a large file
            page.wait_for_load_state("networkidle", timeout=60000)
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

            print(f" -> Starting Deep Crawl (Max Depth {self.MAX_DEPTH}, Max Pages {self.MAX_PAGES})...")
            self.process_queue_dfs(page, start_url)

            if self.chapters:
                safe_name = self.sanitize_filename(self.chapters[0]['title'])
                out_path = os.path.join(save_dir, f"{safe_name}_FullGuide.pdf")
                self.generate_pdf(out_path, context)
            else:
                print("No chapters found.")

            browser.close()

if __name__ == "__main__":
    crawler = SalesforceDeepCrawler()
    crawler.run()