import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Pattern to match grounding tags: <|ref|>label<|/ref|><|det|>[[x1,y1,x2,y2]]<|/det|>
GROUNDING_PATTERN = re.compile(
    r'<\|ref\|>(?P<label>.*?)<\|/ref\|>\s*<\|det\|>\[\[(?P<coords>[\d,\s]+)\]\]<\|/det\|>\s*(?P<content>.*?)(?=<\|ref\||$)',
    re.DOTALL
)

def convert_deepseek_to_paddle_schema(markdown_text: str, image_width: int, image_height: int) -> Dict[str, Any]:
    """
    Convert DeepSeek OCR grounding-tagged Markdown output to PaddleOCR-compatible schema.
    
    Args:
        markdown_text: DeepSeek OCR output with grounding tags
        image_width: Original image width in pixels
        image_height: Original image height in pixels
    
    Returns:
        PaddleOCR-compatible dict: {"words": [{"id": 0, "content": "...", "rec_score": 1.0, "points": [[x1,y1],...]}]}
    """
    logger.info(f"Converting DeepSeek output to PaddleOCR schema (image: {image_width}x{image_height})")
    logger.info(f"Raw DeepSeek output: {markdown_text[:500]}...")  # Log first 500 chars
    
    words = []
    word_id = 0
    
    # Find all grounding tag matches
    matches = GROUNDING_PATTERN.finditer(markdown_text)
    
    for match in matches:
        try:
            label = match.group('label').strip()
            coords_str = match.group('coords').strip()
            content = match.group('content').strip()
            
            # Parse coordinates: "x1, y1, x2, y2"
            coords = [int(c.strip()) for c in coords_str.split(',')]
            if len(coords) != 4:
                logger.warning(f"Invalid coordinates: {coords_str}")
                continue
            
            x1, y1, x2, y2 = coords
            
            # Denormalize coordinates (0-999 -> actual pixels)
            actual_x1 = int((x1 / 999.0) * image_width)
            actual_y1 = int((y1 / 999.0) * image_height)
            actual_x2 = int((x2 / 999.0) * image_width)
            actual_y2 = int((y2 / 999.0) * image_height)
            
            # Convert to 4-point format (top-left, top-right, bottom-right, bottom-left)
            points = [
                [actual_x1, actual_y1],  # top-left
                [actual_x2, actual_y1],  # top-right
                [actual_x2, actual_y2],  # bottom-right
                [actual_x1, actual_y2]   # bottom-left
            ]
            
            # Extract text content from HTML
            text_content = extract_text_from_html(content)
            
            if text_content:
                word = {
                    "id": word_id,
                    "content": text_content,
                    "rec_score": 1.0,  # DeepSeek doesn't provide confidence scores
                    "points": points
                }
                words.append(word)
                word_id += 1
                logger.info(f"Extracted word {word_id}: '{text_content[:50]}...' at {points}")
        
        except Exception as e:
            logger.error(f"Error processing match: {str(e)}")
            continue
    
    logger.info(f"Converted {len(words)} words from DeepSeek output")
    return {"words": words}

def extract_text_from_html(html_content: str) -> str:
    """
    Extract plain text from HTML content, removing all tags.
    
    Args:
        html_content: HTML string (e.g., "<table><tr><td>text</td></tr></table>")
    
    Returns:
        Plain text with spaces between elements
    """
    if not html_content:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<br\s*/?>', ' ', html_content)  # Replace <br> with space
    text = re.sub(r'</tr>', ' ', text)  # Add space after table rows
    text = re.sub(r'</td>', ' ', text)  # Add space after table cells
    text = re.sub(r'<[^>]+>', '', text)  # Remove all other tags
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def format_ocr_result(extracted_text: str, image_width: int, image_height: int) -> Dict[str, Any]:
    """
    Format DeepSeek OCR result to PaddleOCR-compatible format.
    
    Args:
        extracted_text: Raw DeepSeek OCR output (Markdown with grounding tags)
        image_width: Image width in pixels
        image_height: Image height in pixels
    
    Returns:
        PaddleOCR-compatible dict
    """
    try:
        result = convert_deepseek_to_paddle_schema(extracted_text, image_width, image_height)
        logger.info(f"Formatted OCR result: {len(result.get('words', []))} words detected")
        return result
    except Exception as e:
        logger.error(f"Error formatting OCR result: {str(e)}")
        # Return empty result on error
        return {"words": []}

def clean_extracted_text(text: str) -> str:
    """
    Return text as-is for processing (no cleaning needed for grounding tags).
    """
    return text if text else ""
