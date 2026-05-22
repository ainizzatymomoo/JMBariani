"""
Invoice Parser for JM Baryani.
Parses raw OCR text into structured invoice data.
Handles Malaysian invoice formats (BM + English mixed).
"""

import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from dateutil import parser as date_parser


class InvoiceParser:
    """Parse raw OCR text into structured invoice data."""

    # Common Malaysian supplier keywords
    SUPPLIER_KEYWORDS = [
        "sdn bhd", "enterprise", "trading", "supply", "supplies",
        "mart", "wholesale", "pembekal", "kedai"
    ]

    # Date patterns (Malaysian formats)
    DATE_PATTERNS = [
        r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',     # DD/MM/YYYY or DD-MM-YYYY
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',         # YYYY/MM/DD
        r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}',
    ]

    # Invoice number patterns
    INVOICE_PATTERNS = [
        r'(?:invoice|inv)[\s.#:]*(?:no[\s.#:]*)?([A-Z0-9][\w-]{2,20})',
        r'(?:no|no\.|bil|resit|receipt)[\s#:]+([A-Z0-9][\w-]{2,20})',
        r'#\s*([A-Z0-9][\w-]{2,20})',
    ]

    # Item line patterns - tries to match: qty unit item_name price
    ITEM_PATTERNS = [
        # qty unit_price total: "2 x 15.00 = 30.00" or "2 @ RM15.00"
        r'(\d+\.?\d*)\s*[x@]\s*(?:RM\s*)?(\d+\.?\d*)\s*[=\s]*(?:RM\s*)?(\d+\.?\d*)',
        # name qty price: "Ayam 5kg RM45.00"
        r'(.+?)\s+(\d+\.?\d*)\s*(?:kg|pcs|ltr|packet|bungkus|kotak|botol|tin)?\s+(?:RM\s*)?(\d+\.?\d*)',
        # simple: item price
        r'(.+?)\s+(?:RM\s*)?(\d+\.?\d{2})\s*$',
    ]

    # Category keywords
    BASAH_KEYWORDS = [
        "ayam", "chicken", "daging", "beef", "meat", "kambing", "mutton", "lamb",
        "ikan", "fish", "udang", "prawn", "sotong", "squid",
        "sayur", "vegetable", "bawang", "onion", "tomato", "cili", "chili",
        "santan", "susu", "milk", "telur", "egg", "tahu", "tofu",
        "yogurt", "mentega", "butter", "keju", "cheese"
    ]

    KERING_KEYWORDS = [
        "beras", "rice", "minyak", "oil", "garam", "salt", "gula", "sugar",
        "tepung", "flour", "rempah", "spice", "kunyit", "turmeric",
        "jintan", "cumin", "kayu manis", "cinnamon", "bunga lawang", "star anise",
        "lada", "pepper", "serbuk", "powder", "kari", "curry",
        "sos", "sauce", "kicap", "soy sauce", "cuka", "vinegar",
        "mi", "noodle", "bihun", "vermicelli", "dal", "lentil",
        "kismis", "raisin", "badam", "almond", "gajus", "cashew"
    ]

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse raw OCR text into structured invoice data.
        Returns dict with: supplier_name, invoice_number, invoice_date, items, total, category
        """
        if not raw_text or not raw_text.strip():
            return self._empty_result()

        lines = raw_text.strip().split('\n')
        lines = [l.strip() for l in lines if l.strip()]

        result = {
            "supplier_name": self._extract_supplier(lines),
            "invoice_number": self._extract_invoice_number(raw_text),
            "invoice_date": self._extract_date(raw_text),
            "items": self._extract_items(lines),
            "subtotal": 0.0,
            "tax": 0.0,
            "total": self._extract_total(raw_text),
            "category": "lain",
            "raw_text": raw_text
        }

        # Calculate subtotal from items if total not found
        if result["items"]:
            items_total = sum(item.get("total_price", 0) for item in result["items"])
            if result["subtotal"] == 0:
                result["subtotal"] = items_total
            if result["total"] == 0:
                result["total"] = items_total

        # Determine category based on items
        result["category"] = self._determine_category(result["items"], raw_text)

        return result

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "supplier_name": None,
            "invoice_number": None,
            "invoice_date": None,
            "items": [],
            "subtotal": 0.0,
            "tax": 0.0,
            "total": 0.0,
            "category": "lain",
            "raw_text": ""
        }

    def _extract_supplier(self, lines: List[str]) -> Optional[str]:
        """Extract supplier name - usually in the first few lines."""
        for line in lines[:5]:
            line_lower = line.lower()
            for keyword in self.SUPPLIER_KEYWORDS:
                if keyword in line_lower:
                    return line.strip()

        # Fallback: first non-empty line that looks like a name
        for line in lines[:3]:
            if len(line) > 3 and not any(c.isdigit() for c in line[:3]):
                return line.strip()

        return None

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice/receipt number."""
        for pattern in self.INVOICE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract invoice date."""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                try:
                    parsed = date_parser.parse(date_str, dayfirst=True)
                    return parsed.isoformat()
                except (ValueError, OverflowError):
                    return date_str
        return None

    def _extract_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract line items from invoice."""
        items = []

        for line in lines:
            # Skip header/footer lines
            if any(skip in line.lower() for skip in [
                'total', 'jumlah', 'subtotal', 'tax', 'cukai',
                'terima kasih', 'thank you', 'invoice', 'receipt',
                'phone', 'tel', 'fax', 'email', 'address'
            ]):
                continue

            item = self._parse_item_line(line)
            if item:
                items.append(item)

        return items

    def _parse_item_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Try to parse a single line as an item entry."""

        # Pattern: "ItemName    Qty    UnitPrice    Total"
        # Common format: "Ayam 1kg    5    RM12.00    RM60.00"
        match = re.match(
            r'(.+?)\s+(\d+\.?\d*)\s*(?:kg|pcs|ltr|packet|bungkus|kotak|unit|botol|tin|beg|bag)?\s+'
            r'(?:RM\s*)?(\d+\.?\d{2})\s+(?:RM\s*)?(\d+\.?\d{2})',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1).strip()
            qty = float(match.group(2))
            unit_price = float(match.group(3))
            total = float(match.group(4))
            return {
                "name": name,
                "quantity": qty,
                "unit": self._guess_unit(name),
                "unit_price": unit_price,
                "total_price": total,
                "category": self._categorize_item(name)
            }

        # Pattern: "ItemName    RM XX.XX"
        match = re.match(
            r'(.+?)\s+(?:RM\s*)?(\d+\.?\d{2})\s*$',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1).strip()
            total = float(match.group(2))
            # Only if name looks valid (not just numbers)
            if len(name) > 2 and not name.replace('.', '').replace(',', '').isdigit():
                return {
                    "name": name,
                    "quantity": 1,
                    "unit": self._guess_unit(name),
                    "unit_price": total,
                    "total_price": total,
                    "category": self._categorize_item(name)
                }

        return None

    def _extract_total(self, text: str) -> float:
        """Extract the total amount from invoice."""
        # Look for total/jumlah patterns
        patterns = [
            r'(?:grand\s*total|jumlah\s*besar|total\s*keseluruhan)[\s:]*(?:RM\s*)?(\d+[,.]?\d*\.?\d{0,2})',
            r'(?:total|jumlah)[\s:]*(?:RM\s*)?(\d+[,.]?\d*\.?\d{0,2})',
            r'(?:RM\s*)(\d+[,.]?\d*\.?\d{0,2})\s*$',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Take the largest number as total (usually the last/biggest)
                amounts = []
                for m in matches:
                    try:
                        amount = float(m.replace(',', ''))
                        amounts.append(amount)
                    except ValueError:
                        continue
                if amounts:
                    return max(amounts)

        return 0.0

    def _determine_category(self, items: List[Dict], raw_text: str) -> str:
        """Determine overall invoice category based on items."""
        basah_count = 0
        kering_count = 0

        # Check items
        for item in items:
            cat = item.get("category", "lain")
            if cat == "basah":
                basah_count += 1
            elif cat == "kering":
                kering_count += 1

        # Also check raw text
        text_lower = raw_text.lower()
        for keyword in self.BASAH_KEYWORDS:
            if keyword in text_lower:
                basah_count += 1
        for keyword in self.KERING_KEYWORDS:
            if keyword in text_lower:
                kering_count += 1

        if basah_count > kering_count:
            return "basah"
        elif kering_count > basah_count:
            return "kering"
        elif basah_count > 0 or kering_count > 0:
            return "basah" if basah_count >= kering_count else "kering"
        return "lain"

    def _categorize_item(self, name: str) -> str:
        """Categorize a single item."""
        name_lower = name.lower()
        for keyword in self.BASAH_KEYWORDS:
            if keyword in name_lower:
                return "basah"
        for keyword in self.KERING_KEYWORDS:
            if keyword in name_lower:
                return "kering"
        return "lain"

    def _guess_unit(self, name: str) -> str:
        """Guess the unit from item name."""
        name_lower = name.lower()
        if any(k in name_lower for k in ["kg", "kilo"]):
            return "kg"
        elif any(k in name_lower for k in ["ltr", "liter", "litre"]):
            return "liter"
        elif any(k in name_lower for k in ["pcs", "biji", "ekor"]):
            return "pcs"
        elif any(k in name_lower for k in ["packet", "pek", "bungkus"]):
            return "packet"
        elif any(k in name_lower for k in ["botol", "bottle"]):
            return "bottle"
        elif any(k in name_lower for k in ["tin", "can"]):
            return "tin"
        elif any(k in name_lower for k in ["kotak", "box"]):
            return "box"
        return "unit"


# Singleton instance
invoice_parser = InvoiceParser()
