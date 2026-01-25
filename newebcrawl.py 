import time
import random
import re
from urllib.parse import urljoin, urlparse

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Parsing Imports
from bs4 import BeautifulSoup

# PDF Imports
from fpdf import FPDF

# --- Configuration ---
MAX_WORDS = 500000
visited_urls = set()
url_queue = []
chapter_data = [] # Stores dicts: {'title': str, 'level': int, 'content': str}

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, 'Documentation Export', align='R')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 16)
        self.multi_cell(0, 10, title)
        self.ln(5)

    def sub_chapter_title(self, title):
        self.set_font('helvetica', 'B', 14)
        self.multi_cell(0, 10, title)
        self.ln(3)

    def body_text(self, text):
        self.set_font('helvetica', '', 11)
        # Clean specific unicode chars that might break latin-1
        text = text.encode('latin-1', 'replace').decode('latin-1') 
        self.multi_cell(0, 5, text)
        self.ln()

def setup_driver():
    """Setup Chrome Driver with anti-bot detection measures"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    # Fake a real user agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def clean_text(text):
    """Remove extra whitespace"""
    return re.sub(r'\s+', ' ', text).strip()

def extract_content(soup, url):
    """
    Parses HTML to find Main Content.
    Logic: Looks for <main>, <article>, or specific Salesforce classes.
    """
    # 1. Try to find the main content area
    content_div = soup.find('main')
    if not content_div:
        content_div = soup.find('article')
    if not content_div:
        # Fallback for generic sites
        content_div = soup.find('body')

    # Remove script and style elements from the content
    for script in content_div(["script", "style", "nav", "footer", "header"]):
        script.extract()

    # Extract Title
    title = "Untitled Chapter"
    h1 = content_div.find('h1')
    if h1:
        title = h1.get_text().strip()
    else:
        # Fallback to page title
        if soup.title:
            title = soup.title.string

    # Extract Text structure for PDF
    # We iterate over children to maintain H2/Paragraph hierarchy
    elements = []
    
    # Simple parser: Grab H2, H3, and P tags
    for tag in content_div.find_all(['h2', 'h3', 'p', 'li']):
        text = clean_text(tag.get_text())
        if not text:
            continue
            
        if tag.name == 'h2':
            elements.append({'type': 'sub', 'text': text})
        elif tag.name == 'h3':
            elements.append({'type': 'sub_sub', 'text': text})
        else:
            elements.append({'type': 'text', 'text': text})

    return title, elements

def get_internal_links(soup, base_url, parent_domain_path):
    """
    Finds links in the page that belong to the same guide section.
    """
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)
        
        # Remove fragment identifiers (#section-name)
        full_url = full_url.split('#')[0]

        # Check if URL belongs to the same guide/path to prevent crawling the whole internet
        if parent_domain_path in full_url and full_url not in visited_urls:
            links.append(full_url)
    return links

def crawl_page(driver, url, parent_path):
    if url in visited_urls:
        return None
    
    print(f"Crawling: {url}")
    try:
        driver.get(url)
        
        # WAITING LOGIC: Wait for the main body or h1 to load (handles dynamic salesforce pages)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            # Add a small random sleep for anti-bot behavior
            time.sleep(random.uniform(1.5, 3.0))
        except:
            print(f"Timeout waiting for {url}, attempting parse anyway...")

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Extract Data
        title, content_elements = extract_content(soup, url)
        
        # Mark visited
        visited_urls.add(url)
        
        # Find children links
        new_links = get_internal_links(soup, url, parent_path)
        
        return {
            'url': url,
            'title': title,
            'content': content_elements,
            'links': new_links
        }

    except Exception as e:
        print(f"Error crawling {url}: {e}")
        return None

def create_pdf(chapters, filename):
    print(f"Generating PDF: {filename}...")
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    total_words = 0
    
    for chapter in chapters:
        pdf.add_page()
        pdf.chapter_title(chapter['title'])
        
        for item in chapter['content']:
            if total_words > MAX_WORDS:
                print("Max word count reached. Finalizing PDF.")
                break
            
            if item['type'] == 'sub':
                pdf.ln(2)
                pdf.sub_chapter_title(item['text'])
            elif item['type'] == 'sub_sub':
                pdf.set_font('helvetica', 'B', 12)
                pdf.cell(0, 10, item['text'])
                pdf.ln(5)
            else:
                pdf.body_text(item['text'])
                total_words += len(item['text'].split())
        
        if total_words > MAX_WORDS:
            break

    pdf.output(filename)
    print(f"PDF Saved successfully. Total estimated words: {total_words}")

def main():
    print("--- Knowledge Guide Web Crawler to PDF ---")
    start_url = input("Enter the Parent URL: ").strip()
    output_path = input("Enter path/filename to store PDF (e.g., Guide.pdf): ").strip()
    
    if not output_path.endswith('.pdf'):
        output_path += '.pdf'

    # Determine the "Scope" of the crawl based on the parent URL
    # We only crawl pages that start with the same directory path
    parsed_start = urlparse(start_url)
    parent_path = parsed_start.path.rsplit('/', 1)[0] # e.g., /docs/guide/
    
    driver = setup_driver()
    
    # BFS Queue
    queue = [start_url]
    all_chapters = []
    
    try:
        while queue:
            current_url = queue.pop(0)
            
            if current_url in visited_urls:
                continue
            
            data = crawl_page(driver, current_url, parent_path)
            
            if data:
                all_chapters.append(data)
                # Add found links to queue
                for link in data['links']:
                    if link not in visited_urls and link not in queue:
                        queue.append(link)
                        
            # Safety break to prevent infinite loops during testing
            if len(all_chapters) > 100: 
                print("Safety limit of 100 pages reached.")
                break
                
    except KeyboardInterrupt:
        print("\nStopping crawl manually...")
    finally:
        driver.quit()
        
    if all_chapters:
        create_pdf(all_chapters, output_path)
    else:
        print("No content found.")

if __name__ == "__main__":
    main()