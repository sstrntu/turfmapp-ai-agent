export function Login() {
  // thin redirect to static portal
  if (typeof window !== 'undefined') {
    window.location.replace('/portal.html')
  }
  return null
}

