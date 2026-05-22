"""
Unit tests for Invoice Parser.
Tests parsing logic against sample Malaysian invoice text formats.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.invoice_parser import invoice_parser


def test_parse_basic_invoice():
    """Test parsing a basic Malaysian supplier invoice."""
    raw_text = """
    ABU BAKAR TRADING SDN BHD
    No. 12 Jalan Pasar, Selangor
    Tel: 03-1234 5678

    INVOICE
    No: INV-2024-0156
    Date: 15/01/2024

    Ayam 1kg          10    RM12.00    RM120.00
    Beras Basmathi     5    RM25.00    RM125.00
    Bawang Merah 1kg   3    RM8.50     RM25.50
    Minyak Masak 5L    2    RM28.00    RM56.00
    Garam 1kg          4    RM3.50     RM14.00

    Subtotal: RM340.50
    Total: RM340.50

    Terima Kasih
    """

    result = invoice_parser.parse(raw_text)

    print("=" * 60)
    print("TEST: Basic Malaysian Invoice")
    print("=" * 60)
    print(f"Supplier: {result['supplier_name']}")
    print(f"Invoice #: {result['invoice_number']}")
    print(f"Date: {result['invoice_date']}")
    print(f"Category: {result['category']}")
    print(f"Total: RM{result['total']:.2f}")
    print(f"Items found: {len(result['items'])}")
    for item in result['items']:
        print(f"  - {item['name']} | Qty: {item['quantity']} | "
              f"Price: RM{item['unit_price']:.2f} | Total: RM{item['total_price']:.2f} | "
              f"Cat: {item['category']}")
    print()

    # Assertions
    assert result['supplier_name'] is not None, "Should extract supplier name"
    assert "ABU BAKAR" in result['supplier_name'].upper() or "SDN BHD" in result['supplier_name'].upper()
    assert result['invoice_number'] == "INV-2024-0156", f"Got: {result['invoice_number']}"
    assert result['total'] > 0, "Should extract total"
    assert len(result['items']) > 0, "Should extract items"
    # Category should be mixed (basah items like ayam + kering items like beras)
    assert result['category'] in ('basah', 'kering'), f"Got: {result['category']}"

    print("PASSED!\n")


def test_parse_meat_supplier_invoice():
    """Test parsing a wet goods (basah) invoice."""
    raw_text = """
    HAJI AHMAD ENTERPRISE
    Pembekal Daging & Ayam
    016-7778888

    Resit No: R-0089
    Tarikh: 20-01-2024

    Ayam Segar 1kg      20    RM11.50    RM230.00
    Daging Kambing 1kg   5    RM55.00    RM275.00
    Daging Lembu 1kg     8    RM42.00    RM336.00

    JUMLAH: RM841.00
    """

    result = invoice_parser.parse(raw_text)

    print("=" * 60)
    print("TEST: Meat Supplier (Basah) Invoice")
    print("=" * 60)
    print(f"Supplier: {result['supplier_name']}")
    print(f"Invoice #: {result['invoice_number']}")
    print(f"Date: {result['invoice_date']}")
    print(f"Category: {result['category']}")
    print(f"Total: RM{result['total']:.2f}")
    print(f"Items found: {len(result['items'])}")
    for item in result['items']:
        print(f"  - {item['name']} | Cat: {item['category']}")
    print()

    assert result['supplier_name'] is not None
    assert result['category'] == 'basah', f"Expected 'basah', got: {result['category']}"
    assert result['total'] >= 841.00

    print("PASSED!\n")


def test_parse_dry_goods_invoice():
    """Test parsing a dry goods (kering) invoice."""
    raw_text = """
    SPICE WORLD SUPPLIES
    Wholesale Rempah & Beras
    Lot 5, Kawasan Perindustrian
    No: 03-5556 7890

    Invoice: SW-2024-042
    Date: 22/01/2024

    Beras Basmathi 10kg    10    RM45.00    RM450.00
    Serbuk Kunyit 500g      5    RM8.00     RM40.00
    Jintan Manis 200g       8    RM6.50     RM52.00
    Bunga Lawang 100g       6    RM12.00    RM72.00
    Kayu Manis 200g         4    RM9.00     RM36.00
    Minyak Sapi 1L          3    RM18.00    RM54.00
    Gula Pasir 1kg         10    RM3.80     RM38.00

    Subtotal: RM742.00
    SST 6%: RM44.52
    GRAND TOTAL: RM786.52
    """

    result = invoice_parser.parse(raw_text)

    print("=" * 60)
    print("TEST: Dry Goods (Kering) Invoice")
    print("=" * 60)
    print(f"Supplier: {result['supplier_name']}")
    print(f"Invoice #: {result['invoice_number']}")
    print(f"Date: {result['invoice_date']}")
    print(f"Category: {result['category']}")
    print(f"Total: RM{result['total']:.2f}")
    print(f"Items found: {len(result['items'])}")
    for item in result['items']:
        print(f"  - {item['name']} | Cat: {item['category']}")
    print()

    assert result['supplier_name'] is not None
    assert result['category'] == 'kering', f"Expected 'kering', got: {result['category']}"
    assert result['total'] >= 742.00

    print("PASSED!\n")


def test_parse_minimal_invoice():
    """Test parsing a minimal/poorly formatted invoice."""
    raw_text = """
    Kedai Ali
    5/1/2024

    Ayam RM120.00
    Sayur RM45.00
    Beras RM80.00

    Total RM245.00
    """

    result = invoice_parser.parse(raw_text)

    print("=" * 60)
    print("TEST: Minimal Invoice Format")
    print("=" * 60)
    print(f"Supplier: {result['supplier_name']}")
    print(f"Date: {result['invoice_date']}")
    print(f"Category: {result['category']}")
    print(f"Total: RM{result['total']:.2f}")
    print(f"Items found: {len(result['items'])}")
    for item in result['items']:
        print(f"  - {item['name']} | Total: RM{item['total_price']:.2f}")
    print()

    assert result['supplier_name'] is not None
    assert result['total'] > 0

    print("PASSED!\n")


def test_category_detection():
    """Test item categorization."""
    from app.services.invoice_parser import InvoiceParser
    parser = InvoiceParser()

    # Basah items
    assert parser._categorize_item("Ayam Segar") == "basah"
    assert parser._categorize_item("Daging Kambing") == "basah"
    assert parser._categorize_item("Bawang Merah") == "basah"
    assert parser._categorize_item("Santan") == "basah"
    assert parser._categorize_item("Telur Ayam") == "basah"

    # Kering items
    assert parser._categorize_item("Beras Basmathi") == "kering"
    assert parser._categorize_item("Minyak Masak") == "kering"
    assert parser._categorize_item("Serbuk Kunyit") == "kering"
    assert parser._categorize_item("Garam Halus") == "kering"
    assert parser._categorize_item("Gula Pasir") == "kering"

    print("=" * 60)
    print("TEST: Category Detection")
    print("=" * 60)
    print("All category assertions passed!")
    print("PASSED!\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  JM BARYANI - Invoice Parser Unit Tests")
    print("=" * 60 + "\n")

    test_parse_basic_invoice()
    test_parse_meat_supplier_invoice()
    test_parse_dry_goods_invoice()
    test_parse_minimal_invoice()
    test_category_detection()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED!")
    print("=" * 60 + "\n")
