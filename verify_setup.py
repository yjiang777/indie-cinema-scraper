#!/usr/bin/env python3
"""Verify development environment setup for Apple Silicon Mac"""

import sys
import platform

def check_environment():
    """Check Python and system info"""
    print("🔍 System Information:")
    print(f"   Python version: {sys.version}")
    print(f"   Platform: {platform.platform()}")
    print(f"   Processor: {platform.processor()}")
    print(f"   Machine: {platform.machine()}")
    
    if platform.machine() != 'arm64':
        print("\n⚠️  Warning: Not running native ARM Python!")
        print("   Consider reinstalling Python via Homebrew")
    else:
        print("\n✅ Running native ARM Python")

def check_imports():
    """Check if all required packages are installed"""
    print("\n🔍 Checking installed packages:")
    
    packages = {
        'requests': 'requests',
        'bs4': 'beautifulsoup4',
        'playwright': 'playwright',
        'sqlalchemy': 'sqlalchemy',
        'dotenv': 'python-dotenv',
        'pydantic': 'pydantic',
        'dateutil': 'python-dateutil',
        'pytz': 'pytz',
    }
    
    missing = []
    for import_name, package_name in packages.items():
        try:
            __import__(import_name)
            print(f"   ✅ {package_name}")
        except ImportError:
            print(f"   ❌ {package_name}")
            missing.append(package_name)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        sys.exit(1)
    else:
        print("\n✅ All packages installed successfully!")

def check_playwright():
    """Check if Playwright browser is installed"""
    print("\n🔍 Checking Playwright:")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("   ✅ Playwright chromium browser installed")
    except Exception as e:
        print(f"   ❌ Playwright issue: {e}")
        print("   Run: playwright install chromium")

if __name__ == "__main__":
    print("=" * 60)
    print("Indie Cinema Scraper - Environment Verification")
    print("=" * 60)
    
    check_environment()
    check_imports()
    check_playwright()
    
    print("\n" + "=" * 60)
    print("✅ Setup verification complete! Ready to code!")
    print("=" * 60)
