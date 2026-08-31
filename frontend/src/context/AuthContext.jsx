import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { loginUser, registerUser, fetchMe } from '../lib/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const cached = localStorage.getItem('mailtrace_user')
    return cached ? JSON.parse(cached) : null
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('mailtrace_token')
    if (!token) {
      setLoading(false)
      return
    }
    fetchMe()
      .then((data) => {
        setUser(data)
        localStorage.setItem('mailtrace_user', JSON.stringify(data))
      })
      .catch(() => {
        localStorage.removeItem('mailtrace_token')
        localStorage.removeItem('mailtrace_user')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await loginUser({ email, password })
    localStorage.setItem('mailtrace_token', data.access_token)
    localStorage.setItem('mailtrace_user', JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (email, password, fullName) => {
    const data = await registerUser({ email, password, full_name: fullName })
    localStorage.setItem('mailtrace_token', data.access_token)
    localStorage.setItem('mailtrace_user', JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('mailtrace_token')
    localStorage.removeItem('mailtrace_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
