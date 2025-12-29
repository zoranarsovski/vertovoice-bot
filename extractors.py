"""
Content Extractors
Extract text content from URLs and PDF files
"""

import os
import requests
import tempfile
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import PyPDF2

logger = logging.getLogger(__name__)

# Headers to mimic browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def extract_from_url(url: str) -> str:
    """
    Extract main content from a URL
    Returns the text content or None if extraction fails
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe']):
            element.decompose()
        
        # Try to find the main content area
        main_content = None
        
        # Common article/content selectors
        content_selectors = [
            'article',
            '[role="main"]',
            '.post-content',
            '.article-content',
            '.entry-content',
            '.content',
            'main',
            '.blog-post',
            '.post-body',
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # Fallback to body
        if not main_content:
            main_content = soup.body
        
        if not main_content:
            return None
        
        # Get title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.get_text().strip()
        
        # Extract text
        paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li'])
        text_parts = []
        
        for p in paragraphs:
            text = p.get_text().strip()
            if text and len(text) > 20:  # Filter out very short fragments
                text_parts.append(text)
        
        content = '\n\n'.join(text_parts)
        
        # Add title at the beginning
        if title:
            content = f"# {title}\n\n{content}"
        
        # Basic cleanup
        content = ' '.join(content.split())  # Normalize whitespace
        
        logger.info(f"Extracted {len(content)} characters from {url}")
        
        return content if len(content) > 100 else None
        
    except requests.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return None


def extract_from_pdf(file_url: str, slack_client) -> str:
    """
    Extract text from a PDF file shared in Slack
    Downloads the file using Slack auth and extracts text
    """
    try:
        # Download file from Slack (requires auth)
        headers = {
            'Authorization': f'Bearer {slack_client.token}'
        }
        
        response = requests.get(file_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        try:
            # Extract text from PDF
            text_parts = []
            
            with open(tmp_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    
                    # Limit to first 20 pages
                    if page_num >= 19:
                        text_parts.append("\n[Content truncated - PDF exceeds 20 pages]")
                        break
            
            content = '\n\n'.join(text_parts)
            
            # Basic cleanup
            content = ' '.join(content.split())
            
            logger.info(f"Extracted {len(content)} characters from PDF")
            
            return content if len(content) > 100 else None
            
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except requests.RequestException as e:
        logger.error(f"Error downloading PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting PDF content: {e}")
        return None


def extract_from_text(text: str) -> str:
    """
    Simple passthrough for plain text input
    Just cleans up the text
    """
    if not text:
        return None
    
    # Basic cleanup
    content = ' '.join(text.split())
    
    return content if len(content) > 50 else None
