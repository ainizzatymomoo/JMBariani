import React, { useState, useEffect } from 'react'
import { FileText, Eye, Trash2, CheckCircle, Clock, AlertCircle, Package } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

const statusColors = {
  pending: 'bg-gray-100 text-gray-700',
  parsed: 'bg-yellow-100 text-yellow-700',
  manual_required: 'bg-orange-100 text-orange-700',
  verified: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700'
}

const categoryColors = {
  basah: 'bg-blue-100 text-blue-700',
  kering: 'bg-orange-100 text-orange-700',
  lain: 'bg-gray-100 text-gray-600'
}

export default function Invoices() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedInvoice, setSelectedInvoice] = useState(null)

  useEffect(() => {
    fetchInvoices()
  }, [])

  async function fetchInvoices() {
    try {
      const res = await axios.get(`${API_URL}/api/invoices/`)
      setInvoices(res.data)
    } catch (err) {
      console.error('Failed to fetch invoices:', err)
    } finally {
      setLoading(false)
    }
  }

  async function deleteInvoice(id) {
    if (!confirm('Delete this invoice?')) return
    try {
      await axios.delete(`${API_URL}/api/invoices/${id}`)
      setInvoices(invoices.filter(i => i.id !== id))
      if (selectedInvoice?.id === id) setSelectedInvoice(null)
    } catch (err) {
      console.error('Failed to delete:', err)
    }
  }

  async function verifyInvoice(id) {
    try {
      await axios.put(`${API_URL}/api/invoices/${id}`, { status: 'verified' })
      fetchInvoices()
      if (selectedInvoice?.id === id) {
        setSelectedInvoice({ ...selectedInvoice, status: 'verified' })
      }
    } catch (err) {
      console.error('Failed to verify:', err)
    }
  }

  async function processToInventory(id) {
    try {
      const res = await axios.post(`${API_URL}/api/inventory/process-invoice/${id}`)
      alert(res.data.message)
      fetchInvoices()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to process to inventory')
    }
  }

  if (loading) {
    return <div className="text-center py-20 text-gray-500">Loading...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Invoices</h1>
          <p className="text-gray-500">Manage supplier invoices</p>
        </div>
        <a
          href="/invoices/upload"
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition"
        >
          + Upload Invoice
        </a>
      </div>

      {invoices.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border">
          <FileText size={48} className="mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">No invoices yet. Upload your first invoice!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Invoice List */}
          <div className="lg:col-span-2 space-y-3">
            {invoices.map(inv => (
              <div
                key={inv.id}
                className={`bg-white rounded-lg border p-4 cursor-pointer hover:shadow-md transition ${
                  selectedInvoice?.id === inv.id ? 'ring-2 ring-primary-500' : ''
                }`}
                onClick={() => setSelectedInvoice(inv)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-gray-800">
                      {inv.supplier?.name || inv.original_filename || `Invoice #${inv.id}`}
                    </p>
                    <p className="text-sm text-gray-500">
                      {inv.invoice_number && `#${inv.invoice_number} | `}
                      {inv.original_filename}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[inv.status]}`}>
                      {inv.status}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${categoryColors[inv.category]}`}>
                      {inv.category}
                    </span>
                  </div>
                </div>
                <div className="flex justify-between mt-2 text-sm">
                  <span className="text-gray-500">
                    Confidence: {inv.ocr_confidence?.toFixed(1)}%
                  </span>
                  <span className="font-semibold text-gray-700">
                    RM {inv.total?.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-1">
            {selectedInvoice ? (
              <div className="bg-white rounded-xl border p-6 sticky top-8">
                <h3 className="font-bold text-lg mb-4">Invoice Detail</h3>
                <div className="space-y-3 text-sm">
                  <div>
                    <span className="text-gray-500">Supplier:</span>
                    <p className="font-medium">{selectedInvoice.supplier?.name || '-'}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Invoice #:</span>
                    <p className="font-medium">{selectedInvoice.invoice_number || '-'}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Total:</span>
                    <p className="font-bold text-xl">RM {selectedInvoice.total?.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Items:</span>
                    {selectedInvoice.items?.length > 0 ? (
                      <ul className="mt-1 space-y-1">
                        {selectedInvoice.items.map((item, i) => (
                          <li key={i} className="flex justify-between">
                            <span>{item.name}</span>
                            <span className="text-gray-600">RM{item.total_price?.toFixed(2)}</span>
                          </li>
                        ))}
                      </ul>
                    ) : <p>No items parsed</p>}
                  </div>
                </div>
                <div className="flex flex-col gap-2 mt-6">
                  {selectedInvoice.status !== 'verified' && (
                    <button
                      onClick={() => verifyInvoice(selectedInvoice.id)}
                      className="w-full bg-green-500 text-white py-2 rounded-lg text-sm hover:bg-green-600"
                    >
                      <CheckCircle size={14} className="inline mr-1" /> Verify
                    </button>
                  )}
                  {selectedInvoice.status === 'verified' && selectedInvoice.items?.length > 0 && (
                    <button
                      onClick={() => processToInventory(selectedInvoice.id)}
                      className="w-full bg-primary-600 text-white py-2 rounded-lg text-sm hover:bg-primary-700"
                    >
                      <Package size={14} className="inline mr-1" /> Process to Inventory
                    </button>
                  )}
                  <button
                    onClick={() => deleteInvoice(selectedInvoice.id)}
                    className="w-full bg-red-50 text-red-600 py-2 rounded-lg text-sm hover:bg-red-100"
                  >
                    <Trash2 size={14} className="inline mr-1" /> Delete
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl border p-6 text-center text-gray-400">
                <Eye size={32} className="mx-auto mb-2" />
                <p>Select an invoice to view details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
