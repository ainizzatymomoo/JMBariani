import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { FileText, Package, TrendingUp, LayoutDashboard, LogOut } from 'lucide-react'
import axios from 'axios'
import Dashboard from './pages/Dashboard'
import Invoices from './pages/Invoices'
import InvoiceUpload from './pages/InvoiceUpload'
import Inventory from './pages/Inventory'
import Sales from './pages/Sales'
import Login from './pages/Login'

const API_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

// --- Axios interceptor: auto-attach token & handle 401 ---
function setupAxiosAuth(token, onUnauthorized) {
  axios.interceptors.request.use(config => {
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  axios.interceptors.response.use(
    response => response,
    error => {
      if (error.response?.status === 401) {
        onUnauthorized()
      }
      return Promise.reject(error)
    }
  )
}

function Sidebar({ onLogout, username }) {
  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
      isActive
        ? 'bg-primary-600 text-white'
        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
    }`

  return (
    <aside className="w-64 bg-brand-dark min-h-screen p-4 fixed left-0 top-0 flex flex-col">
      <div className="mb-8 px-4">
        <h1 className="text-2xl font-bold text-white">JM Baryani</h1>
        <p className="text-gray-400 text-sm">HQ Dashboard</p>
      </div>
      <nav className="space-y-2 flex-1">
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

      {/* User & Logout */}
      <div className="border-t border-gray-700 pt-4 mt-4 px-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-white text-sm font-medium">{username || 'Admin'}</p>
            <p className="text-gray-500 text-xs">Administrator</p>
          </div>
          <button
            onClick={onLogout}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition"
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  )
}

function Layout({ children, onLogout, username }) {
  return (
    <div className="flex">
      <Sidebar onLogout={onLogout} username={username} />
      <main className="ml-64 flex-1 p-8 min-h-screen">
        {children}
      </main>
    </div>
  )
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState('')
  const [checking, setChecking] = useState(true)

  // On mount, check if token exists and is valid
  useEffect(() => {
    const token = localStorage.getItem('jmb_token')
    const savedUser = localStorage.getItem('jmb_user')

    if (token) {
      // Setup axios with existing token
      setupAxiosAuth(token, handleLogout)

      // Verify token is still valid
      axios.post(`${API_URL}/api/auth/verify`)
        .then(() => {
          setIsAuthenticated(true)
          setUsername(savedUser || 'admin')
        })
        .catch(() => {
          // Token expired/invalid
          handleLogout()
        })
        .finally(() => setChecking(false))
    } else {
      setChecking(false)
    }
  }, [])

  function handleLogin(data) {
    localStorage.setItem('jmb_token', data.access_token)
    localStorage.setItem('jmb_user', data.username)
    setupAxiosAuth(data.access_token, handleLogout)
    setIsAuthenticated(true)
    setUsername(data.username)
  }

  function handleLogout() {
    localStorage.removeItem('jmb_token')
    localStorage.removeItem('jmb_user')
    setIsAuthenticated(false)
    setUsername('')
    // Clear axios default headers
    delete axios.defaults.headers.common['Authorization']
  }

  // Loading state while checking auth
  if (checking) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  // Not authenticated - show login
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />
  }

  // Authenticated - show app
  return (
    <BrowserRouter>
      <Layout onLogout={handleLogout} username={username}>
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
