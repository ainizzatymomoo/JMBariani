# JM Baryani HQ - Business Intelligence System

Integrated business management system for JM Baryani restaurant chain.

## Features (Phase 1 - Invoice OCR)

- Upload supplier invoices (PDF/images)
- Automatic OCR text extraction (Tesseract - free)
- Smart parsing of Malaysian invoice formats
- Auto-categorize items (Basah/Kering/Lain)
- Manual correction and verification workflow
- Supplier management

## Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: React + Vite + TailwindCSS
- **Database**: PostgreSQL
- **OCR**: Tesseract (free, with Malay+English support)
- **Deployment**: Docker Compose

## Quick Start (Localhost)

### Prerequisites
- Docker & Docker Compose installed

### Run

```bash
# Clone the repo
git clone https://github.com/ainizzatymomoo/JMBariani.git
cd JMBariani

# Start all services
docker-compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Development (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
JMBariani/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── models/       # DB models
│   │   ├── routes/       # API endpoints
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # OCR, parsing logic
│   └── requirements.txt
├── frontend/         # React frontend
│   └── src/
│       └── pages/        # Dashboard, Invoices, Upload
├── test_invoice/     # Sample invoices for OCR testing
├── test_report/      # Sample POS reports for testing
├── uploads/          # Uploaded files (gitignored)
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/invoices/upload | Upload invoice for OCR |
| GET | /api/invoices/ | List all invoices |
| GET | /api/invoices/{id} | Get invoice detail |
| PUT | /api/invoices/{id} | Update/correct invoice |
| DELETE | /api/invoices/{id} | Delete invoice |
| GET | /api/invoices/suppliers/ | List suppliers |
| POST | /api/invoices/suppliers/ | Create supplier |

## Roadmap

- [x] Phase 1: Invoice OCR & Tracking
- [ ] Phase 2: Inventory Management
- [ ] Phase 3: Sales Tracker (AcePos integration)
- [ ] Phase 4: Dashboard & Analytics
- [ ] Phase 5: Report Generation
- [ ] Phase 6: Smart Suggestions
