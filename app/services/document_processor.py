import os
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import docx


class DocumentProcessor:
    """
    Document parsing service for PDF, DOCX, and TXT files.
    Extracts text while preserving page numbers for PDF citations.
    """

    SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt"}

    @classmethod
    def is_supported(cls, file_type: str) -> bool:
        return file_type.lower() in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def extract_text(cls, file_path: str, file_type: str) -> List[Dict[str, Optional[Any]]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        normalized_type = file_type.lower().lstrip(".")
        if not cls.is_supported(normalized_type):
            raise ValueError(f"Unsupported document format: '{normalized_type}'. Allowed: PDF, DOCX, TXT.")

        if normalized_type == "pdf":
            return cls._extract_pdf(file_path)
        elif normalized_type == "docx":
            return cls._extract_docx(file_path)
        elif normalized_type == "txt":
            return cls._extract_txt(file_path)
        else:
            raise ValueError(f"Unhandled file type: {normalized_type}")

    @staticmethod
    def _extract_pdf(file_path: str) -> List[Dict[str, Optional[Any]]]:
        pages = []
        try:
            doc = fitz.open(file_path)
            for page_index in range(len(doc)):
                page = doc[page_index]
                text = page.get_text("text") or ""
                pages.append({
                    "text": text.strip(),
                    "page_number": page_index + 1
                })
            doc.close()
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

        return pages

    @staticmethod
    def _extract_docx(file_path: str) -> List[Dict[str, Optional[Any]]]:
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
            full_text = "\n\n".join(paragraphs)
            return [{
                "text": full_text.strip(),
                "page_number": None
            }]
        except Exception as e:
            raise ValueError(f"Failed to extract text from DOCX: {str(e)}")

    @staticmethod
    def _extract_txt(file_path: str) -> List[Dict[str, Optional[Any]]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return [{
                "text": content.strip(),
                "page_number": None
            }]
        except Exception as e:
            raise ValueError(f"Failed to read TXT file: {str(e)}")
