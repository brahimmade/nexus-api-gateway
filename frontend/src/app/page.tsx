'use client'

import { useAuth } from '@/lib/auth-context'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { Shield, Zap, Users, BarChart3, ArrowRight, Github } from 'lucide-react'
import Link from 'next/link'

export default function HomePage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/dashboard')
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50">
      {/* Header */}
      <header className="relative z-10">
        <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-primary-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">Nexus API Gateway</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/auth/login"
                className="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/auth/register"
                className="btn btn-primary btn-sm"
              >
                Get Started
              </Link>
            </div>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-20 pb-16">
          <div className="text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Modern API Gateway
              <span className="block text-primary-600">Built for Scale</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600 max-w-2xl mx-auto">
              A powerful microservices architecture with authentication, authorization, 
              and real-time monitoring. Built with FastAPI, MongoDB, Kafka, and Next.js.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link
                href="/auth/register"
                className="btn btn-primary btn-lg group"
              >
                Get Started
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/docs"
                className="btn btn-secondary btn-lg"
              >
                View Documentation
              </Link>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Everything you need to build modern APIs
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Comprehensive features for enterprise-grade API management
            </p>
          </div>

          <div className="mt-20 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div className="card p-6 text-center hover:shadow-lg transition-shadow">
              <div className="mx-auto h-12 w-12 rounded-lg bg-primary-100 flex items-center justify-center">
                <Shield className="h-6 w-6 text-primary-600" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">Security First</h3>
              <p className="mt-2 text-sm text-gray-600">
                JWT authentication, role-based access control, and comprehensive authorization
              </p>
            </div>

            <div className="card p-6 text-center hover:shadow-lg transition-shadow">
              <div className="mx-auto h-12 w-12 rounded-lg bg-green-100 flex items-center justify-center">
                <Zap className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">High Performance</h3>
              <p className="mt-2 text-sm text-gray-600">
                FastAPI backend with async processing and optimized database queries
              </p>
            </div>

            <div className="card p-6 text-center hover:shadow-lg transition-shadow">
              <div className="mx-auto h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">User Management</h3>
              <p className="mt-2 text-sm text-gray-600">
                Complete user lifecycle management with roles, permissions, and audit trails
              </p>
            </div>

            <div className="card p-6 text-center hover:shadow-lg transition-shadow">
              <div className="mx-auto h-12 w-12 rounded-lg bg-purple-100 flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">Monitoring</h3>
              <p className="mt-2 text-sm text-gray-600">
                Real-time metrics with Prometheus and beautiful dashboards with Grafana
              </p>
            </div>
          </div>
        </div>

        {/* Tech Stack Section */}
        <div className="bg-gray-50 py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
                Built with Modern Technologies
              </h2>
              <p className="mt-4 text-lg text-gray-600">
                Leveraging the best tools for scalable microservices architecture
              </p>
            </div>

            <div className="mt-16 grid grid-cols-2 gap-8 md:grid-cols-4 lg:grid-cols-6">
              {[
                'FastAPI', 'Next.js', 'MongoDB', 'Kafka', 'Docker', 'Prometheus'
              ].map((tech) => (
                <div key={tech} className="col-span-1 flex justify-center">
                  <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                    <span className="text-sm font-medium text-gray-900">{tech}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Shield className="h-6 w-6 text-primary-600" />
              <span className="ml-2 text-lg font-semibold text-gray-900">Nexus API Gateway</span>
            </div>
            <div className="flex items-center space-x-6">
              <a
                href="#"
                className="text-gray-500 hover:text-gray-900 transition-colors"
              >
                <Github className="h-5 w-5" />
              </a>
            </div>
          </div>
          <div className="mt-8 border-t border-gray-200 pt-8">
            <p className="text-sm text-gray-500 text-center">
              © 2024 Nexus API Gateway. Built with ❤️ for modern microservices.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}