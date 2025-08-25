import React from 'react'
import { Link } from 'react-router-dom'
import { MDBNavbar, MDBContainer, MDBNavbarBrand, MDBNavbarNav, MDBNavbarItem } from 'mdb-react-ui-kit'

export function SiteNav() {
  return (
    <div className='position-fixed top-0 w-100' style={{ zIndex: 100, background: 'transparent' }}>
      <MDBNavbar light className='bg-transparent'>
        <MDBContainer fluid>
          <MDBNavbarBrand as={Link as any} to='/' style={{ color: 'white' }}>TurfMapp</MDBNavbarBrand>
          <MDBNavbarNav className='d-flex flex-row gap-4 ms-auto align-items-center'>
            <MDBNavbarItem>
              <Link to='/' style={linkStyle}>Home</Link>
            </MDBNavbarItem>
            <MDBNavbarItem>
              <Link to='/app' style={linkStyle}>App</Link>
            </MDBNavbarItem>
            <MDBNavbarItem>
              <Link to='/login' style={linkStyle}>Login</Link>
            </MDBNavbarItem>
            <MDBNavbarItem>
              <Link to='/admin' style={linkStyle}>Admin</Link>
            </MDBNavbarItem>
          </MDBNavbarNav>
        </MDBContainer>
      </MDBNavbar>
    </div>
  )
}

const linkStyle: React.CSSProperties = {
  color: '#e2e8f0',
  textDecoration: 'none',
  fontWeight: 600,
}
