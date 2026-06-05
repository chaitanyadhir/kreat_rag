import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DocumentParser(ABC):
    """
    Abstract base class defining the interface for document parsers.
    All concrete parser implementations must subclass this and implement the 'parse' method.
    """
    
    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text content and metadata from the document file.
        
        Args:
            file_path (str): The absolute or relative path to the file.
            
        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents 
                                 a unit of content (e.g., a page or a slide) and contains:
                                 - 'text' (str): The extracted raw text.
                                 - 'metadata' (dict): Metadata including source filename, page/slide number, etc.
        """
        pass


class PDFParser(DocumentParser):
    """
    Concrete parser for PDF documents.
    Uses the 'pypdf' package to extract text page-by-page.
    """
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from a PDF file page by page.
        
        Args:
            file_path (str): Path to the PDF file.
            
        Returns:
            List[Dict[str, Any]]: Pages extracted from the PDF.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")
            
        try:
            import pypdf
        except ImportError:
            raise ImportError(
                "The 'pypdf' library is required to run the PDFParser. "
                "Please install it using: pip install pypdf"
            )
            
        results = []
        reader = pypdf.PdfReader(file_path)
        
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            results.append({
                "text": text.strip(),
                "metadata": {
                    "source": os.path.basename(file_path),
                    "page_number": index + 1,
                    "total_pages": len(reader.pages),
                    "file_type": "pdf"
                }
            })
        return results


class PPTXParser(DocumentParser):
    """
    Concrete parser for PowerPoint (PPTX) presentations.
    Uses the 'python-pptx' package to extract text slide-by-slide.
    """
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from a PPTX file slide by slide.
        
        Args:
            file_path (str): Path to the PPTX file.
            
        Returns:
            List[Dict[str, Any]]: Slides extracted from the PPTX.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PPTX file not found at: {file_path}")
            
        try:
            # pyrefly: ignore [missing-import]
            from pptx import Presentation
        except ImportError:
            raise ImportError(
                "The 'python-pptx' library is required to run the PPTXParser. "
                "Please install it using: pip install python-pptx"
            )
            
        results = []
        prs = Presentation(file_path)
        
        for index, slide in enumerate(prs.slides):
            slide_text_blocks = []
            
            # Iterate through shapes in the slide to find text frames
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    slide_text_blocks.append(shape.text)
                    
            combined_text = "\n".join(slide_text_blocks)
            results.append({
                "text": combined_text.strip(),
                "metadata": {
                    "source": os.path.basename(file_path),
                    "slide_number": index + 1,
                    "total_slides": len(prs.slides),
                    "file_type": "pptx"
                }
            })
        return results


class ParserFactory:
    """
    Factory class that returns the appropriate DocumentParser implementation
    based on the file extension of the document.
    """
    
    @staticmethod
    def get_parser(file_path: str) -> DocumentParser:
        """
        Returns a concrete DocumentParser instance for the given file extension.
        
        Args:
            file_path (str): Path to the document.
            
        Returns:
            DocumentParser: An instance of PDFParser or PPTXParser.
            
        Raises:
            ValueError: If the file format/extension is not supported.
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == ".pdf":
            return PDFParser()
        elif ext in [".pptx", ".ppt"]:
            return PPTXParser()
        else:
            raise ValueError(f"Unsupported file type '{ext}'. Only PDF and PPTX files are supported.")


# ==========================================
# EXAMPLE USAGE (Executable Example in Comments)
# ==========================================
# 
# if __name__ == "__main__":
#     # Example 1: Using the Factory to parse a PDF file
#     pdf_path = "data/example_policy.pdf"
#     try:
#         # Instantiating parser via Factory
#         parser = ParserFactory.get_parser(pdf_path)
#         print(f"Instantiated parser: {type(parser).__name__}")
#         
#         # Parsing the file (will raise ImportError if libraries are missing)
#         parsed_pages = parser.parse(pdf_path)
#         for page in parsed_pages[:2]:  # Print first 2 pages
#             print(f"\n--- Page {page['metadata']['page_number']} ---")
#             print(page['text'][:200] + "...")
#             print(f"Metadata: {page['metadata']}")
#             
#     except Exception as e:
#         print(f"Failed to parse PDF (Expected if file or library is missing): {e}")
# 
#     # Example 2: Using the Factory to parse a PPTX file
#     pptx_path = "data/security_training.pptx"
#     try:
#         parser = ParserFactory.get_parser(pptx_path)
#         parsed_slides = parser.parse(pptx_path)
#         for slide in parsed_slides[:2]:  # Print first 2 slides
#             print(f"\n--- Slide {slide['metadata']['slide_number']} ---")
#             print(slide['text'][:200] + "...")
#     except Exception as e:
#         print(f"Failed to parse PPTX (Expected if file or library is missing): {e}")
