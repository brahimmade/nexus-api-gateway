'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Cookies from 'js-cookie'
import { apiClient } from './api-client'
import toast from 'react-hot-toast'

interface User {
  id: string
  email: string
  username: string
  full_name: string
  role: string
  permissions: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (userData: RegisterData) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

interface RegisterData {
  email: string
  username: string
  password: string
  full_name: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  const refreshUser = async () => {
    try {
      const token = Cookies.get('access_token')
      if (!token) {
        setIsLoading(false)
        return
      }

      const response = await apiClient.get('/users/me')
      setUser(response.data)
    } catch (error: any) {
      console.error('Failed to refresh user:', error)
      if (error.response?.status === 401) {
        // Token is invalid, clear it
        Cookies.remove('access_token')
        setUser(null)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true)
      const formData = new FormData()
      formData.append('username', email)
      formData.append('password', password)

      const response = await apiClient.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })

      const { access_token, user: userData } = response.data
      
      // Store token in cookie
      Cookies.set('access_token', access_token, {
        expires: 7, // 7 days
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
      })

      setUser(userData)
      toast.success('Login successful!')
      router.push('/dashboard')
    } catch (error: any) {
      console.error('Login failed:', error)
      const message = error.response?.data?.detail || 'Login failed. Please try again.'
      toast.error(message)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (userData: RegisterData) => {
    try {
      setIsLoading(true)
      const response = await apiClient.post('/auth/register', userData)
      
      toast.success('Registration successful! Please log in.')
      router.push('/auth/login')
    } catch (error: any) {
      console.error('Registration failed:', error)
      const message = error.response?.data?.detail || 'Registration failed. Please try again.'
      toast.error(message)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    Cookies.remove('access_token')
    setUser(null)
    toast.success('Logged out successfully')
    router.push('/')
  }

  useEffect(() => {
    refreshUser()
  }, [])

  const value = {
    user,
    isLoading,
    login,
    register,
    logout,
    refreshUser,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}