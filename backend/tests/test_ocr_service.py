"""
Test OCR Service with sample invoice files.
Place test files in /test_invoice/ folder.
This test generates a sample invoice image to test OCR.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PIL import Image, ImageDraw, ImageFont
import tempfile


def create_test_invoice_image(output_path):
    """Create a sample invoice image for OCR testing."""
    # Create image
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)

    # Use default font (no external font file needed)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        font_large = ImageFont.load_default()
        font_normal = ImageFont.load_default()

    # Draw invoice content
    y = 30
    draw.text((250, y), "AHMAD SUPPLIES SDN BHD", fill='black', font=font_large)
    y += 40
    draw.text((250, y), "No 5 Jalan Industri, Shah Alam", fill='gray', font=font_normal)
    y += 25
    draw.text((300, y), "Tel: 03-5510 2233", fill='gray', font=font_normal)
    y += 60

    draw.text((50, y), "INVOICE", fill='black', font=font_large)
    y += 35
    draw.text((50, y), "No: INV-2024-0201", fill='black', font=font_normal)
    y += 25
    draw.text((50, y), "Date: 25/01/2024", fill='black', font=font_normal)
    y += 50

    # Table header
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 10
    draw.text((50, y), "Item", fill='black', font=font_normal)
    draw.text((350, y), "Qty", fill='black', font=font_normal)
    draw.text((450, y), "Price", fill='black', font=font_normal)
    draw.text((600, y), "Total", fill='black', font=font_normal)
    y += 25
    draw.line([(50, y), (750, y)], fill='black', width=1)
    y += 15

    # Items
    items = [
        ("Beras Basmathi 5kg", "10", "RM22.00", "RM220.00"),
        ("Ayam Segar 1kg", "15", "RM12.50", "RM187.50"),
        ("Minyak Masak 5L", "4", "RM28.00", "RM112.00"),
        ("Bawang Merah 1kg", "8", "RM7.50", "RM60.00"),
        ("Garam Halus 1kg", "6", "RM3.20", "RM19.20"),
    ]

    for item_name, qty, price, total in items:
        draw.text((50, y), item_name, fill='black', font=font_normal)
        draw.text((360, y), qty, fill='black', font=font_normal)
        draw.text((450, y), price, fill='black', font=font_normal)
        draw.text((600, y), total, fill='black', font=font_normal)
        y += 30

    # Total
    y += 20
    draw.line([(50, y), (750, y)], fill='black', width=2)
    y += 15
    draw.text((450, y), "TOTAL:", fill='black', font=font_large)
    draw.text((600, y), "RM598.70", fill='black', font=font_large)

    y += 60
    draw.text((250, y), "Terima Kasih / Thank You", fill='gray', font=font_normal)

    # Save
    img.save(output_path)
    print(f"Test invoice image created: {output_path}")
    return output_path


def test_ocr_on_generated_image():
    """Test OCR on a generated invoice image."""
    print("=" * 60)
    print("TEST: OCR on Generated Invoice Image")
    print("=" * 60)

    # Check if any OCR engine is available
    ocr_available = False
    try:
        import tesserocr
        print(f"Tesseract version (tesserocr): {tesserocr.tesseract_version()}")
        ocr_available = True
    except ImportError:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            print(f"Tesseract version (pytesseract): {pytesseract.get_tesseract_version()}")
            ocr_available = True
        except Exception:
            pass

    if not ocr_available:
        print("WARNING: No OCR engine available")
        print("Install tesserocr or tesseract-ocr to run this test")
        return

    from app.services.ocr_service import ocr_service
    from app.services.invoice_parser import invoice_parser

    # Create test image
    test_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'test_invoice')
    os.makedirs(test_dir, exist_ok=True)
    test_image_path = os.path.join(test_dir, 'test_generated_invoice.png')
    create_test_invoice_image(test_image_path)

    # Run OCR
    print("\nRunning OCR...")
    raw_text, confidence = ocr_service.extract_text(test_image_path, 'png')

    print(f"\nOCR Confidence: {confidence:.1f}%")
    print(f"\nRaw OCR Text:")
    print("-" * 40)
    print(raw_text)
    print("-" * 40)

    # Parse
    print("\nParsing extracted text...")
    result = invoice_parser.parse(raw_text)

    print(f"\nParsed Result:")
    print(f"  Supplier: {result['supplier_name']}")
    print(f"  Invoice #: {result['invoice_number']}")
    print(f"  Date: {result['invoice_date']}")
    print(f"  Total: RM{result['total']:.2f}")
    print(f"  Category: {result['category']}")
    print(f"  Items: {len(result['items'])}")
    for item in result['items']:
        print(f"    - {item['name']}: RM{item['total_price']:.2f} [{item['category']}]")

    # Basic validation
    assert raw_text.strip() != "", "OCR should extract some text"
    assert confidence > 0, "Confidence should be > 0"
    print(f"\nOCR extraction successful with {confidence:.1f}% confidence")
    print("PASSED!\n")


def test_ocr_on_existing_files():
    """Test OCR on any files already in test_invoice/ folder."""
    test_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'test_invoice')

    if not os.path.exists(test_dir):
        print("No test_invoice directory found")
        return

    files = [f for f in os.listdir(test_dir)
             if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.tiff'))]

    if not files:
        print("No test invoice files found in test_invoice/")
        print("Add PDF/image files to test_invoice/ folder to test OCR")
        return

    try:
        import tesserocr
    except ImportError:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except Exception:
            print("No OCR engine available - skipping")
            return

    from app.services.ocr_service import ocr_service
    from app.services.invoice_parser import invoice_parser

    for filename in files:
        print(f"\n{'=' * 60}")
        print(f"TEST: OCR on {filename}")
        print("=" * 60)

        file_path = os.path.join(test_dir, filename)
        ext = filename.rsplit('.', 1)[-1].lower()

        raw_text, confidence = ocr_service.extract_text(file_path, ext)
        result = invoice_parser.parse(raw_text)

        print(f"  Confidence: {confidence:.1f}%")
        print(f"  Supplier: {result['supplier_name']}")
        print(f"  Invoice #: {result['invoice_number']}")
        print(f"  Total: RM{result['total']:.2f}")
        print(f"  Category: {result['category']}")
        print(f"  Items: {len(result['items'])}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  JM BARYANI - OCR Service Tests")
    print("=" * 60 + "\n")

    test_ocr_on_generated_image()
    test_ocr_on_existing_files()

    print("\n" + "=" * 60)
    print("  OCR TESTS COMPLETE")
    print("=" * 60 + "\n")
