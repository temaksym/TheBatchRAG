import requests
from bs4 import BeautifulSoup
import json
import os
import time
from urllib.parse import urljoin, urlparse
from PIL import Image
import io
from dataclasses import dataclass
from typing import List, Optional, Dict
import logging
import re

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager


@dataclass
class Article:
    title: str
    content: str
    url: str
    images: List[str]
    metadata: Dict

class BatchScraper:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config['scraping']['user_agent']
        })
        
    def scrape_articles(self) -> List[Article]:
        articles = []
        base_url = self.config['scraping']['base_url']
        
        try:
            response = self.session.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            article_links = self._get_all_pages_links(base_url)

            logging.info(f"Found {len(article_links)} articles to scrape.")
            
            for i, link in enumerate(article_links[:self.config['scraping']['max_articles']]):
                try:
                    article = self._scrape_single_article(link)
                    if article:
                        articles.append(article)
                        logging.info(f"Scraped article {i+1}: {article.title}")
                    
                    time.sleep(self.config['scraping']['delay_seconds'])
                    
                except Exception as e:
                    logging.error(f"Error scraping article {link}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error scraping main page: {e}")
            
        return articles
    

    def _find_load_more_by_text(self, driver):
        load_more_pattern = 'Load More'
        xpath = f"//div[contains(text(), '{load_more_pattern}')]"
            
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    return element, load_more_pattern
        except:
            logging.error("Error finding Load More button by text.")

    def _get_all_pages_links(self, base_url: str) -> List[str]:
        """Navigate through all pages and collect article links"""

        categories_pages = [
            "",
            "/tag/letters/"
        ]
        categories_load_more = [
            "/tag/data-points/",
            "/tag/business/",
            "/tag/science/",
            "/tag/culture/",
            "/tag/hardware/",
            "/tag/ai-careers/",
        ]

        all_links = []

        # Trying to scrape pages with "pages"
        # Iterate through categories
        for category in categories_pages:
            try:
                # Find out how many pages total
                response = self.session.get(f"{base_url}{category}")
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                match = re.search(r'Page\s+\d+\s+of\s+(\d+)', soup.get_text())
                if match:
                    total_pages = int(match.group(1))

                logging.info(f"Found {total_pages} pages in category: {category}")

                # Iterate through all pages in the category
                for page in range(1, total_pages + 1):
                    page_url = f"{base_url}{category}/page/{page}/"
                    
                    logging.info(f"Scraping page {page}: {page_url}")
                    response = self.session.get(page_url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    page_links = set()
                    
                    if category == "":
                        page_link_elements = soup.select('article > div:nth-of-type(2) > a:nth-of-type(2)')
                    elif category == "/tag/letters/":
                        page_link_elements = soup.select('article > div:nth-of-type(2) > a:nth-of-type(1)')
                    
                    for el in page_link_elements:
                        href = el.get('href')
                        if href:
                            page_links.add("https://www.deeplearning.ai/"+href)

                    if not page_links:
                        logging.info(f"No more articles found on page {page}")
                        break

                    logging.info(f"Found {len(page_links)} articles on page {page}")
                    
                    all_links.extend(page_links)
                
            except Exception as e:
                logging.error(f"Error scraping pages: {e}")
        

        # Trying to scrape pages with "Load More"
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)

        
        for category in categories_load_more:
            try:
                driver.get(f"{base_url}{category}")
                time.sleep(2)

                iteration = 0
                while True:
                    iteration += 1

                    elements = driver.find_elements(By.CSS_SELECTOR, 'article > div:nth-of-type(2) > a:nth-of-type(2)')
        
                    current_links = set()
                    for el in elements:
                        href = el.get_attribute('href')
                        if href:
                            current_links.add(href)
                    
                    new_links = current_links - set(all_links)
                    all_links.extend(new_links)
                    
                    
                    # Find Load More button
                    load_more_button, found_text = self._find_load_more_by_text(driver)
                    
                    if load_more_button:
                        logging.info(f"Found Load More button with text: '{found_text}'")
                        driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", load_more_button)
                        time.sleep(3)
                    else:
                        logging.info("No Load More button found. Scraping complete.")
                        break
                    
                    if len(new_links) == 0:
                        logging.info("No new links found, stopping.")
                        break
            
            except Exception as e:
                logging.error(f"Error scraping 'Load More' pages: {e}")
            finally:
                driver.quit()

        return all_links
    

    def _scrape_single_article(self, url: str) -> Optional[Article]:
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Scraping title
            try: 
                title = soup.select_one('article > header > div > div > div > div > h1').get_text(strip=True)
            except:
                title = "No title found"

            # Scraping content
            content_div = soup.select_one('main > div > article > div > div')
            
            if content_div:
                text_parts = []

                tags_to_extract = ['h1', 'h2', 'h3', 'p', 'ul', 'ol']

                for tag in content_div.find_all(tags_to_extract):
                    if tag.name in ['ul', 'ol']:
                        for li in tag.find_all('li'):
                            text_parts.append(f"- {li.get_text(strip=True)}")
                    else:
                        text_parts.append(tag.get_text(strip=True))

                full_text = '\n\n'.join(text_parts)

            else:
                print("Content section not found.")

            # Scraping images
            images = self._extract_images(soup, url)
            
            # Scraping metadata
            date_tag = soup.find('time')
            publication_date = date_tag.get_text(strip=True) if date_tag else 'N/A'

            metadata = {}
            metadata['publication_date'] = publication_date

            # Passing data to Article object
            if full_text:
                return Article(
                    title=title,
                    content=full_text,
                    url=url,
                    images=images,
                    metadata=metadata
                )
                
        except Exception as e:
            logging.error(f"Error scraping article {url}: {e}")
            
        return None
    
    
    def _extract_images(self, soup, base_url) -> List[str]:
        """Extract image URLs"""
        images = []
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(base_url, src)
                if self._is_valid_image_url(full_url):
                    images.append(full_url)
        
        return images
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme in ['http', 'https']:
                return False
            
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            return any(url.lower().endswith(ext) for ext in valid_extensions)
            
        except:
            return False
    
    def download_images(self, articles: List[Article], image_dir: str):
        """Download images for articles"""
        os.makedirs(image_dir, exist_ok=True)
        
        for article in articles:
            for i, image_url in enumerate(article.images):
                try:
                    response = self.session.get(image_url, timeout=10)
                    response.raise_for_status()
                    
                    # Save image
                    image_name = f"{hash(article.url)}_{i}.jpg"
                    image_path = os.path.join(image_dir, image_name)
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Update article with local path
                    article.images[i] = image_path
                    
                except Exception as e:
                    logging.error(f"Error downloading image {image_url}: {e}")