"""
DocuMind AI — Layout Understanding
====================================
WHY WE DO THIS:
    Raw OCR gives us a "bag of lines" (e.g., "The quick", "brown fox", "jumps over").
    If you feed a bag of lines into a Vector Database or LLM, it loses structural context.
    
    A human doesn't read a bag of lines; they read Paragraphs, Headings, and Tables.
    We must algorithmically group these isolated OCR lines back into their original
    semantic structures (Paragraphs) before embedding them for RAG.

HOW IT WORKS:
    We use Spatial Heuristics (Rule-Based Layout Analysis).
    1. We sort all lines on a page from top-to-bottom, left-to-right.
    2. We measure the vertical gap between lines.
    3. If the gap is small, they belong to the same paragraph.
    4. If the gap is large, it's a new paragraph.
    5. If a line is very short and has a large vertical gap below it, it's likely a Heading.
    
    In a more advanced future phase, we would swap this heuristic engine for an 
    AI vision model like LayoutParser or DocTR.
"""

from typing import List
from backend.api.schemas.ocr import OCRPage, OCRLine, BoundingBox
from backend.api.schemas.extraction import TextBlock, StructuredPage

class LayoutAnalyzer:
    """Core logic for semantic document structuring."""

    @staticmethod
    def _calculate_vertical_gap(line1: OCRLine, line2: OCRLine) -> int:
        """Calculates the vertical space between the bottom of line1 and top of line2."""
        return line2.box.y1 - line1.box.y2

    @staticmethod
    def _calculate_line_height(line: OCRLine) -> int:
        """Calculates the height of a text line."""
        return line.box.y2 - line.box.y1

    @staticmethod
    def analyze_page(ocr_page: OCRPage) -> List[TextBlock]:
        """
        Transforms a flat list of OCR lines into structured semantic blocks.
        """
        if not ocr_page.lines:
            return []

        # 1. Sort lines: Top-to-Bottom. If on the same y-level, Left-to-Right.
        # We use a slight tolerance (e.g., 10 pixels) for y-level to handle slight tilts.
        sorted_lines = sorted(ocr_page.lines, key=lambda l: (l.box.y1 // 10, l.box.x1))
        
        blocks: List[TextBlock] = []
        current_block_lines: List[OCRLine] = [sorted_lines[0]]
        
        # Calculate average line height on the page to establish a baseline
        avg_line_height = sum(LayoutAnalyzer._calculate_line_height(l) for l in sorted_lines) / len(sorted_lines)
        
        # Heuristic: A paragraph gap is usually > 1.0x line height, but < 2.5x line height
        # If it's larger, it's a new section. If smaller, it's the next line of the same paragraph.
        paragraph_gap_threshold = avg_line_height * 1.5

        for i in range(1, len(sorted_lines)):
            prev_line = sorted_lines[i-1]
            curr_line = sorted_lines[i]
            
            vertical_gap = LayoutAnalyzer._calculate_vertical_gap(prev_line, curr_line)
            
            # Condition: If the gap is small enough, it's the same paragraph
            # We also check horizontal overlap loosely if we want to be strict,
            # but for MVP, vertical distance is the strongest signal.
            if 0 <= vertical_gap <= paragraph_gap_threshold:
                current_block_lines.append(curr_line)
            else:
                # The gap is too large. We must finalize the current block and start a new one.
                blocks.append(LayoutAnalyzer._finalize_block(current_block_lines))
                current_block_lines = [curr_line]
                
        # Finalize the last block
        if current_block_lines:
            blocks.append(LayoutAnalyzer._finalize_block(current_block_lines))
            
        return blocks

    @staticmethod
    def analyze_document(ocr_doc) -> 'StructuredDocument':
        """
        Transforms a full OCRDocument into a StructuredDocument.
        """
        from backend.api.schemas.extraction import StructuredDocument
        structured_pages = []
        for page in ocr_doc.pages:
            blocks = LayoutAnalyzer.analyze_page(page)
            structured_pages.append(StructuredPage(page_number=page.page_number, blocks=blocks))
            
        return StructuredDocument(
            document_id=ocr_doc.document_id,
            pages=structured_pages
        )

    @staticmethod
    def _finalize_block(lines: List[OCRLine]) -> TextBlock:
        """
        Takes a list of grouped lines, determines if they form a heading or paragraph,
        and merges their text and bounding boxes.
        """
        # Merge text
        # If lines don't end with a hyphen, separate them with a space
        merged_text = ""
        for i, line in enumerate(lines):
            text = line.text.strip()
            if text.endswith('-'):
                # Handle hyphenation across lines (e.g. "import-\nant")
                merged_text += text[:-1]
            else:
                merged_text += text + (" " if i < len(lines) - 1 else "")
                
        # Merge bounding box
        x1 = min(l.box.x1 for l in lines)
        y1 = min(l.box.y1 for l in lines)
        x2 = max(l.box.x2 for l in lines)
        y2 = max(l.box.y2 for l in lines)
        merged_box = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
        
        # Determine Type (Heading vs Paragraph)
        # Heuristic: If it's a single line, short, and title-cased or uppercase, it's a heading.
        block_type = "paragraph"
        if len(lines) == 1:
            words = merged_text.split()
            if len(words) <= 7 and (merged_text.istitle() or merged_text.isupper()):
                block_type = "heading"

        return TextBlock(
            type=block_type,
            text=merged_text,
            box=merged_box,
            lines=lines
        )
