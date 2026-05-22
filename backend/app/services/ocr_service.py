"""
OCR Service for JM Baryani Invoice Processing.
Enhanced pipeline: Google Vision (primary) → Tesseract (fallback).
Improved preprocessing for Malaysian supplier receipts & dot-matrix fonts.
"""

import os
import io
import json
import base64
from typing import Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np

from app.config import settings

# Try Google Vision API
GOOGLE_VISION_AVAILABLE = False
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    pass

# Try tesserocr (C bindings)
TESSEROCR_AVAILABLE = False
try:
    import tesserocr
    TESSEROCR_AVAILABLE = True
except ImportError:
    pass

# Try pytesseract (subprocess)
PYTESSERACT_AVAILABLE = False
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    pass


class OCRService:
    """
    Enhanced OCR service with multi-engine support and
    advanced preprocessing for Malaysian receipts.
    
    Engine priority:
    1. Google Cloud Vision API (if GOOGLE_VISION_API_KEY set)
    2. Tesserocr (C bindings, fast)
    3. Pytesseract (subprocess fallback)
    """

    # Minimum dimensions for OCR (upscale if smaller)
    MIN_WIDTH = 1200
    MIN_HEIGHT = 800

    def __init__(self):
        self.lang = settings.OCR_LANG.split('+')[0]
        self.google_api_key = os.environ.get('GOOGLE_VISION_API_KEY', '') or getattr(settings, 'GOOGLE_VISION_API_KEY', '') or ''
        self.use_google = bool(self.google_api_key) and GOOGLE_VISION_AVAILABLE

        if self.use_google:
            print(f"OCR Engine: Google Vision (primary) + Tesseract (fallback)")
        elif TESSEROCR_AVAILABLE:
            print(f"OCR Engine: tesserocr | Lang: {self.lang}")
        elif PYTESSERACT_AVAILABLE:
            print(f"OCR Engine: pytesseract | Lang: {self.lang}")
        else:
            print("WARNING: No OCR engine available!")

    def extract_text(self, file_path: str, file_type: str) -> Tuple[str, float]:
        """
        Extract text from a file using the best available engine.
        Returns: (extracted_text, confidence_score 0-100)
        """
        file_type = file_type.lower()

        if file_type == "pdf":
            return self._process_pdf(file_path)
        elif file_type in ("jpg", "jpeg", "png", "tiff", "bmp"):
            return self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _process_pdf(self, file_path: str) -> Tuple[str, float]:
        """Process PDF - try text extraction first, fall back to OCR."""
        text = self._extract_pdf_text(file_path)
        if text and len(text.strip()) > 50:
            return text.strip(), 95.0
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
            import fitz
            text_parts = []
            confidences = []

            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                mat = fitz.Matrix(2.5, 2.5)  # Higher zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                page_text, page_conf = self._run_ocr_pipeline(img)
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
        """Process an image file with full OCR pipeline."""
        try:
            img = Image.open(file_path)
            # Fix EXIF rotation
            img = ImageOps.exif_transpose(img)
            return self._run_ocr_pipeline(img)
        except Exception as e:
            print(f"Image OCR failed: {e}")
            return "", 0.0

    def _run_ocr_pipeline(self, img: Image.Image) -> Tuple[str, float]:
        """
        Main OCR pipeline:
        1. Try Google Vision (if available)
        2. Fallback to Tesseract with enhanced preprocessing
        """
        # Try Google Vision first (better for receipts)
        if self.use_google:
            text, conf = self._ocr_google_vision(img)
            if conf > 50:
                return text, conf
            print(f"Google Vision low confidence ({conf:.0f}%), trying Tesseract...")

        # Preprocess for Tesseract
        processed_img = self._preprocess_for_receipts(img)
        return self._ocr_tesseract(processed_img)

    # =============================================
    # PREPROCESSING - Enhanced for Malaysian Receipts
    # =============================================

    def _preprocess_for_receipts(self, img: Image.Image) -> Image.Image:
        """
        Advanced preprocessing pipeline optimized for:
        - Phone camera photos of receipts
        - Dot-matrix printed invoices
        - Thermal paper receipts
        - Low-light / blurry scans
        """
        # 1. Convert to RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 2. Upscale if too small (critical for dot-matrix fonts)
        img = self._upscale_if_needed(img)

        # 3. Auto-rotate/deskew
        img = self._deskew(img)

        # 4. Convert to grayscale
        img = img.convert("L")

        # 5. Denoise (remove scan artifacts)
        img = self._denoise(img)

        # 6. Increase contrast (adaptive)
        img = self._adaptive_contrast(img)

        # 7. Sharpen
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(ImageFilter.SHARPEN)  # Double sharpen for dot-matrix

        # 8. Adaptive binarization (better than fixed threshold)
        img = self._adaptive_threshold(img)

        return img

    def _upscale_if_needed(self, img: Image.Image) -> Image.Image:
        """Upscale low-resolution images for better OCR."""
        w, h = img.size
        if w < self.MIN_WIDTH or h < self.MIN_HEIGHT:
            scale = max(self.MIN_WIDTH / w, self.MIN_HEIGHT / h, 2.0)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        return img

    def _deskew(self, img: Image.Image) -> Image.Image:
        """Auto-rotate/deskew crooked scans using numpy."""
        try:
            # Convert to numpy for angle detection
            img_array = np.array(img.convert("L"))

            # Find edges
            edges = np.abs(np.diff(img_array.astype(float), axis=1))

            # Simple deskew: find dominant angle from edge distribution
            # Use horizontal projection to detect skew
            row_sums = np.sum(edges > 30, axis=1)
            if np.max(row_sums) < 10:
                return img  # No significant edges, skip deskew

            # Try small rotation angles (-5 to +5 degrees)
            best_angle = 0
            best_score = 0

            for angle in np.arange(-5, 5.5, 0.5):
                if angle == 0:
                    continue
                rotated = img.rotate(angle, expand=False, fillcolor=(255, 255, 255) if img.mode == "RGB" else 255)
                rot_array = np.array(rotated.convert("L"))
                # Score: variance of row sums (higher = more aligned text)
                row_var = np.var(np.sum(rot_array < 128, axis=1))
                if row_var > best_score:
                    best_score = row_var
                    best_angle = angle

            # Only apply if significant skew detected
            if abs(best_angle) > 0.5:
                fill = (255, 255, 255) if img.mode == "RGB" else 255
                img = img.rotate(best_angle, expand=True, fillcolor=fill)

            return img
        except Exception:
            return img  # Skip deskew on error

    def _denoise(self, img: Image.Image) -> Image.Image:
        """Remove noise and scan artifacts."""
        # Median filter removes salt-and-pepper noise (common in scans)
        img = img.filter(ImageFilter.MedianFilter(size=3))
        return img

    def _adaptive_contrast(self, img: Image.Image) -> Image.Image:
        """Apply adaptive contrast enhancement."""
        # Auto-contrast normalizes the histogram
        img = ImageOps.autocontrast(img, cutoff=2)

        # Additional contrast boost
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)

        # Brightness adjustment if too dark
        stat = img.getextrema()
        if stat[1] < 200:  # Image is too dark
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.3)

        return img

    def _adaptive_threshold(self, img: Image.Image) -> Image.Image:
        """
        Adaptive binarization - better than fixed threshold
        for receipts with uneven lighting.
        """
        try:
            img_array = np.array(img)

            # Use local mean thresholding
            # For each pixel, threshold = mean of surrounding block
            block_size = 31
            h, w = img_array.shape

            # Pad image
            pad = block_size // 2
            padded = np.pad(img_array, pad, mode='edge')

            # Calculate local mean using cumulative sum (fast)
            integral = padded.cumsum(axis=0).cumsum(axis=1)

            # Calculate block sums
            y1, x1 = 0, 0
            y2, x2 = block_size, block_size
            block_sum = (
                integral[y2:y2+h, x2:x2+w] -
                integral[y1:y1+h, x2:x2+w] -
                integral[y2:y2+h, x1:x1+w] +
                integral[y1:y1+h, x1:x1+w]
            )
            local_mean = block_sum / (block_size * block_size)

            # Apply threshold with offset (C parameter)
            C = 10  # Offset to avoid noise
            binary = ((img_array > (local_mean - C)) * 255).astype(np.uint8)

            return Image.fromarray(binary, mode="L")
        except Exception:
            # Fallback to Otsu-like fixed threshold
            img_array = np.array(img)
            threshold = np.mean(img_array)
            binary = ((img_array > threshold) * 255).astype(np.uint8)
            return Image.fromarray(binary, mode="L")

    # =============================================
    # OCR ENGINES
    # =============================================

    def _ocr_google_vision(self, img: Image.Image) -> Tuple[str, float]:
        """OCR using Google Cloud Vision API (best for receipts)."""
        try:
            import requests

            # Convert image to base64
            buffer = io.BytesIO()
            img_rgb = img.convert("RGB") if img.mode != "RGB" else img
            img_rgb.save(buffer, format="JPEG", quality=95)
            image_content = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Call Google Vision API
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.google_api_key}"
            payload = {
                "requests": [{
                    "image": {"content": image_content},
                    "features": [{"type": "TEXT_DETECTION", "maxResults": 1}],
                    "imageContext": {
                        "languageHints": ["en", "ms"]
                    }
                }]
            }

            response = requests.post(url, json=payload, timeout=30)
            if response.status_code != 200:
                print(f"Google Vision API error: {response.status_code}")
                return "", 0.0

            result = response.json()
            annotations = result.get("responses", [{}])[0].get("textAnnotations", [])

            if annotations:
                full_text = annotations[0].get("description", "")
                # Google Vision doesn't return confidence per se, but it's very reliable
                # Estimate confidence based on text quality
                confidence = 85.0 if len(full_text.strip()) > 20 else 50.0
                return full_text.strip(), confidence

            return "", 0.0
        except Exception as e:
            print(f"Google Vision OCR failed: {e}")
            return "", 0.0

    def _ocr_tesseract(self, img: Image.Image) -> Tuple[str, float]:
        """Run Tesseract OCR with optimized config for receipts."""
        if TESSEROCR_AVAILABLE:
            return self._ocr_tesserocr(img)
        elif PYTESSERACT_AVAILABLE:
            return self._ocr_pytesseract(img)
        return "", 0.0

    def _ocr_tesserocr(self, img: Image.Image) -> Tuple[str, float]:
        """OCR using tesserocr with receipt-optimized settings."""
        tessdata_path = os.environ.get('TESSDATA_PREFIX', '/usr/local/share/tessdata')

        # Try multiple PSM modes and pick best result
        best_text = ""
        best_conf = 0.0

        # PSM 6: Assume uniform block of text (good for receipts)
        # PSM 4: Assume single column of text of variable sizes
        psm_modes = [tesserocr.PSM.SINGLE_BLOCK, tesserocr.PSM.SINGLE_COLUMN]

        for psm in psm_modes:
            try:
                with tesserocr.PyTessBaseAPI(
                    path=tessdata_path,
                    lang=self.lang,
                    psm=psm,
                    oem=tesserocr.OEM.LSTM_AND_TESSERACT  # OEM 3: LSTM + legacy
                ) as api:
                    # Set receipt-friendly config
                    api.SetVariable("tessedit_char_whitelist",
                                    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                                    ".,:-/()@#%&*+= RMrm$")
                    api.SetVariable("preserve_interword_spaces", "1")

                    api.SetImage(img)
                    text = api.GetUTF8Text()
                    confidence = api.MeanTextConf()

                    if confidence > best_conf:
                        best_text = text.strip()
                        best_conf = float(confidence)
            except Exception as e:
                print(f"tesserocr PSM {psm} failed: {e}")
                continue

        # If both PSM modes failed, try without lang
        if best_conf == 0:
            try:
                with tesserocr.PyTessBaseAPI(path=tessdata_path, psm=tesserocr.PSM.AUTO) as api:
                    api.SetImage(img)
                    best_text = api.GetUTF8Text().strip()
                    best_conf = float(api.MeanTextConf())
            except Exception as e:
                print(f"tesserocr fallback failed: {e}")

        return best_text, best_conf

    def _ocr_pytesseract(self, img: Image.Image) -> Tuple[str, float]:
        """OCR using pytesseract with optimized config."""
        try:
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

            # Receipt-optimized config
            config = (
                "--psm 6 "  # Assume uniform block of text
                "--oem 3 "  # LSTM + legacy engine
                "-c tessedit_char_whitelist="
                "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/()@#%&*+= RMrm$"
                " -c preserve_interword_spaces=1"
            )

            data = pytesseract.image_to_data(
                img, lang=self.lang,
                output_type=pytesseract.Output.DICT,
                config=config
            )
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            text = pytesseract.image_to_string(img, lang=self.lang, config=config)
            return text.strip(), avg_confidence
        except Exception as e:
            print(f"pytesseract failed: {e}")
            return "", 0.0


# Singleton instance
ocr_service = OCRService()
