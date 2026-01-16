"""Base class for Playwright-based scrapers"""
from playwright.sync_api import sync_playwright, Page
import time
from typing import List, Dict, Optional

class PlaywrightScraper:
    """Base scraper using Playwright for JS-heavy sites"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def __enter__(self):
        """Context manager entry"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = self.context.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def navigate_and_wait(self, url: str, wait_for: Optional[str] = None, timeout: int = 30000, wait_until: str = 'networkidle'):
        """
        Navigate to URL and wait for content to load
        
        Args:
            url: URL to navigate to
            wait_for: CSS selector to wait for (optional)
            timeout: Max wait time in milliseconds
            wait_until: When to consider navigation complete ('load', 'domcontentloaded', 'networkidle')
        """
        self.page.goto(url, wait_until=wait_until, timeout=timeout)
        
        if wait_for:
            self.page.wait_for_selector(wait_for, timeout=timeout)
        
        # Extra wait for JS to finish
        time.sleep(2)
    
    def get_page_content(self) -> str:
        """Get current page HTML content"""
        return self.page.content()
    
    def click_and_wait(self, selector: str, wait_for: Optional[str] = None):
        """Click element and optionally wait for another element"""
        self.page.click(selector)
        
        if wait_for:
            self.page.wait_for_selector(wait_for)
        
        time.sleep(1)
    
    def scroll_to_bottom(self):
        """Scroll to bottom of page to trigger lazy loading"""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)