import axios from 'axios'
import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1))
    const accessToken = hash.get('access_token')
    const refreshToken = hash.get('refresh_token')
    const state = hash.get('state')

    async function exchange() {
      if (!accessToken || !state) {
        navigate('/')
        return
      }
      try {
        await axios.post(
          `/api/auth/exchange`,
          { access_token: accessToken, refresh_token: refreshToken, state },
          { withCredentials: true }
        )
      } catch (e) {
        // ignore, fall through to home
      } finally {
        navigate('/')
      }
    }
    void exchange()
  }, [navigate])

  return <p style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>Signing you in…</p>
}


