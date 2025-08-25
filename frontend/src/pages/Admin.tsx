import axios from 'axios'
import React, { useCallback, useEffect, useMemo, useState } from 'react'

type PublicUser = {
  id: string
  email: string
  name?: string | null
  avatar_url?: string | null
  last_login_at?: string | null
}

export function AdminPage() {
  const [token, setToken] = useState<string>('')
  const [users, setUsers] = useState<PublicUser[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    const saved = localStorage.getItem('tm_admin_token')
    if (saved) setToken(saved)
  }, [])

  const headers = useMemo(() => ({ 'X-Admin-Token': token || '' }), [token])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await axios.get<PublicUser[]>(`/api/admin/users`, { headers })
      setUsers(res.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  const onSaveToken = () => {
    localStorage.setItem('tm_admin_token', token)
    void refresh()
  }

  const onDelete = async (id: string) => {
    if (!confirm('Delete this user?')) return
    try {
      await axios.delete(`/api/admin/users/${id}`, { headers })
      setUsers((prev) => prev.filter((u) => u.id !== id))
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Delete failed')
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '40px auto', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <h1>Admin</h1>
      <div style={{ marginBottom: 16 }}>
        <input
          placeholder="Admin token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          style={{ padding: 8, width: 320, marginRight: 8 }}
        />
        <button onClick={onSaveToken}>Save token</button>
        <button onClick={() => void refresh()} style={{ marginLeft: 8 }}>Refresh</button>
      </div>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: 'crimson' }}>{error}</p> : null}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Email</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Name</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Last Login</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{u.email}</td>
              <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{u.name || '—'}</td>
              <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>
                {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : '—'}
              </td>
              <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>
                <button onClick={() => void onDelete(u.id)} style={{ color: 'crimson' }}>Delete</button>
              </td>
            </tr>
          ))}
          {users.length === 0 && !loading ? (
            <tr>
              <td colSpan={4} style={{ padding: 16, color: '#666' }}>No users</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  )
}


