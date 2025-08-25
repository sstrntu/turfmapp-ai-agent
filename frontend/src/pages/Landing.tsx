import React from 'react'
import { MDBIcon } from 'mdb-react-ui-kit'

export function Landing() {
  return (
    <div style={{ 
      background: '#f8f9fa',
      fontFamily: '"DM Sans", system-ui, sans-serif',
      overflow: 'hidden'
    }}>
      {/* Navigation */}
      <nav style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        padding: '1rem 2rem',
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          maxWidth: '1200px',
          margin: '0 auto'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '1.25rem',
            fontWeight: '700',
            color: '#1a1a1a'
          }}>
            <MDBIcon icon="cube" style={{ color: '#667eea' }} />
            ACCESS PORTAL
          </div>
          
          <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
            <a href="#" style={{ color: '#666', textDecoration: 'none', fontWeight: '500' }}>Home</a>
            <a href="#" style={{ color: '#666', textDecoration: 'none', fontWeight: '500' }}>About</a>
            <a href="#" style={{ color: '#666', textDecoration: 'none', fontWeight: '500' }}>Services</a>
            <a href="#" style={{ color: '#666', textDecoration: 'none', fontWeight: '500' }}>Contact</a>
            <div style={{
              padding: '8px 16px',
              background: 'rgba(0, 0, 0, 0.05)',
              borderRadius: '20px',
              fontSize: '0.9rem'
            }}>
              Get Started
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        position: 'relative',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        paddingTop: '80px'
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 2rem',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '4rem',
          alignItems: 'center',
          width: '100%'
        }}>
          {/* Left Content */}
          <div>
            <div style={{
              fontSize: '0.9rem',
              color: '#667eea',
              fontWeight: '600',
              textTransform: 'uppercase',
              letterSpacing: '2px',
              marginBottom: '1rem'
            }}>
              FUTURISTIC
            </div>
            
            <h1 style={{
              fontSize: 'clamp(2.5rem, 5vw, 4rem)',
              fontWeight: '700',
              lineHeight: '1.1',
              color: '#1a1a1a',
              marginBottom: '1.5rem'
            }}>
              NEW DIGITAL<br />
              UNIVERSE
            </h1>
            
            <p style={{
              fontSize: '1.1rem',
              color: '#666',
              lineHeight: '1.6',
              marginBottom: '2.5rem',
              maxWidth: '500px'
            }}>
              Step into the future with cutting-edge VR technology and immersive digital experiences that redefine reality.
            </p>
            
            <div style={{
              display: 'flex',
              gap: '1rem',
              alignItems: 'center'
            }}>
              <button style={{
                padding: '14px 28px',
                background: '#1a1a1a',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '1rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}>
                Get Started
              </button>
              <button style={{
                padding: '14px 28px',
                background: 'transparent',
                color: '#1a1a1a',
                border: '2px solid #e1e5e9',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '1rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}>
                Contact Us
              </button>
            </div>
          </div>

          {/* Right Content - VR Image */}
          <div style={{ position: 'relative' }}>
            <div style={{
              position: 'relative',
              borderRadius: '20px',
              overflow: 'hidden',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)'
            }}>
              <img
                src="/neovision/PNG/NeoVision - Futuristic Tech & VR Website.png"
                alt="VR Experience"
                style={{
                  width: '100%',
                  height: 'auto',
                  display: 'block'
                }}
              />
            </div>
            
            {/* Floating Stats */}
            <div style={{
              position: 'absolute',
              top: '20%',
              right: '-10%',
              background: 'white',
              padding: '1.5rem',
              borderRadius: '15px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{
                fontSize: '2rem',
                fontWeight: '700',
                color: '#1a1a1a',
                marginBottom: '0.5rem'
              }}>
                472%
              </div>
              <div style={{
                fontSize: '0.9rem',
                color: '#666'
              }}>
                Reality
              </div>
            </div>
            
            {/* User Avatars */}
            <div style={{
              position: 'absolute',
              bottom: '10%',
              left: '-10%',
              background: 'white',
              padding: '1.5rem',
              borderRadius: '15px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{
                display: 'flex',
                marginBottom: '1rem'
              }}>
                <div style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  marginRight: '-8px',
                  border: '2px solid white'
                }}></div>
                <div style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  marginRight: '-8px',
                  border: '2px solid white'
                }}></div>
                <div style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  marginRight: '-8px',
                  border: '2px solid white'
                }}></div>
                <div style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                  border: '2px solid white'
                }}></div>
              </div>
              <div style={{
                fontSize: '1.2rem',
                fontWeight: '700',
                color: '#1a1a1a'
              }}>
                20+
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section style={{
        backgroundColor: '#1a1a1a',
        color: 'white',
        padding: '6rem 0',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center'
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 2rem',
          width: '100%'
        }}>
          <div style={{
            textAlign: 'center',
            marginBottom: '4rem'
          }}>
            <h2 style={{
              fontSize: 'clamp(2rem, 4vw, 3rem)',
              fontWeight: '700',
              marginBottom: '1rem'
            }}>
              OUR SERVICE
            </h2>
          </div>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '2rem'
          }}>
            {[
              {
                icon: 'eye',
                title: 'Reality Development',
                description: 'Creating immersive virtual reality experiences with cutting-edge technology and innovative design approaches.'
              },
              {
                icon: 'search',
                title: 'Digital Assistants',
                description: 'AI-powered digital companions that understand context and provide intelligent assistance across platforms.'
              },
              {
                icon: 'gamepad',
                title: 'Gaming Solutions',
                description: 'Revolutionary gaming platforms that merge reality with virtual worlds for unprecedented experiences.'
              }
            ].map((service, index) => (
              <div key={index} style={{
                background: 'rgba(255, 255, 255, 0.05)',
                padding: '2.5rem',
                borderRadius: '15px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)',
                textAlign: 'center',
                transition: 'all 0.3s ease'
              }}>
                <div style={{
                  width: '60px',
                  height: '60px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: '15px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 1.5rem'
                }}>
                  <MDBIcon icon={service.icon} size="lg" style={{ color: 'white' }} />
                </div>
                <h3 style={{
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  marginBottom: '1rem',
                  color: 'white'
                }}>
                  {service.title}
                </h3>
                <p style={{
                  color: 'rgba(255, 255, 255, 0.7)',
                  lineHeight: '1.6',
                  fontSize: '0.95rem'
                }}>
                  {service.description}
                </p>
                <button style={{
                  marginTop: '1.5rem',
                  padding: '8px 20px',
                  background: 'transparent',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  borderRadius: '20px',
                  color: 'white',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}>
                  Learn More
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '12px 20px',
  background: 'linear-gradient(135deg, #22c55e, #16a34a)',
  color: 'black',
  borderRadius: 999,
  textDecoration: 'none',
  fontWeight: 600,
}

const btnOutlineStyle: React.CSSProperties = {
  padding: '12px 20px',
  background: 'transparent',
  color: 'white',
  borderRadius: 999,
  border: '1px solid rgba(148,163,184,.5)',
  textDecoration: 'none',
  fontWeight: 600,
}


