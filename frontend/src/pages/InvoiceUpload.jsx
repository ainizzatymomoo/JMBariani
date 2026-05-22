import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, CheckCircle, AlertCircle, Loader, PenTool, Plus, Trash2, Save } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

export default function InvoiceUpload() {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)

  // Editable form state — always editable after upload
  const [form, setForm] = useState({
    supplier_name: '',
    invoice_number: '',
    invoice_date: '',
    total: '',
    tax: '',
    category: 'lain'
  })
  const [items, setItems] = useState([])

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    setResult(null)
    setError(null)
    setSaved(false)

    try {
      const res = await axios.post(`${API_URL}/api/invoices/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(res.data)

      // Pre-fill form with parsed data (editable immediately)
      const parsed = res.data.parsed_data || {}
      setForm({
        supplier_name: parsed.supplier_name || '',
        invoice_number: parsed.invoice_number || '',
        invoice_date: parsed.invoice_date || '',
        total: parsed.total || '',
        tax: parsed.tax || '',
        category: parsed.category || 'lain'
      })

      // Pre-fill items (or empty row if manual required / no items)
      const parsedItems = (parsed.items || []).map(i => ({
        name: i.name || '',
        quantity: i.quantity || 1,
        unit: i.unit || 'unit',
        unit_price: i.unit_price || 0,
        total_price: i.total_price || 0,
        category: i.category || 'lain'
      }))

      if (parsedItems.length === 0) {
        setItems([emptyItem()])
      } else {
        setItems(parsedItems)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/tiff': ['.tiff']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024
  })

  function emptyItem() {
    return { name: '', quantity: 1, unit: 'kg', unit_price: 0, total_price: 0, category: 'lain' }
  }

  function addItem() {
    setItems([...items, emptyItem()])
  }

  function removeItem(index) {
    setItems(items.filter((_, i) => i !== index))
  }

  function updateItem(index, field, value) {
    const updated = [...items]
    updated[index] = { ...updated[index], [field]: value }
    if (field === 'quantity' || field === 'unit_price') {
      const qty = parseFloat(updated[index].quantity) || 0
      const price = parseFloat(updated[index].unit_price) || 0
      updated[index].total_price = parseFloat((qty * price).toFixed(2))
    }
    setItems(updated)
  }

  // Auto-recalculate grand total from items
  const itemsTotal = items.reduce((sum, i) => sum + (parseFloat(i.total_price) || 0), 0)

  async function handleSave() {
    if (!result) return
    setError(null)
    try {
      const payload = {
        supplier_name: form.supplier_name || null,
        invoice_number: form.invoice_number || null,
        total: parseFloat(form.total) || itemsTotal,
        category: form.category,
        status: 'verified',
        items: items.filter(i => i.name.trim()).map(i => ({
          name: i.name.trim(),
          quantity: parseFloat(i.quantity) || 1,
          unit: i.unit || 'unit',
          unit_price: parseFloat(i.unit_price) || 0,
          total_price: parseFloat(i.total_price) || 0,
          category: i.category || 'lain'
        }))
      }
      await axios.put(`${API_URL}/api/invoices/${result.invoice_id}`, payload)
      setSaved(true)
      setResult({ ...result, status: 'verified' })
    } catch (err) {
      setError(err.response?.data?.detail || 'Save failed')
    }
  }

  const isManualRequired = result?.status === 'manual_required'
  const confidence = result?.ocr_confidence || 0

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Upload Invoice</h1>
      <p className="text-gray-500 mb-6">
        Upload supplier invoice (PDF or image). OCR extracts data into an editable form.
      </p>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div>
            <Loader size={40} className="mx-auto mb-3 text-primary-500 animate-spin" />
            <p className="text-lg font-medium text-gray-700">Processing invoice...</p>
            <p className="text-sm text-gray-500">Running OCR + parsing</p>
          </div>
        ) : (
          <div>
            <Upload size={40} className="mx-auto mb-3 text-gray-400" />
            <p className="text-lg font-medium text-gray-700">
              {isDragActive ? 'Drop invoice here' : 'Drag & drop invoice file'}
            </p>
            <p className="text-sm text-gray-500 mt-1">PDF, JPG, PNG, TIFF (max 10MB)</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-5 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="text-red-500 mt-0.5 flex-shrink-0" size={20} />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Success saved */}
      {saved && (
        <div className="mt-5 bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
          <CheckCircle className="text-green-500 mt-0.5 flex-shrink-0" size={20} />
          <div>
            <p className="font-medium text-green-700">Invoice saved & verified!</p>
            <p className="text-sm text-green-600">You can now process it to inventory from the Invoices page.</p>
          </div>
        </div>
      )}

      {/* Editable Form (always shown after upload) */}
      {result && !saved && (
        <div className="mt-6 bg-white rounded-2xl border shadow-sm p-6">
          {/* Header with confidence badge */}
          <div className="flex justify-between items-center mb-5">
            <div className="flex items-center gap-2">
              {isManualRequired ? (
                <PenTool className="text-orange-500" size={20} />
              ) : (
                <CheckCircle className="text-green-500" size={20} />
              )}
              <h2 className="text-lg font-bold text-gray-800">
                {isManualRequired ? 'Manual Entry Required' : 'Review & Confirm'}
              </h2>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              confidence >= 70 ? 'bg-green-100 text-green-700' :
              confidence >= 50 ? 'bg-yellow-100 text-yellow-700' :
              'bg-red-100 text-red-700'
            }`}>
              OCR: {confidence.toFixed(0)}%
            </span>
          </div>

          {isManualRequired && (
            <p className="text-sm text-orange-600 bg-orange-50 border border-orange-100 rounded-lg p-3 mb-5">
              OCR confidence is below 50%. Please fill in the invoice details manually.
            </p>
          )}

          {/* Invoice Header Fields — ALWAYS EDITABLE */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">Supplier Name</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 mt-1 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                value={form.supplier_name}
                onChange={e => setForm({...form, supplier_name: e.target.value})}
                placeholder="e.g. Ahmad Trading Sdn Bhd"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">Invoice #</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 mt-1 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                value={form.invoice_number}
                onChange={e => setForm({...form, invoice_number: e.target.value})}
                placeholder="e.g. INV-2026-001"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">Date</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 mt-1 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                value={form.invoice_date}
                onChange={e => setForm({...form, invoice_date: e.target.value})}
                placeholder="DD/MM/YYYY"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">Category</label>
              <select
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 mt-1 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                value={form.category}
                onChange={e => setForm({...form, category: e.target.value})}
              >
                <option value="basah">Basah (Wet Goods)</option>
                <option value="kering">Kering (Dry Goods)</option>
                <option value="lain">Lain-lain (Others)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">Tax / SST (RM)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 mt-1 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                value={form.tax}
                onChange={e => setForm({...form, tax: e.target.value})}
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">Grand Total (RM)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 mt-1 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none font-semibold"
                value={form.total || itemsTotal.toFixed(2)}
                onChange={e => setForm({...form, total: e.target.value})}
                placeholder="Auto-calculated from items"
              />
            </div>
          </div>

          {/* Line Items — ALWAYS EDITABLE */}
          <div className="border-t pt-5">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold text-gray-700">Line Items</h3>
              <button
                onClick={addItem}
                className="flex items-center gap-1 text-sm bg-primary-50 text-primary-700 px-3 py-1.5 rounded-lg hover:bg-primary-100 transition"
              >
                <Plus size={16} /> Add Row
              </button>
            </div>

            {/* Table Header */}
            <div className="grid grid-cols-12 gap-2 text-xs font-medium text-gray-500 uppercase mb-2 px-1">
              <div className="col-span-4">Item Name</div>
              <div className="col-span-1">Qty</div>
              <div className="col-span-1">Unit</div>
              <div className="col-span-2">Price/Unit</div>
              <div className="col-span-2">Total</div>
              <div className="col-span-1">Cat</div>
              <div className="col-span-1"></div>
            </div>

            {/* Item Rows */}
            <div className="space-y-2">
              {items.map((item, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center bg-gray-50 p-2 rounded-lg hover:bg-gray-100 transition">
                  <div className="col-span-4">
                    <input
                      className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-400 outline-none"
                      value={item.name}
                      onChange={e => updateItem(i, 'name', e.target.value)}
                      placeholder="Item name"
                    />
                  </div>
                  <div className="col-span-1">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-400 outline-none"
                      value={item.quantity}
                      onChange={e => updateItem(i, 'quantity', e.target.value)}
                    />
                  </div>
                  <div className="col-span-1">
                    <select
                      className="w-full border border-gray-200 rounded px-1 py-1.5 text-xs focus:ring-1 focus:ring-primary-400 outline-none"
                      value={item.unit}
                      onChange={e => updateItem(i, 'unit', e.target.value)}
                    >
                      <option value="kg">kg</option>
                      <option value="gram">g</option>
                      <option value="unit">unit</option>
                      <option value="pcs">pcs</option>
                      <option value="liter">liter</option>
                      <option value="ml">ml</option>
                      <option value="packet">pkt</option>
                      <option value="bottle">btl</option>
                      <option value="box">box</option>
                      <option value="tin">tin</option>
                    </select>
                  </div>
                  <div className="col-span-2">
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">RM</span>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        className="w-full border border-gray-200 rounded pl-8 pr-2 py-1.5 text-sm focus:ring-1 focus:ring-primary-400 outline-none"
                        value={item.unit_price}
                        onChange={e => updateItem(i, 'unit_price', e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="col-span-2">
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">RM</span>
                      <input
                        type="number"
                        step="0.01"
                        className="w-full border border-gray-200 rounded pl-8 pr-2 py-1.5 text-sm bg-gray-100 font-medium outline-none"
                        value={typeof item.total_price === 'number' ? item.total_price.toFixed(2) : item.total_price}
                        readOnly
                      />
                    </div>
                  </div>
                  <div className="col-span-1">
                    <select
                      className="w-full border border-gray-200 rounded px-1 py-1.5 text-xs focus:ring-1 focus:ring-primary-400 outline-none"
                      value={item.category}
                      onChange={e => updateItem(i, 'category', e.target.value)}
                    >
                      <option value="basah">Basah</option>
                      <option value="kering">Kering</option>
                      <option value="lain">Lain</option>
                    </select>
                  </div>
                  <div className="col-span-1 text-center">
                    <button
                      onClick={() => removeItem(i)}
                      className="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50 transition"
                      title="Remove item"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Items Summary */}
            {items.length > 0 && (
              <div className="flex justify-end mt-4 pt-3 border-t">
                <div className="text-right">
                  <p className="text-sm text-gray-500">
                    {items.filter(i => i.name.trim()).length} items
                  </p>
                  <p className="text-lg font-bold text-gray-800">
                    Items Total: RM {itemsTotal.toFixed(2)}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex gap-3 border-t pt-5">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 bg-green-600 text-white px-6 py-2.5 rounded-lg hover:bg-green-700 transition font-medium shadow-sm"
            >
              <Save size={18} />
              Confirm & Save
            </button>
            <button
              onClick={() => { setResult(null); setItems([]); setForm({ supplier_name: '', invoice_number: '', invoice_date: '', total: '', tax: '', category: 'lain' }) }}
              className="bg-gray-100 text-gray-700 px-6 py-2.5 rounded-lg hover:bg-gray-200 transition"
            >
              Upload New
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
