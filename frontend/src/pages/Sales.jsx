import React, { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { TrendingUp, Upload, FileText, AlertTriangle, CheckCircle, Info, XCircle, Trash2, Loader, BarChart3 } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const insightIcons = {
  positive: <CheckCircle size={18} className="text-green-500" />,
  warning: <AlertTriangle size={18} className="text-yellow-500" />,
  danger: <XCircle size={18} className="text-red-500" />,
  info: <Info size={18} className="text-blue-500" />
}

const insightBg = {
  positive: 'bg-green-50 border-green-200',
  warning: 'bg-yellow-50 border-yellow-200',
  danger: 'bg-red-50 border-red-200',
  info: 'bg-blue-50 border-blue-200'
}

const reportTypeLabels = {
  fc_gp: 'Food Cost & GP',
  fc_gp_ytd: 'FC & GP (YTD)',
  daily_sales: 'Daily Sales',
  ytd_sales: 'YTD Sales Performance',
  delivery_partner: 'Delivery Partner',
  delivery_detail: 'Delivery Detail',
  unknown: 'Unknown'
}

export default function Sales() {
  const [reports, setReports] = useState([])
  const [insights, setInsights] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('insights')

  useEffect(() => {
    fetchAll()
  }, [])

  async function fetchAll() {
    setLoading(true)
    try {
      const [reportsRes, insightsRes] = await Promise.all([
        axios.get(`${API_URL}/api/sales/reports`),
        axios.get(`${API_URL}/api/sales/insights`)
      ])
      setReports(reportsRes.data)
      setInsights(insightsRes.data)
    } catch (err) {
      console.error('Failed to fetch sales data:', err)
    } finally {
      setLoading(false)
    }
  }

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return
    const file = acceptedFiles[0]
    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    setUploadResult(null)

    try {
      const res = await axios.post(`${API_URL}/api/sales/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setUploadResult(res.data)
      fetchAll()
    } catch (err) {
      setUploadResult({ error: err.response?.data?.detail || 'Upload failed' })
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024
  })

  async function parseTestReports() {
    setUploading(true)
    try {
      const res = await axios.post(`${API_URL}/api/sales/parse-test`)
      setUploadResult({ message: res.data.message, insights: res.data.results.flatMap(r => r.insights || []) })
      fetchAll()
    } catch (err) {
      setUploadResult({ error: err.response?.data?.detail || 'Failed to parse test reports' })
    } finally {
      setUploading(false)
    }
  }

  async function deleteReport(id) {
    if (!confirm('Delete this report?')) return
    try {
      await axios.delete(`${API_URL}/api/sales/reports/${id}`)
      fetchAll()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  if (loading) {
    return <div className="text-center py-20 text-gray-500">Loading sales data...</div>
  }

  const allInsights = insights?.insights || []

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Sales & Reports</h1>
          <p className="text-gray-500">Upload POS reports for analysis and insights</p>
        </div>
        <button
          onClick={parseTestReports}
          className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 text-sm"
          disabled={uploading}
        >
          <BarChart3 size={16} className="inline mr-1" />
          Parse Test Reports
        </button>
      </div>

      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition mb-6 ${
          isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div>
            <Loader size={36} className="mx-auto mb-3 text-primary-500 animate-spin" />
            <p className="text-gray-700">Processing report...</p>
          </div>
        ) : (
          <div>
            <Upload size={36} className="mx-auto mb-3 text-gray-400" />
            <p className="text-gray-700 font-medium">Drop sales report PDF here</p>
            <p className="text-sm text-gray-500 mt-1">Supports: FC&GP, Daily Sales, Delivery, YTD reports</p>
          </div>
        )}
      </div>

      {/* Upload Result */}
      {uploadResult && (
        <div className={`mb-6 rounded-xl border p-4 ${uploadResult.error ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
          {uploadResult.error ? (
            <p className="text-red-700"><XCircle size={16} className="inline mr-1" />{uploadResult.error}</p>
          ) : (
            <div>
              <p className="font-medium text-green-700 mb-2">
                <CheckCircle size={16} className="inline mr-1" />
                {uploadResult.message}
              </p>
              {uploadResult.report_type && (
                <p className="text-sm text-green-600">Type: {reportTypeLabels[uploadResult.report_type] || uploadResult.report_type}</p>
              )}
              {uploadResult.insights?.length > 0 && (
                <div className="mt-3 space-y-2">
                  {uploadResult.insights.map((ins, i) => (
                    <div key={i} className={`flex items-start gap-2 p-2 rounded-lg border ${insightBg[ins.type]}`}>
                      {insightIcons[ins.type]}
                      <div>
                        <p className="text-sm font-medium">{ins.title}</p>
                        <p className="text-xs text-gray-600">{ins.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { key: 'insights', label: `Insights (${allInsights.length})` },
          { key: 'reports', label: `Reports (${reports.length})` }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === tab.key ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <div>
          {allInsights.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-xl border">
              <TrendingUp size={48} className="mx-auto mb-4 text-gray-300" />
              <p className="text-gray-500">No insights yet. Upload sales reports to generate insights.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {allInsights.map((ins, i) => (
                <div key={i} className={`p-4 rounded-xl border ${insightBg[ins.type]}`}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{insightIcons[ins.type]}</div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-800">{ins.title}</h4>
                      <p className="text-sm text-gray-600 mt-1">{ins.message}</p>
                      {ins.source && (
                        <p className="text-xs text-gray-400 mt-2">Source: {ins.source}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reports Tab */}
      {activeTab === 'reports' && (
        <div>
          {reports.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-xl border">
              <FileText size={48} className="mx-auto mb-4 text-gray-300" />
              <p className="text-gray-500">No reports uploaded yet.</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3 font-medium">Filename</th>
                    <th className="text-left p-3 font-medium">Type</th>
                    <th className="text-left p-3 font-medium">Status</th>
                    <th className="text-left p-3 font-medium">Uploaded</th>
                    <th className="text-center p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map(r => (
                    <tr key={r.id} className="border-t hover:bg-gray-50">
                      <td className="p-3 font-medium text-gray-800">{r.filename}</td>
                      <td className="p-3">
                        <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs">
                          {reportTypeLabels[r.report_type] || r.report_type}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-1 bg-green-50 text-green-700 rounded-full text-xs">
                          {r.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-500">
                        {r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td className="p-3 text-center">
                        <button
                          onClick={() => deleteReport(r.id)}
                          className="text-red-400 hover:text-red-600 p-1"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
