import axios from 'axios'
import React, { useEffect, useState } from 'react'

type PublicUser = {
  id: string
  email: string
  name?: string | null
  avatar_url?: string | null
  last_login_at?: string | null
}

export default function App() {
  const [user, setUser] = useState<PublicUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchMe() {
      try {
        const res = await axios.get<PublicUser>(`/api/auth/me`, { withCredentials: true })
        setUser(res.data)
      } catch {
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    fetchMe()
  }, [])

  const onLogin = async () => {
    window.location.href = `/api/auth/login`
  }

  const onLogout = async () => {
    await axios.post(`/api/auth/logout`, {}, { withCredentials: true })
    setUser(null)
  }

  return (
    <div style={{ maxWidth: 560, margin: '80px auto', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <h1>TurfMapp Chatbot</h1>
      {loading ? (
        <p>Loading...</p>
      ) : user ? (
        <div>
          <p>Signed in as {user.email}</p>
          {user.last_login_at ? (
            <p style={{ color: '#666', fontSize: 14 }}>Last login: {new Date(user.last_login_at).toLocaleString()}</p>
          ) : null}
          <button onClick={onLogout}>Logout</button>
        </div>
      ) : (
        <button onClick={onLogin}>Continue with Google</button>
      )}
    </div>
  )
}


