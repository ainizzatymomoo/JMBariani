import React from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { FileText, Package, TrendingUp, LayoutDashboard } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Invoices from './pages/Invoices'
import InvoiceUpload from './pages/InvoiceUpload'
import Inventory from './pages/Inventory'
import Sales from './pages/Sales'

function Sidebar() {
  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
      isActive
        ? 'bg-primary-600 text-white'
        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
    }`

  return (
    <aside className="w-64 bg-brand-dark min-h-screen p-4 fixed left-0 top-0">
      <div className="mb-8 px-4">
        <h1 className="text-2xl font-bold text-white">JM Baryani</h1>
        <p className="text-gray-400 text-sm">HQ Dashboard</p>
      </div>
      <nav className="space-y-2">
        <NavLink to="/" className={linkClass}>
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </NavLink>
        <NavLink to="/invoices" className={linkClass}>
          <FileText size={20} />
          <span>Invoices</span>
        </NavLink>
        <NavLink to="/invoices/upload" className={linkClass}>
          <FileText size={20} />
          <span>Upload Invoice</span>
        </NavLink>
        <NavLink to="/inventory" className={linkClass}>
          <Package size={20} />
          <span>Inventory</span>
        </NavLink>
        <NavLink to="/sales" className={linkClass}>
          <TrendingUp size={20} />
          <span>Sales</span>
        </NavLink>
      </nav>
    </aside>
  )
}

function Layout({ children }) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-64 flex-1 p-8 min-h-screen">
        {children}
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/invoices" element={<Invoices />} />
          <Route path="/invoices/upload" element={<InvoiceUpload />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/sales" element={<Sales />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
