import React, { useState, useEffect } from 'react'
import {
  TrendingUp, TrendingDown, DollarSign, Package, FileText,
  AlertTriangle, CheckCircle, XCircle, Info, ShoppingCart,
  Truck, Users, BarChart3, PieChart, Activity
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const insightIcons = {
  positive: <CheckCircle size={18} className="text-emerald-500" />,
  warning: <AlertTriangle size={18} className="text-amber-500" />,
  danger: <XCircle size={18} className="text-red-500" />,
  info: <Info size={18} className="text-blue-500" />
}

const insightBorders = {
  positive: 'border-l-emerald-500',
  warning: 'border-l-amber-500',
  danger: 'border-l-red-500',
  info: 'border-l-blue-500'
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDashboard()
  }, [])

  async function fetchDashboard() {
    try {
      const res = await axios.get(`${API_URL}/api/dashboard/overview`)
      setData(res.data)
    } catch (err) {
      console.error('Dashboard fetch failed:', err)
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <XCircle size={48} className="mx-auto mb-4 text-red-300" />
        <p className="text-gray-500">{error}</p>
        <button onClick={fetchDashboard} className="mt-4 text-primary-600 hover:underline">Retry</button>
      </div>
    )
  }

  const { kpis, invoices, inventory, sales, insights, top_suppliers } = data || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">JM Baryani HQ — Business Overview</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">Last updated: {new Date().toLocaleTimeString()}</span>
          <button
            onClick={fetchDashboard}
            className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition"
            title="Refresh"
          >
            <Activity size={18} className="text-gray-600" />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <KPICard
          icon={<TrendingUp size={24} />}
          label="Total Revenue"
          value={`RM ${(kpis?.total_revenue || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}`}
          sublabel="From parsed sales reports"
          color="emerald"
        />
        <KPICard
          icon={<ShoppingCart size={24} />}
          label="Total Expenses"
          value={`RM ${(kpis?.total_expenses || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}`}
          sublabel="Verified invoices"
          color="red"
        />
        <KPICard
          icon={<Package size={24} />}
          label="Inventory Value"
          value={`RM ${(kpis?.inventory_value || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}`}
          sublabel={`${inventory?.total_items || 0} items tracked`}
          color="blue"
        />
        <KPICard
          icon={<AlertTriangle size={24} />}
          label="Needs Attention"
          value={kpis?.active_alerts || 0}
          sublabel="Alerts & pending reviews"
          color="amber"
          highlight={kpis?.active_alerts > 0}
        />
      </div>

      {/* Insights Panel */}
      {insights && insights.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={20} className="text-primary-600" />
            <h2 className="text-lg font-bold text-gray-800">Key Insights</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {insights.map((insight, i) => (
              <div
                key={i}
                className={`flex items-start gap-3 p-4 rounded-xl bg-gray-50 border-l-4 ${insightBorders[insight.type]}`}
              >
                <div className="mt-0.5 flex-shrink-0">{insightIcons[insight.type]}</div>
                <div>
                  <p className="font-semibold text-gray-800 text-sm">{insight.title}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{insight.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Grid: 2 columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* LEFT: Sales & Performance (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">

          {/* Outlet Performance Table */}
          {sales?.outlets && sales.outlets.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-800">Outlet Performance</h2>
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">Latest Month</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-gray-500">
                      <th className="text-left py-3 font-medium">Outlet</th>
                      <th className="text-right py-3 font-medium">Sales</th>
                      <th className="text-right py-3 font-medium">Food Cost</th>
                      <th className="text-right py-3 font-medium">Gross Profit</th>
                      <th className="text-right py-3 font-medium">GP (RM)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sales.outlets.map((outlet, i) => (
                      <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="py-3 font-medium text-gray-800">{outlet.outlet}</td>
                        <td className="py-3 text-right">RM {outlet.total_sales?.toLocaleString()}</td>
                        <td className="py-3 text-right">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            outlet.food_cost_pct > 50 ? 'bg-red-100 text-red-700' :
                            outlet.food_cost_pct > 45 ? 'bg-amber-100 text-amber-700' :
                            'bg-emerald-100 text-emerald-700'
                          }`}>
                            {outlet.food_cost_pct?.toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 text-right">
                          <span className={`font-semibold ${
                            outlet.gross_profit_pct > 55 ? 'text-emerald-600' :
                            outlet.gross_profit_pct > 45 ? 'text-gray-700' :
                            'text-red-600'
                          }`}>
                            {outlet.gross_profit_pct?.toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 text-right font-medium text-gray-700">
                          RM {outlet.gross_profit_rm?.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Daily Sales Trend */}
          {sales?.daily_trend && sales.daily_trend.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border p-6">
              <h2 className="text-lg font-bold text-gray-800 mb-4">Daily Sales Trend</h2>
              <div className="flex items-end gap-1 h-40">
                {sales.daily_trend.map((day, i) => {
                  const maxSales = Math.max(...sales.daily_trend.map(d => d.total || 0))
                  const height = maxSales > 0 ? ((day.total || 0) / maxSales) * 100 : 0
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center group relative">
                      <div
                        className="w-full bg-gradient-to-t from-primary-500 to-primary-400 rounded-t-sm hover:from-primary-600 hover:to-primary-500 transition-all cursor-pointer"
                        style={{ height: `${Math.max(height, 2)}%` }}
                        title={`${day.date}: RM${day.total?.toLocaleString()}`}
                      ></div>
                      {i % 5 === 0 && (
                        <span className="text-[9px] text-gray-400 mt-1 transform -rotate-45">{day.date}</span>
                      )}
                    </div>
                  )
                })}
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-400">
                <span>{sales.daily_trend[0]?.date}</span>
                <span>{sales.daily_trend[sales.daily_trend.length - 1]?.date}</span>
              </div>
            </div>
          )}

          {/* Delivery Platform Performance */}
          {sales?.delivery_platforms && sales.delivery_platforms.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border p-6">
              <div className="flex items-center gap-2 mb-4">
                <Truck size={20} className="text-primary-600" />
                <h2 className="text-lg font-bold text-gray-800">Delivery Platforms</h2>
              </div>
              <div className="space-y-3">
                {sales.delivery_platforms
                  .sort((a, b) => b.revenue - a.revenue)
                  .map((platform, i) => {
                    const maxRevenue = Math.max(...sales.delivery_platforms.map(p => p.revenue))
                    const width = maxRevenue > 0 ? (platform.revenue / maxRevenue) * 100 : 0
                    const colors = ['bg-emerald-500', 'bg-blue-500', 'bg-purple-500', 'bg-amber-500', 'bg-rose-500']
                    return (
                      <div key={i} className="flex items-center gap-4">
                        <div className="w-28 text-sm font-medium text-gray-700 flex-shrink-0">
                          {platform.platform}
                        </div>
                        <div className="flex-1">
                          <div className="h-8 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${colors[i % colors.length]} rounded-full flex items-center px-3 transition-all`}
                              style={{ width: `${Math.max(width, 5)}%` }}
                            >
                              <span className="text-white text-xs font-medium whitespace-nowrap">
                                RM {platform.revenue.toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="text-xs text-gray-400 w-16 text-right">
                          {platform.trips > 0 ? `${platform.trips} trips` : ''}
                        </div>
                      </div>
                    )
                  })}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Sidebar (1/3 width) */}
        <div className="space-y-6">

          {/* Invoice Summary */}
          <div className="bg-white rounded-2xl shadow-sm border p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileText size={20} className="text-primary-600" />
              <h2 className="font-bold text-gray-800">Invoices</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <MiniStat label="Total" value={invoices?.total || 0} />
              <MiniStat label="Pending" value={invoices?.pending || 0} highlight={invoices?.pending > 0} />
              <MiniStat label="Verified" value={invoices?.verified || 0} />
              <MiniStat label="Value" value={`RM${((invoices?.total_value || 0) / 1000).toFixed(0)}K`} />
            </div>
            {invoices?.recent && invoices.recent.length > 0 && (
              <div className="border-t pt-3">
                <p className="text-xs text-gray-400 mb-2 uppercase font-medium">Recent</p>
                <div className="space-y-2">
                  {invoices.recent.slice(0, 4).map((inv, i) => (
                    <div key={i} className="flex justify-between items-center text-sm">
                      <span className="text-gray-700 truncate max-w-[140px]">{inv.supplier}</span>
                      <span className="font-medium text-gray-800">RM{inv.total?.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Inventory Health */}
          <div className="bg-white rounded-2xl shadow-sm border p-6">
            <div className="flex items-center gap-2 mb-4">
              <Package size={20} className="text-primary-600" />
              <h2 className="font-bold text-gray-800">Inventory Health</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <MiniStat label="Items" value={inventory?.total_items || 0} />
              <MiniStat label="Low Stock" value={inventory?.low_stock || 0} highlight={inventory?.low_stock > 0} />
              <MiniStat label="Alerts" value={inventory?.alerts || 0} highlight={inventory?.alerts > 0} />
              <MiniStat label="Value" value={`RM${((inventory?.total_value || 0) / 1000).toFixed(0)}K`} />
            </div>
            {inventory?.by_category && inventory.by_category.length > 0 && (
              <div className="border-t pt-3">
                <p className="text-xs text-gray-400 mb-2 uppercase font-medium">By Category</p>
                {inventory.by_category.map((cat, i) => (
                  <div key={i} className="flex justify-between items-center text-sm py-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      cat.category === 'basah' ? 'bg-blue-100 text-blue-700' :
                      cat.category === 'kering' ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>{cat.category}</span>
                    <span className="text-gray-600">{cat.count} items</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top Suppliers */}
          {top_suppliers && top_suppliers.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border p-6">
              <div className="flex items-center gap-2 mb-4">
                <Users size={20} className="text-primary-600" />
                <h2 className="font-bold text-gray-800">Top Suppliers</h2>
              </div>
              <div className="space-y-3">
                {top_suppliers.map((supplier, i) => (
                  <div key={i} className="flex justify-between items-center">
                    <div>
                      <p className="text-sm font-medium text-gray-800 truncate max-w-[160px]">{supplier.name}</p>
                      <p className="text-xs text-gray-400">{supplier.invoice_count} invoices</p>
                    </div>
                    <p className="text-sm font-bold text-gray-700">RM{supplier.total_spend?.toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Start (shown when no data) */}
          {(!sales?.outlets || sales.outlets.length === 0) && (!invoices?.total || invoices.total === 0) && (
            <div className="bg-gradient-to-br from-primary-50 to-orange-50 rounded-2xl border border-primary-100 p-6">
              <h3 className="font-bold text-gray-800 mb-3">Quick Start</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <p>1. Upload invoices di <b>Upload Invoice</b></p>
                <p>2. Verify & process to Inventory</p>
                <p>3. Upload sales reports di <b>Sales</b></p>
                <p>4. Dashboard auto-generate insights!</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Sub Components ---

function KPICard({ icon, label, value, sublabel, color, highlight }) {
  const colorMap = {
    emerald: 'from-emerald-500 to-emerald-600',
    red: 'from-red-500 to-red-600',
    blue: 'from-blue-500 to-blue-600',
    amber: 'from-amber-500 to-amber-600',
  }
  const iconBgMap = {
    emerald: 'bg-emerald-100 text-emerald-600',
    red: 'bg-red-100 text-red-600',
    blue: 'bg-blue-100 text-blue-600',
    amber: 'bg-amber-100 text-amber-600',
  }

  return (
    <div className={`bg-white rounded-2xl shadow-sm border p-5 relative overflow-hidden ${highlight ? 'ring-2 ring-amber-300' : ''}`}>
      <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl ${colorMap[color]} opacity-5 rounded-bl-full`}></div>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          <p className="text-xs text-gray-400 mt-1">{sublabel}</p>
        </div>
        <div className={`p-3 rounded-xl ${iconBgMap[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

function MiniStat({ label, value, highlight }) {
  return (
    <div className={`text-center p-2 rounded-lg ${highlight ? 'bg-red-50' : 'bg-gray-50'}`}>
      <p className={`text-lg font-bold ${highlight ? 'text-red-600' : 'text-gray-800'}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  )
}
