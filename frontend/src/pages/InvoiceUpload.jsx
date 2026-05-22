import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertCircle, Loader, PenTool, Plus, Trash2 } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function InvoiceUpload() {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [editMode, setEditMode] = useState(false)
  const [editData, setEditData] = useState({})
  const [manualItems, setManualItems] = useState([])

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    setResult(null)
    setError(null)
    setManualItems([])

    try {
      const res = await axios.post(`${API_URL}/api/invoices/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(res.data)
      setEditData(res.data.parsed_data || {})

      // If manual input required, auto-enable edit mode
      if (res.data.status === 'manual_required') {
        setEditMode(true)
        setManualItems([{ name: '', quantity: 1, unit: 'unit', unit_price: 0, total_price: 0, category: 'lain' }])
      } else {
        setManualItems(res.data.parsed_data?.items || [])
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

  function addItem() {
    setManualItems([...manualItems, { name: '', quantity: 1, unit: 'kg', unit_price: 0, total_price: 0, category: 'lain' }])
  }

  function removeItem(index) {
    setManualItems(manualItems.filter((_, i) => i !== index))
  }

  function updateItem(index, field, value) {
    const updated = [...manualItems]
    updated[index] = { ...updated[index], [field]: value }
    // Auto-calculate total
    if (field === 'quantity' || field === 'unit_price') {
      updated[index].total_price = (parseFloat(updated[index].quantity) || 0) * (parseFloat(updated[index].unit_price) || 0)
    }
    setManualItems(updated)
  }

  async function saveCorrections() {
    if (!result) return
    try {
      const payload = {
        supplier_name: editData.supplier_name,
        invoice_number: editData.invoice_number,
        total: parseFloat(editData.total) || manualItems.reduce((sum, i) => sum + (parseFloat(i.total_price) || 0), 0),
        category: editData.category,
        status: 'verified',
        items: manualItems.filter(i => i.name.trim()).map(i => ({
          name: i.name,
          quantity: parseFloat(i.quantity) || 1,
          unit: i.unit || 'unit',
          unit_price: parseFloat(i.unit_price) || 0,
          total_price: parseFloat(i.total_price) || 0,
          category: i.category || 'lain'
        }))
      }
      await axios.put(`${API_URL}/api/invoices/${result.invoice_id}`, payload)
      setEditMode(false)
      setResult({ ...result, status: 'verified' })
    } catch (err) {
      console.error('Save failed:', err)
    }
  }

  const isManualRequired = result?.status === 'manual_required'

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Upload Invoice</h1>
      <p className="text-gray-500 mb-8">
        Upload supplier invoice (PDF or image). OCR will auto-extract the data.
      </p>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div>
            <Loader size={48} className="mx-auto mb-4 text-primary-500 animate-spin" />
            <p className="text-lg font-medium text-gray-700">Processing invoice...</p>
            <p className="text-sm text-gray-500">Running OCR extraction</p>
          </div>
        ) : (
          <div>
            <Upload size={48} className="mx-auto mb-4 text-gray-400" />
            <p className="text-lg font-medium text-gray-700">
              {isDragActive ? 'Drop invoice here' : 'Drag & drop invoice file'}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Supports: PDF, JPG, PNG, TIFF (max 10MB)
            </p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="text-red-500 mt-0.5" size={20} />
          <div>
            <p className="font-medium text-red-700">Upload Failed</p>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}

      {/* Manual Input Required Alert */}
      {isManualRequired && (
        <div className="mt-6 bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-start gap-3">
          <PenTool className="text-orange-500 mt-0.5" size={20} />
          <div>
            <p className="font-medium text-orange-700">Manual Input Required</p>
            <p className="text-sm text-orange-600">
              OCR confidence is below 60% ({result.ocr_confidence?.toFixed(1)}%). 
              Please enter invoice details manually below.
            </p>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="mt-6 bg-white rounded-xl border shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2">
              {isManualRequired ? (
                <PenTool className="text-orange-500" size={20} />
              ) : (
                <CheckCircle className="text-green-500" size={20} />
              )}
              <h2 className="text-lg font-bold">
                {isManualRequired ? 'Manual Invoice Entry' : 'OCR Result'}
              </h2>
            </div>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm ${
                result.ocr_confidence > 70 ? 'bg-green-100 text-green-700' :
                result.ocr_confidence > 60 ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                Confidence: {result.ocr_confidence?.toFixed(1)}%
              </span>
              {!editMode && !isManualRequired && (
                <button
                  onClick={() => { setEditMode(true); setManualItems(editData.items || []) }}
                  className="text-sm text-primary-600 hover:underline"
                >
                  Edit / Correct
                </button>
              )}
            </div>
          </div>

          <p className="text-sm text-gray-500 mb-4">{result.message}</p>

          {/* Invoice Header Fields */}
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Supplier"
              value={editData.supplier_name}
              editing={editMode || isManualRequired}
              onChange={v => setEditData({...editData, supplier_name: v})}
              placeholder="e.g. Ahmad Trading Sdn Bhd"
            />
            <Field
              label="Invoice #"
              value={editData.invoice_number}
              editing={editMode || isManualRequired}
              onChange={v => setEditData({...editData, invoice_number: v})}
              placeholder="e.g. INV-2024-001"
            />
            <Field
              label="Date"
              value={editData.invoice_date}
              editing={editMode || isManualRequired}
              onChange={v => setEditData({...editData, invoice_date: v})}
              placeholder="DD/MM/YYYY"
            />
            <Field
              label="Total (RM)"
              value={editData.total}
              editing={editMode || isManualRequired}
              onChange={v => setEditData({...editData, total: v})}
              placeholder="0.00"
            />
            <Field
              label="Category"
              value={editData.category || 'lain'}
              editing={editMode || isManualRequired}
              onChange={v => setEditData({...editData, category: v})}
              options={['basah', 'kering', 'lain']}
            />
          </div>

          {/* Items Section */}
          {(editMode || isManualRequired) ? (
            <div className="mt-6">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-medium text-gray-700">Invoice Items</h3>
                <button
                  onClick={addItem}
                  className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
                >
                  <Plus size={16} /> Add Item
                </button>
              </div>
              
              <div className="space-y-3">
                {manualItems.map((item, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-end bg-gray-50 p-3 rounded-lg">
                    <div className="col-span-3">
                      {i === 0 && <label className="text-xs text-gray-500">Item Name</label>}
                      <input
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={item.name}
                        onChange={e => updateItem(i, 'name', e.target.value)}
                        placeholder="e.g. Ayam 1kg"
                      />
                    </div>
                    <div className="col-span-1">
                      {i === 0 && <label className="text-xs text-gray-500">Qty</label>}
                      <input
                        type="number"
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={item.quantity}
                        onChange={e => updateItem(i, 'quantity', e.target.value)}
                      />
                    </div>
                    <div className="col-span-2">
                      {i === 0 && <label className="text-xs text-gray-500">Unit</label>}
                      <select
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={item.unit}
                        onChange={e => updateItem(i, 'unit', e.target.value)}
                      >
                        <option value="kg">kg</option>
                        <option value="unit">unit</option>
                        <option value="pcs">pcs</option>
                        <option value="liter">liter</option>
                        <option value="packet">packet</option>
                        <option value="bottle">bottle</option>
                        <option value="box">box</option>
                        <option value="tin">tin</option>
                      </select>
                    </div>
                    <div className="col-span-2">
                      {i === 0 && <label className="text-xs text-gray-500">Unit Price</label>}
                      <input
                        type="number"
                        step="0.01"
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={item.unit_price}
                        onChange={e => updateItem(i, 'unit_price', e.target.value)}
                      />
                    </div>
                    <div className="col-span-2">
                      {i === 0 && <label className="text-xs text-gray-500">Total</label>}
                      <input
                        type="number"
                        step="0.01"
                        className="w-full border rounded px-2 py-1.5 text-sm bg-gray-100"
                        value={item.total_price?.toFixed?.(2) || item.total_price}
                        readOnly
                      />
                    </div>
                    <div className="col-span-1">
                      {i === 0 && <label className="text-xs text-gray-500">Cat</label>}
                      <select
                        className="w-full border rounded px-2 py-1.5 text-sm"
                        value={item.category}
                        onChange={e => updateItem(i, 'category', e.target.value)}
                      >
                        <option value="basah">Basah</option>
                        <option value="kering">Kering</option>
                        <option value="lain">Lain</option>
                      </select>
                    </div>
                    <div className="col-span-1">
                      <button
                        onClick={() => removeItem(i)}
                        className="text-red-400 hover:text-red-600 p-1"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {manualItems.length > 0 && (
                <div className="mt-3 text-right text-sm text-gray-600">
                  Items Total: <span className="font-bold">
                    RM {manualItems.reduce((sum, i) => sum + (parseFloat(i.total_price) || 0), 0).toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          ) : (
            editData.items && editData.items.length > 0 && (
              <div className="mt-4">
                <h3 className="font-medium text-gray-700 mb-2">Parsed Items</h3>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-2">Item</th>
                      <th className="text-right p-2">Qty</th>
                      <th className="text-right p-2">Unit Price</th>
                      <th className="text-right p-2">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {editData.items.map((item, i) => (
                      <tr key={i} className="border-t">
                        <td className="p-2">{item.name}</td>
                        <td className="text-right p-2">{item.quantity} {item.unit}</td>
                        <td className="text-right p-2">RM{item.unit_price?.toFixed(2)}</td>
                        <td className="text-right p-2 font-medium">RM{item.total_price?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* Save Button */}
          {(editMode || isManualRequired) && (
            <div className="mt-6 flex gap-3">
              <button
                onClick={saveCorrections}
                className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
              >
                Save & Verify
              </button>
              {!isManualRequired && (
                <button
                  onClick={() => setEditMode(false)}
                  className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Field({ label, value, editing, onChange, options, placeholder }) {
  return (
    <div>
      <label className="text-xs text-gray-500 uppercase">{label}</label>
      {editing ? (
        options ? (
          <select
            className="w-full border rounded px-3 py-2 mt-1"
            value={value || ''}
            onChange={e => onChange(e.target.value)}
          >
            {options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : (
          <input
            className="w-full border rounded px-3 py-2 mt-1"
            value={value || ''}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
          />
        )
      ) : (
        <p className="font-medium text-gray-800">{value || '-'}</p>
      )}
    </div>
  )
}
