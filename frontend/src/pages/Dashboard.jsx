import React, { useState, useEffect } from 'react'
import { FileText, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Dashboard() {
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    parsed: 0,
    verified: 0
  })

  useEffect(() => {
    fetchStats()
  }, [])

  async function fetchStats() {
    try {
      const res = await axios.get(`${API_URL}/api/invoices/`)
      const invoices = res.data
      setStats({
        total: invoices.length,
        pending: invoices.filter(i => i.status === 'pending').length,
        parsed: invoices.filter(i => i.status === 'parsed').length,
        verified: invoices.filter(i => i.status === 'verified').length
      })
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Dashboard</h1>
      <p className="text-gray-500 mb-8">Overview of JM Baryani HQ operations</p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<FileText className="text-blue-500" />}
          label="Total Invoices"
          value={stats.total}
          bg="bg-blue-50"
        />
        <StatCard
          icon={<Clock className="text-yellow-500" />}
          label="Pending Review"
          value={stats.parsed}
          bg="bg-yellow-50"
        />
        <StatCard
          icon={<CheckCircle className="text-green-500" />}
          label="Verified"
          value={stats.verified}
          bg="bg-green-50"
        />
        <StatCard
          icon={<AlertTriangle className="text-red-500" />}
          label="Needs Attention"
          value={stats.pending}
          bg="bg-red-50"
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-lg font-semibold mb-4">Quick Start</h2>
        <div className="space-y-3 text-gray-600">
          <p>1. Upload supplier invoices (PDF/image) via <b>Upload Invoice</b></p>
          <p>2. System will OCR and auto-parse the invoice data</p>
          <p>3. Review and correct parsed data if needed</p>
          <p>4. Verified invoices feed into inventory tracking</p>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, bg }) {
  return (
    <div className={`${bg} rounded-xl p-6 border`}>
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <span className="text-sm text-gray-600">{label}</span>
      </div>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
    </div>
  )
}
