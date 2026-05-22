import React, { useState, useEffect } from 'react'
import { Package, AlertTriangle, Plus, ArrowUpCircle, ArrowDownCircle, Trash2, RefreshCw } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

const categoryColors = {
  basah: 'bg-blue-100 text-blue-700',
  kering: 'bg-orange-100 text-orange-700',
  lain: 'bg-gray-100 text-gray-600'
}

export default function Inventory() {
  const [items, setItems] = useState([])
  const [summary, setSummary] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [showMovementForm, setShowMovementForm] = useState(null)
  const [filter, setFilter] = useState('all') // all, basah, kering, low

  useEffect(() => {
    fetchAll()
  }, [])

  async function fetchAll() {
    setLoading(true)
    try {
      const [itemsRes, summaryRes, alertsRes] = await Promise.all([
        axios.get(`${API_URL}/api/inventory/items`),
        axios.get(`${API_URL}/api/inventory/summary`),
        axios.get(`${API_URL}/api/inventory/alerts`)
      ])
      setItems(itemsRes.data)
      setSummary(summaryRes.data)
      setAlerts(alertsRes.data)
    } catch (err) {
      console.error('Failed to fetch inventory:', err)
    } finally {
      setLoading(false)
    }
  }

  const filteredItems = items.filter(item => {
    if (filter === 'all') return true
    if (filter === 'low') return item.current_stock <= item.minimum_stock && item.minimum_stock > 0
    return item.category === filter
  })

  if (loading) {
    return <div className="text-center py-20 text-gray-500">Loading inventory...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Inventory</h1>
          <p className="text-gray-500">Track stock levels for basah & kering items</p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 flex items-center gap-2"
        >
          <Plus size={18} /> Add Item
        </button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <SummaryCard label="Total Items" value={summary.total_items} />
          <SummaryCard label="Total Value" value={`RM ${summary.total_value.toLocaleString()}`} />
          <SummaryCard label="Low Stock" value={summary.low_stock_count} highlight={summary.low_stock_count > 0} />
          <SummaryCard label="Basah Items" value={summary.basah_items} />
          <SummaryCard label="Kering Items" value={summary.kering_items} />
        </div>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="text-red-500" size={20} />
            <h3 className="font-bold text-red-700">Reorder Alerts ({alerts.length})</h3>
          </div>
          <div className="space-y-2">
            {alerts.slice(0, 5).map(alert => (
              <div key={alert.id} className="flex justify-between items-center text-sm">
                <span className="text-red-700">
                  <b>{alert.stock_item?.name || `Item #${alert.stock_item_id}`}</b> - 
                  Stock: {alert.current_stock} (min: {alert.minimum_stock})
                </span>
                <span className="text-red-600">
                  Suggest order: {alert.suggested_order_qty} units
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-4">
        {['all', 'basah', 'kering', 'low'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              filter === f
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f === 'low' ? 'Low Stock' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Items Table */}
      {filteredItems.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <Package size={48} className="mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">No inventory items yet.</p>
          <p className="text-sm text-gray-400 mt-1">
            Upload and verify invoices to auto-add stock, or add items manually.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium">Item</th>
                <th className="text-center p-3 font-medium">Category</th>
                <th className="text-right p-3 font-medium">Stock</th>
                <th className="text-right p-3 font-medium">Min Level</th>
                <th className="text-right p-3 font-medium">Days Left</th>
                <th className="text-right p-3 font-medium">Avg Cost</th>
                <th className="text-center p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map(item => {
                const isLow = item.current_stock <= item.minimum_stock && item.minimum_stock > 0
                return (
                  <tr key={item.id} className={`border-t hover:bg-gray-50 ${isLow ? 'bg-red-50' : ''}`}>
                    <td className="p-3">
                      <div>
                        <p className="font-medium text-gray-800">{item.name}</p>
                        {item.description && (
                          <p className="text-xs text-gray-500">{item.description}</p>
                        )}
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${categoryColors[item.category]}`}>
                        {item.category}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <span className={`font-bold ${isLow ? 'text-red-600' : 'text-gray-800'}`}>
                        {item.current_stock.toFixed(1)}
                      </span>
                      <span className="text-gray-500 ml-1">{item.unit}</span>
                    </td>
                    <td className="p-3 text-right text-gray-600">
                      {item.minimum_stock > 0 ? item.minimum_stock.toFixed(1) : '-'}
                    </td>
                    <td className="p-3 text-right">
                      <span className={`${
                        item.days_of_stock < 3 ? 'text-red-600 font-bold' :
                        item.days_of_stock < 7 ? 'text-yellow-600' :
                        'text-green-600'
                      }`}>
                        {item.days_of_stock >= 999 ? '-' : `${item.days_of_stock.toFixed(0)}d`}
                      </span>
                    </td>
                    <td className="p-3 text-right text-gray-600">
                      RM{item.average_unit_cost.toFixed(2)}
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex justify-center gap-1">
                        <button
                          onClick={() => setShowMovementForm({ item, type: 'in' })}
                          className="p-1.5 rounded text-green-600 hover:bg-green-50"
                          title="Stock In"
                        >
                          <ArrowUpCircle size={18} />
                        </button>
                        <button
                          onClick={() => setShowMovementForm({ item, type: 'out' })}
                          className="p-1.5 rounded text-blue-600 hover:bg-blue-50"
                          title="Stock Out"
                        >
                          <ArrowDownCircle size={18} />
                        </button>
                        <button
                          onClick={() => setShowMovementForm({ item, type: 'waste' })}
                          className="p-1.5 rounded text-red-500 hover:bg-red-50"
                          title="Record Waste"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Item Modal */}
      {showAddForm && (
        <AddItemModal
          onClose={() => setShowAddForm(false)}
          onSaved={() => { setShowAddForm(false); fetchAll() }}
        />
      )}

      {/* Movement Modal */}
      {showMovementForm && (
        <MovementModal
          item={showMovementForm.item}
          type={showMovementForm.type}
          onClose={() => setShowMovementForm(null)}
          onSaved={() => { setShowMovementForm(null); fetchAll() }}
        />
      )}
    </div>
  )
}

function SummaryCard({ label, value, highlight }) {
  return (
    <div className={`rounded-xl p-4 border ${highlight ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
      <p className="text-xs text-gray-500 uppercase">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? 'text-red-600' : 'text-gray-800'}`}>{value}</p>
    </div>
  )
}

function AddItemModal({ onClose, onSaved }) {
  const [form, setForm] = useState({
    name: '', category: 'lain', unit: 'kg',
    current_stock: 0, minimum_stock: 0
  })

  async function handleSubmit(e) {
    e.preventDefault()
    try {
      await axios.post(`${API_URL}/api/inventory/items`, form)
      onSaved()
    } catch (err) {
      console.error('Failed to create item:', err)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl">
        <h2 className="text-xl font-bold mb-4">Add Stock Item</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-sm text-gray-600">Item Name</label>
            <input
              className="w-full border rounded px-3 py-2 mt-1"
              value={form.name}
              onChange={e => setForm({...form, name: e.target.value})}
              placeholder="e.g. Beras Basmathi 10kg"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-gray-600">Category</label>
              <select
                className="w-full border rounded px-3 py-2 mt-1"
                value={form.category}
                onChange={e => setForm({...form, category: e.target.value})}
              >
                <option value="basah">Basah</option>
                <option value="kering">Kering</option>
                <option value="lain">Lain</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-600">Unit</label>
              <select
                className="w-full border rounded px-3 py-2 mt-1"
                value={form.unit}
                onChange={e => setForm({...form, unit: e.target.value})}
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
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-gray-600">Current Stock</label>
              <input
                type="number"
                step="0.1"
                className="w-full border rounded px-3 py-2 mt-1"
                value={form.current_stock}
                onChange={e => setForm({...form, current_stock: parseFloat(e.target.value) || 0})}
              />
            </div>
            <div>
              <label className="text-sm text-gray-600">Min Stock (Reorder)</label>
              <input
                type="number"
                step="0.1"
                className="w-full border rounded px-3 py-2 mt-1"
                value={form.minimum_stock}
                onChange={e => setForm({...form, minimum_stock: parseFloat(e.target.value) || 0})}
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="submit" className="flex-1 bg-primary-600 text-white py-2 rounded-lg hover:bg-primary-700">
              Add Item
            </button>
            <button type="button" onClick={onClose} className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function MovementModal({ item, type, onClose, onSaved }) {
  const [quantity, setQuantity] = useState(0)
  const [unitCost, setUnitCost] = useState(item.last_unit_cost || 0)
  const [notes, setNotes] = useState('')

  const titles = { in: 'Stock In', out: 'Stock Out', waste: 'Record Waste' }
  const colors = { in: 'green', out: 'blue', waste: 'red' }

  async function handleSubmit(e) {
    e.preventDefault()
    try {
      await axios.post(`${API_URL}/api/inventory/movements`, {
        stock_item_id: item.id,
        movement_type: type,
        quantity: parseFloat(quantity),
        unit_cost: type === 'in' ? parseFloat(unitCost) : 0,
        notes: notes || null
      })
      onSaved()
    } catch (err) {
      console.error('Movement failed:', err)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <h2 className="text-xl font-bold mb-1">{titles[type]}</h2>
        <p className="text-sm text-gray-500 mb-4">{item.name} (Current: {item.current_stock} {item.unit})</p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-sm text-gray-600">Quantity ({item.unit})</label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              className="w-full border rounded px-3 py-2 mt-1"
              value={quantity}
              onChange={e => setQuantity(e.target.value)}
              required
              autoFocus
            />
          </div>
          {type === 'in' && (
            <div>
              <label className="text-sm text-gray-600">Unit Cost (RM)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-2 mt-1"
                value={unitCost}
                onChange={e => setUnitCost(e.target.value)}
              />
            </div>
          )}
          <div>
            <label className="text-sm text-gray-600">Notes (optional)</label>
            <input
              className="w-full border rounded px-3 py-2 mt-1"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder={type === 'waste' ? 'Reason for waste' : 'Optional notes'}
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              className={`flex-1 bg-${colors[type]}-600 text-white py-2 rounded-lg hover:bg-${colors[type]}-700`}
              style={{ backgroundColor: type === 'in' ? '#16a34a' : type === 'out' ? '#2563eb' : '#dc2626' }}
            >
              Confirm {titles[type]}
            </button>
            <button type="button" onClick={onClose} className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
