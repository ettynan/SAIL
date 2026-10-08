/**
 * Main Orbit application with registration and login screens.
 */

import { useState } from 'react'
import RegisterForm from './components/RegisterForm'
import LoginForm from './components/LoginForm'

/**
 * Render the authentication interface and handle successful login.
 *
 * @returns {import('react').JSX.Element} Application interface.
 */
function App() {
  const [screen, setScreen] = useState('login')
  const [accessToken, setAccessToken] = useState(null)

  if (accessToken) {
    return (
      <main className="mx-auto max-w-md p-8">
        <h1 className="text-3xl font-bold">SAIL Orbit</h1>
        <p className="mt-4">Login successful.</p>
        <button
          type="button"
          className="mt-4 rounded-md border px-4 py-2"
          onClick={() => setAccessToken(null)}
        >
          Log out
        </button>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-md space-y-6 p-8">
      <h1 className="text-3xl font-bold">SAIL Orbit</h1>

      {screen === 'login' ? (
        <LoginForm onSuccess={setAccessToken} />
      ) : (
        <RegisterForm onSuccess={() => setScreen('login')} />
      )}

      <button
        type="button"
        className="text-sm underline"
        onClick={() => setScreen(screen === 'login' ? 'register' : 'login')}
      >
        {screen === 'login'
          ? 'Need an account? Register'
          : 'Already have an account? Log in'}
      </button>
    </main>
  )
}

export default App