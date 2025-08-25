import React from 'react'
import { MDBIcon } from 'mdb-react-ui-kit'

export function Login() {
  const onGoogle = () => {
    window.location.href = `/api/auth/login`
  }

  return (
    <div style={{ 
      minHeight: '100vh',
      background: '#f8f9fa',
      display: 'flex',
      position: 'relative',
      overflow: 'hidden',
      fontFamily: '"DM Sans", system-ui, sans-serif'
    }}>
      {/* Left side - Hero image and content */}
      <div style={{
        flex: '1',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh'
      }}>
        {/* Geometric shapes overlay */}
        <div style={{
          position: 'absolute',
          top: '10%',
          left: '10%',
          width: '200px',
          height: '200px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '50%',
          filter: 'blur(40px)'
        }} />
        <div style={{
          position: 'absolute',
          bottom: '20%',
          right: '15%',
          width: '150px',
          height: '150px',
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: '50%',
          filter: 'blur(30px)'
        }} />
        
        {/* Hero content */}
        <div style={{
          textAlign: 'center',
          color: 'white',
          zIndex: 2,
          maxWidth: '400px',
          padding: '2rem'
        }}>
          <div style={{
            width: '120px',
            height: '120px',
            background: 'rgba(255, 255, 255, 0.15)',
            borderRadius: '50%',
            margin: '0 auto 2rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backdropFilter: 'blur(10px)'
          }}>
            <MDBIcon icon="vr-cardboard" size="3x" style={{ color: 'white' }} />
          </div>
          
          <h1 style={{
            fontSize: '2.5rem',
            fontWeight: '700',
            marginBottom: '1rem',
            letterSpacing: '-0.02em'
          }}>
            NEW DIGITAL UNIVERSE
          </h1>
          
          <p style={{
            fontSize: '1.1rem',
            opacity: '0.9',
            lineHeight: '1.6',
            marginBottom: '2rem'
          }}>
            Step into the future with cutting-edge VR technology and immersive digital experiences
          </p>
          
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            marginBottom: '2rem'
          }}>
            <div style={{
              padding: '0.5rem 1rem',
              background: 'rgba(255, 255, 255, 0.2)',
              borderRadius: '20px',
              fontSize: '0.9rem',
              fontWeight: '500',
              backdropFilter: 'blur(10px)'
            }}>
              VR Ready
            </div>
            <div style={{
              padding: '0.5rem 1rem',
              background: 'rgba(255, 255, 255, 0.2)',
              borderRadius: '20px',
              fontSize: '0.9rem',
              fontWeight: '500',
              backdropFilter: 'blur(10px)'
            }}>
              AI Powered
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Login form */}
      <div style={{
        flex: '1',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        background: 'white'
      }}>
        <div style={{
          width: '100%',
          maxWidth: '400px'
        }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <h2 style={{
              fontSize: '2rem',
              fontWeight: '700',
              color: '#1a1a1a',
              marginBottom: '0.5rem'
            }}>
              Welcome Back
            </h2>
            <p style={{
              color: '#666',
              fontSize: '1rem'
            }}>
              Sign in to your account
            </p>
          </div>

          {/* Login Form */}
          <form style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Email Input */}
            <div>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                color: '#333'
              }}>
                Email Address
              </label>
              <input
                type="email"
                style={{
                  width: '100%',
                  padding: '14px 16px',
                  border: '2px solid #e1e5e9',
                  borderRadius: '10px',
                  fontSize: '16px',
                  outline: 'none',
                  transition: 'all 0.2s ease',
                  fontFamily: '"DM Sans", system-ui, sans-serif'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#667eea'
                  e.target.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#e1e5e9'
                  e.target.style.boxShadow = 'none'
                }}
              />
            </div>

            {/* Password Input */}
            <div>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '500',
                color: '#333'
              }}>
                Password
              </label>
              <input
                type="password"
                style={{
                  width: '100%',
                  padding: '14px 16px',
                  border: '2px solid #e1e5e9',
                  borderRadius: '10px',
                  fontSize: '16px',
                  outline: 'none',
                  transition: 'all 0.2s ease',
                  fontFamily: '"DM Sans", system-ui, sans-serif'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#667eea'
                  e.target.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#e1e5e9'
                  e.target.style.boxShadow = 'none'
                }}
              />
            </div>

            {/* Options */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '14px'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input 
                  type="checkbox" 
                  style={{ 
                    marginRight: '0.5rem',
                    accentColor: '#667eea'
                  }} 
                />
                <span style={{ color: '#666' }}>Remember me</span>
              </label>
              <a 
                href='#' 
                style={{ 
                  color: '#667eea',
                  textDecoration: 'none',
                  fontWeight: '500'
                }}
              >
                Forgot password?
              </a>
            </div>

            {/* Sign In Button */}
            <button
              type="submit"
              style={{
                width: '100%',
                padding: '16px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                borderRadius: '10px',
                color: 'white',
                fontSize: '16px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)'
              }}
              onMouseOver={(e) => {
                e.target.style.transform = 'translateY(-2px)'
                e.target.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.4)'
              }}
              onMouseOut={(e) => {
                e.target.style.transform = 'translateY(0)'
                e.target.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.3)'
              }}
            >
              Sign In
            </button>

            {/* Divider */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '1rem',
              margin: '1rem 0'
            }}>
              <div style={{ height: '1px', background: '#e1e5e9', flex: 1 }} />
              <span style={{ color: '#666', fontSize: '14px' }}>or continue with</span>
              <div style={{ height: '1px', background: '#e1e5e9', flex: 1 }} />
            </div>

            {/* Google Button */}
            <button
              type="button"
              onClick={onGoogle}
              style={{
                width: '100%',
                padding: '14px',
                backgroundColor: 'white',
                border: '2px solid #e1e5e9',
                borderRadius: '10px',
                fontSize: '16px',
                fontWeight: '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => {
                e.target.style.borderColor = '#667eea'
                e.target.style.backgroundColor = '#f8f9ff'
              }}
              onMouseOut={(e) => {
                e.target.style.borderColor = '#e1e5e9'
                e.target.style.backgroundColor = 'white'
              }}
            >
              <MDBIcon fab icon='google' style={{ color: '#4285f4', fontSize: '18px' }} />
              Continue with Google
            </button>

            {/* Sign Up Link */}
            <div style={{ textAlign: 'center', marginTop: '1rem' }}>
              <span style={{ color: '#666' }}>Don't have an account? </span>
              <a 
                href='#' 
                style={{ 
                  color: '#667eea',
                  textDecoration: 'none',
                  fontWeight: '600'
                }}
              >
                Sign up
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}


