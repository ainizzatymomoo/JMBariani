"""
Invoice Parser for JM Baryani.
Enhanced for Malaysian supplier receipts, dot-matrix fonts, and mixed BM/English.
"""

import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from dateutil import parser as date_parser


class InvoiceParser:
    """Parse raw OCR text into structured invoice data."""

    # Common Malaysian supplier keywords
    SUPPLIER_KEYWORDS = [
        "sdn bhd", "sdn. bhd", "s/b", "enterprise", "ent.",
        "trading", "supply", "supplies", "industries",
        "mart", "wholesale", "pembekal", "kedai", "syarikat",
        "holdings", "resources", "services", "food", "frozen",
        "marketing", "distributor", "agency", "store"
    ]

    # Date patterns (Malaysian formats)
    DATE_PATTERNS = [
        r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}',       # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}',           # YYYY/MM/DD
        r'\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s*\d{2,4}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{2,4}',
    ]

    # Invoice number patterns (more robust)
    INVOICE_PATTERNS = [
        r'(?:invoice|inv)[\s.#:]*(?:no[\s.#:]*)?([A-Z0-9][\w/-]{2,25})',
        r'(?:no|no\.|bil|resit|receipt|rcpt)[\s#:.]+([A-Z0-9][\d][\w/-]{1,25})',
        r'(?:doc|document)[\s#:.]+([A-Z0-9][\w/-]{2,20})',
        r'#\s*([A-Z0-9][\d][\w/-]{1,20})',
    ]

    # RM price patterns (handles various OCR misreads)
    RM_PATTERNS = [
        r'(?:RM|MYR|rm)\s*(\d{1,6}[,.]?\d{0,3}\.?\d{0,2})',  # RM 29.80, RM29.80
        r'(\d{1,6}\.\d{2})\s*(?:RM|MYR|rm)?',                  # 29.80 or 29.80RM
    ]

    # Category keywords
    BASAH_KEYWORDS = [
        "ayam", "chicken", "daging", "beef", "meat", "kambing", "mutton", "lamb",
        "ikan", "fish", "udang", "prawn", "sotong", "squid", "kerang", "kupang",
        "sayur", "vegetable", "bawang", "onion", "tomato", "cili", "chili",
        "santan", "susu", "milk", "cream", "telur", "egg", "tahu", "tofu", "tempe",
        "yogurt", "mentega", "butter", "keju", "cheese", "mayonis", "mayo",
        "lobak", "carrot", "kentang", "potato", "kobis", "cabbage",
        "kangkung", "bayam", "spinach", "salad", "lettuce",
        "limau", "lemon", "lime", "halia", "ginger", "serai", "lemongrass",
        "daun", "leaf", "pandan", "pudina", "mint"
    ]

    KERING_KEYWORDS = [
        "beras", "rice", "basmathi", "basmati", "minyak", "oil", "garam", "salt",
        "gula", "sugar", "tepung", "flour", "rempah", "spice", "kunyit", "turmeric",
        "jintan", "cumin", "kayu manis", "cinnamon", "bunga lawang", "star anise",
        "lada", "pepper", "serbuk", "powder", "kari", "curry",
        "sos", "sauce", "kicap", "soy sauce", "cuka", "vinegar",
        "mi", "noodle", "bihun", "vermicelli", "dal", "lentil",
        "kismis", "raisin", "badam", "almond", "gajus", "cashew",
        "emulco", "flavour", "perisa", "esen", "essence",
        "gelatin", "gelatine", "baking", "yeast",
        "susu pekat", "condensed", "evaporated"
    ]

    # Lines to skip (footer/header noise)
    SKIP_KEYWORDS = [
        'total', 'jumlah', 'subtotal', 'sub total', 'tax', 'cukai',
        'terima kasih', 'thank you', 'invoice', 'receipt',
        'phone', 'tel', 'fax', 'email', 'address', 'alamat',
        'change', 'tender', 'master', 'visa', 'cash', 'card',
        'sst', 'rounding', 'saving', 'member', 'points', 'loyalty',
        'refund', 'exchange', 'voucher', 'please', 'sila',
        'within', 'days', 'purchase', 'packaging',
        'goods sold', 'valid', 'original', 'accepted',
        'qr code', 'e-invoice', 'sign up', 'analysis',
        'no tax', 'printed', 'scan', 'request',
        'jalan', 'kuala lumpur', 'selangor', 'taman', 'lorong',
        'ws:', 'fax:', 'tel:', 'h/p:', 'website', 'www.',
        'payment', 'bayaran', 'baki', 'balance',
        'gst', 'service tax', 'server', 'cashier',
        'table', 'meja', 'cover', 'pax', 'guest'
    ]

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw OCR text into structured invoice data."""
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
            "tax": self._extract_tax(raw_text),
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
        for line in lines[:7]:
            line_lower = line.lower()
            for keyword in self.SUPPLIER_KEYWORDS:
                if keyword in line_lower:
                    # Clean up the line
                    cleaned = re.sub(r'\([\d\w-]+\)', '', line).strip()
                    return cleaned if len(cleaned) > 3 else line.strip()

        # Fallback: first line that looks like a company name (ALL CAPS or Title Case)
        for line in lines[:4]:
            stripped = line.strip()
            if len(stripped) > 4 and not stripped[0].isdigit():
                # Skip if it's clearly a date or number
                if not re.match(r'^[\d/.-]+$', stripped):
                    return stripped

        return None

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice/receipt number."""
        for pattern in self.INVOICE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                # Validate: must contain at least one digit
                if any(c.isdigit() for c in result):
                    return result
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract invoice date."""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                try:
                    parsed = date_parser.parse(date_str, dayfirst=True)
                    # Sanity check: year should be reasonable
                    if 2020 <= parsed.year <= 2030:
                        return parsed.isoformat()
                except (ValueError, OverflowError):
                    return date_str
        return None

    def _extract_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract line items from invoice."""
        items = []

        for line in lines:
            # Skip header/footer lines
            if any(skip in line.lower() for skip in self.SKIP_KEYWORDS):
                continue

            # Skip lines that are just barcodes/numbers
            stripped = line.strip().replace(' ', '').replace('-', '').replace('.', '')
            if stripped.isdigit() and len(stripped) > 8:
                continue

            # Skip very short lines
            if len(line.strip()) < 4:
                continue

            item = self._parse_item_line(line)
            if item:
                # Filter out items with unrealistic prices (> RM5000 for single item)
                if item['total_price'] > 5000:
                    continue
                # Filter out items whose name looks like a barcode
                name_stripped = item['name'].replace(' ', '').replace('.', '').replace('-', '')
                if name_stripped.isdigit() and len(name_stripped) > 6:
                    continue
                # Filter out very short/meaningless names
                if len(item['name'].strip()) < 2:
                    continue
                items.append(item)

        return items

    def _parse_item_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Try to parse a single line as an item entry."""

        # Pattern 1: "ItemName    Qty    UnitPrice    Total"
        # e.g. "Ayam 1kg    5    RM12.00    RM60.00"
        match = re.match(
            r'(.+?)\s+(\d+\.?\d*)\s*(?:kg|pcs|ltr|l|packet|bungkus|kotak|unit|botol|tin|beg|bag|g|ml)?\s+'
            r'(?:RM|rm|MYR)?\s*(\d+\.?\d{2})\s+(?:RM|rm|MYR)?\s*(\d+\.?\d{2})',
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

        # Pattern 2: Receipt format "barcode price@qty total"
        # e.g. "9555755048233 2.40@1 2.40"
        match = re.match(
            r'\d{8,}\s+(\d+\.?\d{2})\s*[@x*]\s*(\d+)\s+(\d+\.?\d{2})',
            line, re.IGNORECASE
        )
        if match:
            unit_price = float(match.group(1))
            qty = float(match.group(2))
            total = float(match.group(3))
            return {
                "name": "(barcode item)",
                "quantity": qty,
                "unit": "unit",
                "unit_price": unit_price,
                "total_price": total,
                "category": "lain"
            }

        # Pattern 3: "qty x price total" or "qty @ price = total"
        match = re.match(
            r'(.+?)\s+(\d+\.?\d*)\s*[x@]\s*(?:RM|rm)?\s*(\d+\.?\d{2})\s*=?\s*(?:RM|rm)?\s*(\d+\.?\d{2})',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1).strip()
            qty = float(match.group(2))
            unit_price = float(match.group(3))
            total = float(match.group(4))
            if len(name) > 2:
                return {
                    "name": name,
                    "quantity": qty,
                    "unit": self._guess_unit(name),
                    "unit_price": unit_price,
                    "total_price": total,
                    "category": self._categorize_item(name)
                }

        # Pattern 4: "ItemName    RM XX.XX" or "ItemName    XX.XX"
        match = re.match(
            r'(.+?)\s+(?:RM|rm|MYR)?\s*(\d+\.?\d{2})\s*$',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1).strip()
            total = float(match.group(2))
            # Validate: name is meaningful, price is reasonable
            if (len(name) > 2 and
                not name.replace('.', '').replace(',', '').replace(' ', '').isdigit() and
                total < 5000 and total > 0.01):
                return {
                    "name": name,
                    "quantity": 1,
                    "unit": self._guess_unit(name),
                    "unit_price": total,
                    "total_price": total,
                    "category": self._categorize_item(name)
                }

        # Pattern 5: "RM XX.XX    ItemName" (price first, common in some receipts)
        match = re.match(
            r'(?:RM|rm|MYR)\s*(\d+\.?\d{2})\s+(.+)',
            line, re.IGNORECASE
        )
        if match:
            total = float(match.group(1))
            name = match.group(2).strip()
            if len(name) > 2 and total < 5000:
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
        patterns = [
            r'(?:grand\s*total|jumlah\s*besar|total\s*keseluruhan)[\s:]*(?:RM|rm|MYR)?\s*(\d+[,.]?\d*\.?\d{0,2})',
            r'(?:total|jumlah)[\s:]*(?:RM|rm|MYR)?\s*(\d+[,.]?\d*\.?\d{0,2})',
            r'(?:RM|rm|MYR)\s*(\d+[,.]?\d*\.?\d{0,2})\s*$',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                amounts = []
                for m in matches:
                    try:
                        amount = float(m.replace(',', ''))
                        if 0.01 < amount < 1000000:  # Sanity range
                            amounts.append(amount)
                    except ValueError:
                        continue
                if amounts:
                    return max(amounts)

        return 0.0

    def _extract_tax(self, text: str) -> float:
        """Extract SST/tax amount."""
        patterns = [
            r'(?:sst|gst|tax|cukai)[\s:]*(?:RM|rm|MYR)?\s*(\d+\.?\d{0,2})',
            r'(?:sst|gst)\s*\d+%[\s:]*(?:RM|rm|MYR)?\s*(\d+\.?\d{0,2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return 0.0

    def _determine_category(self, items: List[Dict], raw_text: str) -> str:
        """Determine overall invoice category based on items."""
        basah_count = 0
        kering_count = 0

        for item in items:
            cat = item.get("category", "lain")
            if cat == "basah":
                basah_count += 1
            elif cat == "kering":
                kering_count += 1

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
        elif any(k in name_lower for k in ["ltr", "liter", "litre", " l ", "1l", "5l"]):
            return "liter"
        elif any(k in name_lower for k in ["ml", "250ml", "500ml"]):
            return "ml"
        elif any(k in name_lower for k in ["g ", "100g", "200g", "500g", "gram"]):
            return "gram"
        elif any(k in name_lower for k in ["pcs", "biji", "ekor", "butir"]):
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
