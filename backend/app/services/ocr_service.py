"""
OCR Service for JM Baryani Invoice Processing.
Uses Tesseract (free) as primary OCR engine via tesserocr bindings.
Supports: PDF, JPG, PNG, TIFF images.
"""

import os
from typing import Tuple
from PIL import Image, ImageEnhance, ImageFilter

from app.config import settings

# Try tesserocr first (C bindings, faster), fall back to pytesseract
try:
    import tesserocr
    OCR_ENGINE = "tesserocr"
except ImportError:
    try:
        import pytesseract
        OCR_ENGINE = "pytesseract"
    except ImportError:
        OCR_ENGINE = None


class OCRService:
    """Handles OCR extraction from various document formats."""

    def __init__(self):
        self.lang = settings.OCR_LANG.split('+')[0]  # Use primary lang
        print(f"OCR Engine: {OCR_ENGINE} | Lang: {self.lang}")

    def extract_text(self, file_path: str, file_type: str) -> Tuple[str, float]:
        """
        Extract text from a file.
        Returns: (extracted_text, confidence_score)
        """
        if not OCR_ENGINE:
            raise RuntimeError("No OCR engine available. Install tesserocr or pytesseract.")

        file_type = file_type.lower()

        if file_type == "pdf":
            return self._process_pdf(file_path)
        elif file_type in ("jpg", "jpeg", "png", "tiff", "bmp"):
            return self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _process_pdf(self, file_path: str) -> Tuple[str, float]:
        """Process PDF - try text extraction first, fall back to OCR."""
        # Method 1: Try pdfplumber for digital/text-based PDFs
        text = self._extract_pdf_text(file_path)
        if text and len(text.strip()) > 50:
            return text.strip(), 95.0

        # Method 2: Fall back to OCR (scanned PDF)
        return self._ocr_pdf(file_path)

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from digital PDF using pdfplumber."""
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
            return ""

    def _ocr_pdf(self, file_path: str) -> Tuple[str, float]:
        """OCR a scanned PDF by converting pages to images."""
        try:
            import fitz  # PyMuPDF
            text_parts = []
            confidences = []

            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img = self._preprocess_image(img)

                page_text, page_conf = self._ocr_image(img)
                text_parts.append(page_text)
                confidences.append(page_conf)

            doc.close()
            full_text = "\n\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            return full_text, avg_confidence
        except Exception as e:
            print(f"PDF OCR failed: {e}")
            return "", 0.0

    def _process_image(self, file_path: str) -> Tuple[str, float]:
        """Process an image file with OCR."""
        try:
            img = Image.open(file_path)
            img = self._preprocess_image(img)
            return self._ocr_image(img)
        except Exception as e:
            print(f"Image OCR failed: {e}")
            return "", 0.0

    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy."""
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Convert to grayscale
        img = img.convert("L")

        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # Binarize
        threshold = 128
        img = img.point(lambda x: 255 if x > threshold else 0, '1')
        img = img.convert("L")

        return img

    def _ocr_image(self, img: Image.Image) -> Tuple[str, float]:
        """Run OCR on a preprocessed image."""
        if OCR_ENGINE == "tesserocr":
            return self._ocr_tesserocr(img)
        elif OCR_ENGINE == "pytesseract":
            return self._ocr_pytesseract(img)
        else:
            return "", 0.0

    def _ocr_tesserocr(self, img: Image.Image) -> Tuple[str, float]:
        """OCR using tesserocr (C bindings - faster)."""
        import tesserocr
        tessdata_path = os.environ.get('TESSDATA_PREFIX', '/usr/local/share/tessdata')
        try:
            with tesserocr.PyTessBaseAPI(path=tessdata_path, lang=self.lang, psm=tesserocr.PSM.AUTO) as api:
                api.SetImage(img)
                text = api.GetUTF8Text()
                confidence = api.MeanTextConf()
                return text.strip(), float(confidence)
        except Exception as e:
            print(f"tesserocr failed: {e}")
            # Try without language specification
            try:
                with tesserocr.PyTessBaseAPI(path=tessdata_path, psm=tesserocr.PSM.AUTO) as api:
                    api.SetImage(img)
                    text = api.GetUTF8Text()
                    confidence = api.MeanTextConf()
                    return text.strip(), float(confidence)
            except Exception as e2:
                print(f"tesserocr fallback also failed: {e2}")
                return "", 0.0

    def _ocr_pytesseract(self, img: Image.Image) -> Tuple[str, float]:
        """OCR using pytesseract (subprocess-based)."""
        try:
            import pytesseract
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

            data = pytesseract.image_to_data(
                img, lang=self.lang,
                output_type=pytesseract.Output.DICT,
                config="--psm 6"
            )
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            text = pytesseract.image_to_string(img, lang=self.lang, config="--psm 6")
            return text.strip(), avg_confidence
        except Exception as e:
            print(f"pytesseract failed: {e}")
            return "", 0.0


# Singleton instance
ocr_service = OCRService()
