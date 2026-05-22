"""
Test OCR on real invoices provided in test_invoice/ folder.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('TESSDATA_PREFIX', '/usr/local/share/tessdata')

from app.services.ocr_service import ocr_service
from app.services.invoice_parser import invoice_parser


def test_all_real_invoices():
    """Run OCR + parsing on all real test invoices."""
    test_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'test_invoice')

    files = sorted([
        f for f in os.listdir(test_dir)
        if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.tiff'))
    ])

    if not files:
        print("No test invoice files found!")
        return

    print(f"\nFound {len(files)} test invoices\n")

    results = []

    for filename in files:
        print("=" * 70)
        print(f"  FILE: {filename}")
        print("=" * 70)

        file_path = os.path.join(test_dir, filename)
        ext = filename.rsplit('.', 1)[-1].lower()

        # Run OCR
        raw_text, confidence = ocr_service.extract_text(file_path, ext)

        print(f"\n  OCR Confidence: {confidence:.1f}%")
        print(f"\n  --- RAW OCR TEXT ---")
        # Print first 1500 chars
        display_text = raw_text[:1500] if len(raw_text) > 1500 else raw_text
        for line in display_text.split('\n'):
            print(f"  | {line}")
        if len(raw_text) > 1500:
            print(f"  | ... (truncated, total {len(raw_text)} chars)")
        print(f"  --- END RAW TEXT ---\n")

        # Parse
        result = invoice_parser.parse(raw_text)

        print(f"  PARSED RESULTS:")
        print(f"    Supplier:    {result['supplier_name']}")
        print(f"    Invoice #:   {result['invoice_number']}")
        print(f"    Date:        {result['invoice_date']}")
        print(f"    Category:    {result['category']}")
        print(f"    Total:       RM {result['total']:.2f}")
        print(f"    Items ({len(result['items'])}):")
        for item in result['items']:
            print(f"      - {item['name']:<30} Qty: {item['quantity']:<6} "
                  f"Unit: RM{item['unit_price']:<8.2f} "
                  f"Total: RM{item['total_price']:<8.2f} [{item['category']}]")

        results.append({
            'file': filename,
            'confidence': confidence,
            'supplier': result['supplier_name'],
            'total': result['total'],
            'items_count': len(result['items']),
            'category': result['category']
        })
        print()

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"\n  {'File':<20} {'Confidence':>10} {'Supplier':<25} {'Total':>10} {'Items':>5} {'Cat':<8}")
    print(f"  {'-'*20} {'-'*10} {'-'*25} {'-'*10} {'-'*5} {'-'*8}")
    for r in results:
        supplier = (r['supplier'] or '-')[:25]
        print(f"  {r['file']:<20} {r['confidence']:>8.1f}% {supplier:<25} "
              f"RM{r['total']:>8.2f} {r['items_count']:>5} {r['category']:<8}")

    avg_conf = sum(r['confidence'] for r in results) / len(results) if results else 0
    print(f"\n  Average Confidence: {avg_conf:.1f}%")
    print(f"  Total Invoices Processed: {len(results)}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  JM BARYANI - Real Invoice OCR Test")
    print("=" * 70)
    test_all_real_invoices()
    print("\n  DONE!\n")
