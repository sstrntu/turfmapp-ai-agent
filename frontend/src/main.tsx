import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import App from './App'
import { AuthCallback } from './pages/AuthCallback'
import { AdminPage } from './pages/Admin'
import './global.css'
import { Login } from './pages/Login'
import { Home } from './pages/Home'
import { Landing } from './pages/Landing'

const router = createBrowserRouter(
  [
    { path: '/', element: <Navigate to="/login" replace /> },
    { path: '/landing', element: <Landing /> },
    { path: '/app', element: <App /> },
    { path: '/auth/callback', element: <AuthCallback /> },
    { path: '/admin', element: <AdminPage /> },
    { path: '/login', element: <Login /> },
    { path: '/home', element: <Home /> },
  ],
  {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    },
  },
)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)



