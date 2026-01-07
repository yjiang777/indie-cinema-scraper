"""Normalize movie titles and extract metadata"""
import re

def normalize_title(title):
    """
    Clean up movie title
    - Remove extra whitespace
    - Strip format info (35mm, 70mm, etc.)
    """
    if not title:
        return None
    
    # Remove leading/trailing whitespace
    title = title.strip()
    
    # Remove format indicators in parentheses
    title = re.sub(r'\s*\([^)]*mm\)', '', title)
    title = re.sub(r'\s*\(IB Tech[^)]*\)', '', title)
    
    # Remove "in 35mm", "in 70mm" etc at end
    title = re.sub(r'\s+in \d+mm$', '', title, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    title = re.sub(r'\s+', ' ', title)
    
    return title.strip()

def extract_format(text):
    """
    Extract film format from text
    Returns: "35mm", "70mm", "IB Technicolor 35mm", "Digital", etc.
    """
    if not text:
        return "Digital"
    
    # Look for format indicators
    formats = {
        r'70mm': '70mm',
        r'35mm': '35mm',
        r'16mm': '16mm',
        r'IB Tech': 'IB Technicolor 35mm',
        r'Technicolor': 'Technicolor',
    }
    
    for pattern, format_name in formats.items():
        if re.search(pattern, text, re.IGNORECASE):
            return format_name
    
    return "Digital"

def split_double_feature(title):
    """
    Split double feature titles
    Example: "The Long Goodbye / Night Moves" -> ["The Long Goodbye", "Night Moves"]
    """
    if not title:
        return [title]
    
    # Common separators for double features
    separators = [' / ', ' + ', ' & ']
    
    for sep in separators:
        if sep in title:
            return [t.strip() for t in title.split(sep)]
    
    return [title]