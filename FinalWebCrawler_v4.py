import os
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class SalesforceCleanCrawler:
    def __init__(self):
        self.chapters = []
        self.visited_urls = set() # To track which pages have been successfully processed
        self.pdf_css = """
        <style>
            body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #222; }
            h1 { color: #005fb2; font-size: 24pt; border-bottom: 2px solid #005fb2; padding-bottom: 10px; margin-top: 0; page-break-before: always; }
            h2 { color: #005fb2; font-size: 18pt; margin-top: 25px; }
            h3 { font-size: 14pt; margin-top: 15px; color: #333; }
            img { max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; }
            pre { background: #f4f6f9; border: 1px solid #d8dde6; padding: 10px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; font-size: 9pt; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
            th { background-color: #f3f2f2; }
            a { color: #005fb2; text-decoration: none; }
            .chapter-meta { font-size: 9pt; color: #777; margin-bottom: 20px; font-style: italic; border-bottom: 1px solid #eee; padding-bottom: 5px; }
            
            /* HIDE UI ELEMENTS for PDF */
            .siteforce-header, .siteforce-footer, header, footer, nav, aside { display: none !important; }
            .slds-breadcrumb, .cHelpFeedback, .feedback-component, .slds-docked-composer { display: none !important; }
            #onetrust-banner-sdk, #onetrust-consent-sdk, .onetrust-pc-dark-filter { display: none !important; }
            button, .slds-button, iframe { display: none !important; }
            /* Hide Salesforce's default "You are here:" and "See Also" in the article body */
            .article-body .you-are-here, .article-body .see-also-section { display: none !important; }
        </style>
        """

    def clean_filename(self, text):
        return re.sub(r'[\\/*?:"<>|]', "", text).strip()[:100]

    def normalize_url_for_dedup(self, url):
        """Standardizes Salesforce Help URLs to prevent duplicates by query params."""
        parsed = urlparse(url)
        if 'articleView' in parsed.path:
            qs = parse_qs(parsed.query)
            new_qs = {}
            if 'id' in qs: new_qs['id'] = qs['id']
            if 'type' in qs: new_qs['type'] = qs['type']
            # Reconstruct URL with only 'id' and 'type'
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(new_qs, doseq=True), ''))
        return url

    def get_links_interactively(self, page, hub_url):
        """
        Loads the Hub page, asks for user interaction to clear modals,
        then extracts relevant article links from the *main content area*.
        """
        print(f"    -> Navigating to Hub: {hub_url}")
        page.goto(hub_url, timeout=90000) # Increased timeout for hub

        # --- MANUAL INTERVENTION STEP ---
        print("\n" + "!"*60)
        print(" ACTION REQUIRED:")
        print(" 1. A browser window has opened.")
        print(" 2. Please CLOSE any Cookie/Region popups manually (e.g., 'Reject All').")
        print(" 3. SCROLL down slowly to the bottom of the page to load all content cards/tiles.")
        print(" 4. When the page looks fully loaded and clean, come back here and PRESS ENTER.")
        print("!"*60 + "\n")
        input(">>> Press ENTER to continue scraping links from this page...")
        # --------------------------------

        print("    -> Extracting links from the main content body...")
        
        # We grab all links visible on the page after user interaction
        # We try to get from the main article container, but fallback to body
        links_from_js = page.evaluate("""() => {
            const getVisibleAnchors = (element) => {
                const anchors = Array.from(element.querySelectorAll('a'));
                return anchors
                    .filter(a => a.offsetParent !== null && a.href.includes('articleView') && a.innerText.trim().length > 2)
                    .map(a => ({ text: a.innerText.trim(), href: a.href }));
            };

            let mainContent = document.querySelector('.siteforce-content-area') || 
                              document.querySelector('article') || 
                              document.querySelector('[role="main"]');
            
            if (mainContent) {
                return getVisibleAnchors(mainContent);
            } else {
                // Fallback to body, but apply strict filters later in Python
                return getVisibleAnchors(document.body);
            }
        }""")
        
        valid_links = []
        seen_urls = set() # Stores normalized URLs

        # Add Hub Page first
        hub_clean_url = self.normalize_url_for_dedup(hub_url)
        # We'll put a placeholder title for the hub; it will be updated when parsed
        valid_links.append({'title': 'Hub Page', 'url': hub_url}) 
        seen_urls.add(hub_clean_url)

        # Detect the prefix of the Hub URL (e.g., 'ind.') for filtering children
        hub_id_match = re.search(r'id=([^&]+)', hub_url)
        hub_prefix = ""
        if hub_id_match:
            full_id = hub_id_match.group(1)
            # Example: 'ind.get_started_with_business_rules_engine.htm' -> 'ind.'
            # Example: 'bre_learn_explore.htm' -> 'bre_'
            parts = full_id.split('.')
            if len(parts) > 1:
                hub_prefix = parts[0] + "." # e.g. "ind."
            elif '_' in full_id:
                hub_prefix = full_id.split('_')[0] + "_" # e.g. "bre_"
        
        print(f"       * Detected URL ID Prefix: '{hub_prefix}' (Used for filtering child links)")
        
        for link in links_from_js:
            url = link['href']
            clean_url = self.normalize_url_for_dedup(url)
            
            # Filter:
            # 1. Must be a unique URL
            # 2. Must contain the expected prefix (e.g., 'ind.') or be a core Salesforce system doc ('sf.')
            # 3. Must NOT be a login/product/community page
            if (hub_prefix in url or "sf." in url) and \
               "login" not in url and \
               "/products/" not in url and \
               "/community/" not in url and \
               url not in seen_urls: # Check against raw URL initially
               
                valid_links.append({'title': link['text'], 'url': url})
                seen_urls.add(url) # Store original URL for crawling

        return valid_links

    def parse_page_content_only(self, page, url):
        """
        Navigates to URL, injects CSS, extracts ONLY the core article content.
        """
        print(f"    -> Loading content for: {url}")
        
        try:
            # Navigate to the page
            if page.url != url: # Avoid re-navigating for the first page
                page.goto(url, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2) # Give it time for LWC to fully render the content
            
            # Inject CSS to clean elements
            page.add_style_tag(content=self.pdf_css)

            # Wait for the CORE content container to appear
            # Trying multiple robust selectors for the actual article content
            content_locator = page.locator(".siteforce-content-area, article, [role='main'], .slds-text-longform, c-help-article")
            content_locator.first.wait_for(state="visible", timeout=15000)

        except Exception as e:
            print(f"       ! Failed to load/find content for {url}: {e}")
            return None

        # Extract content using Playwright for Shadow DOM, then parse with BS4
        main_html = page.evaluate("""() => {
            let contentElement = document.querySelector('.siteforce-content-area') || 
                                 document.querySelector('article') || 
                                 document.querySelector('[role="main"]') || 
                                 document.querySelector('.slds-text-longform') ||
                                 document.querySelector('c-help-article'); // Specific Salesforce component
            
            if (!contentElement) {
                // Fallback to body but try to clean aggressively
                console.log('No specific content element found, falling back to body.');
                contentElement = document.body;
                // Aggressive cleaning on body if used
                Array.from(contentElement.querySelectorAll('header, footer, nav, aside, .siteforce-sidebar-container, .slds-breadcrumb')).forEach(el => el.remove());
            }

            // Remove internal 'You are here' or 'See Also' if they are within the content
            Array.from(contentElement.querySelectorAll('.you-are-here, .see-also-section')).forEach(el => el.remove());

            return contentElement ? contentElement.innerHTML : null;
        }""")

        if not main_html:
            print(f"       ! No usable HTML extracted from {url}.")
            return None

        soup = BeautifulSoup(main_html, 'html.parser')
        
        # Get Title from the extracted content
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "Chapter"

        # Fix Images to Absolute URLs (again, after innerHTML extraction)
        for img in soup.find_all('img'):
            if img.get('src'):
                img['src'] = urljoin(url, img['src'])

        return {'title': title, 'url': url, 'html': str(soup)}

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

        temp_file = os.path.abspath("temp_interactive_export.html")
        with open(temp_file, "w", encoding="utf-8") as f: f.write(html)

        try:
            page = browser_context.new_page()
            page.goto(f"file:///{temp_file}")
            # Give it a moment to render all images etc.
            page.wait_for_timeout(3000) 
            page.pdf(path=output_path, format="A4", margin={"top":"2cm","bottom":"2cm","left":"2cm","right":"2cm"}, print_background=True)
            print(f" -> Success! PDF saved to: {output_path}")
        except Exception as e:
            print(f"Error printing PDF: {e}")
        finally:
            page.close()
            if os.path.exists(temp_file): os.remove(temp_file)

    def run(self):
        hub_url = input("Enter Hub URL: ").strip()
        save_dir = input("Enter output folder: ").strip()
        
        if not os.path.exists(save_dir):
            try: os.makedirs(save_dir)
            except: save_dir = "."

        with sync_playwright() as p:
            # HEADLESS=FALSE IS CRITICAL FOR USER INTERACTION
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1400, "height": 1000})
            page = context.new_page()

            # 1. Interactive Link Gathering (User closes popups, scrolls)
            links_to_crawl = self.get_links_interactively(page, hub_url)
            
            if not links_to_crawl:
                print("No relevant links captured after interactive step.")
                browser.close()
                return

            print(f" -> Found {len(links_to_crawl)} chapters. Starting content extraction...")

            # 2. Crawl and Parse each page
            for i, link in enumerate(links_to_crawl):
                print(f"    [{i+1}/{len(links_to_crawl)}] Fetching: {link['title'][:50]}...")
                content = self.parse_page_content_only(page, link['url'])
                if content:
                    self.chapters.append(content)
                    print("       + Added chapter.")
                else:
                    print("       - Skipped chapter (Content not found or error).")

            # 3. Generate PDF
            if self.chapters:
                safe_name = self.clean_filename(self.chapters[0]['title'])
                out_path = os.path.join(save_dir, f"{safe_name}_Guide.pdf")
                self.generate_pdf(out_path, context)
            else:
                print("No chapters found to create PDF.")

            browser.close()

if __name__ == "__main__":
    crawler = SalesforceCleanCrawler()
    crawler.run()