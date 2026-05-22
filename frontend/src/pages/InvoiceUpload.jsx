import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function InvoiceUpload() {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [editMode, setEditMode] = useState(false)
  const [editData, setEditData] = useState({})

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    setResult(null)
    setError(null)

    try {
      const res = await axios.post(`${API_URL}/api/invoices/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(res.data)
      setEditData(res.data.parsed_data || {})
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
    maxSize: 10 * 1024 * 1024 // 10MB
  })

  async function saveCorrections() {
    if (!result) return
    try {
      await axios.put(`${API_URL}/api/invoices/${result.invoice_id}`, {
        supplier_name: editData.supplier_name,
        invoice_number: editData.invoice_number,
        total: parseFloat(editData.total) || 0,
        category: editData.category,
        status: 'verified'
      })
      setEditMode(false)
      setResult({ ...result, status: 'verified' })
    } catch (err) {
      console.error('Save failed:', err)
    }
  }

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

      {/* Result */}
      {result && (
        <div className="mt-6 bg-white rounded-xl border shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="text-green-500" size={20} />
              <h2 className="text-lg font-bold">OCR Result</h2>
            </div>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm ${
                result.ocr_confidence > 70 ? 'bg-green-100 text-green-700' :
                result.ocr_confidence > 40 ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                Confidence: {result.ocr_confidence?.toFixed(1)}%
              </span>
              {!editMode && (
                <button
                  onClick={() => setEditMode(true)}
                  className="text-sm text-primary-600 hover:underline"
                >
                  Edit / Correct
                </button>
              )}
            </div>
          </div>

          <p className="text-sm text-gray-500 mb-4">{result.message}</p>

          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Supplier"
              value={editData.supplier_name}
              editing={editMode}
              onChange={v => setEditData({...editData, supplier_name: v})}
            />
            <Field
              label="Invoice #"
              value={editData.invoice_number}
              editing={editMode}
              onChange={v => setEditData({...editData, invoice_number: v})}
            />
            <Field
              label="Date"
              value={editData.invoice_date}
              editing={editMode}
              onChange={v => setEditData({...editData, invoice_date: v})}
            />
            <Field
              label="Total (RM)"
              value={editData.total}
              editing={editMode}
              onChange={v => setEditData({...editData, total: v})}
            />
            <Field
              label="Category"
              value={editData.category}
              editing={editMode}
              onChange={v => setEditData({...editData, category: v})}
              options={['basah', 'kering', 'lain']}
            />
          </div>

          {/* Items */}
          {editData.items && editData.items.length > 0 && (
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
          )}

          {editMode && (
            <div className="mt-6 flex gap-3">
              <button
                onClick={saveCorrections}
                className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
              >
                Save & Verify
              </button>
              <button
                onClick={() => setEditMode(false)}
                className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Field({ label, value, editing, onChange, options }) {
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
          />
        )
      ) : (
        <p className="font-medium text-gray-800">{value || '-'}</p>
      )}
    </div>
  )
}
