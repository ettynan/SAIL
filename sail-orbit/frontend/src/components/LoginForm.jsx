import { useState } from 'react'
import { loginUser } from '../api'

/**
 * Login form for authenticating an Orbit user.
 *
 * @param {{ onSuccess: (token: string) => void }} props - Login callback.
 * @returns {import('react').JSX.Element} Login form.
 */
export default function LoginForm({ onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  /**
   * Submit credentials to FastAPI.
   *
   * @param {import('react').FormEvent<HTMLFormElement>} event - Form event.
   */
  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const result = await loginUser(username, password)
      onSuccess(result.access_token)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-2xl font-semibold">Log in</h2>

      <label className="block space-y-1">
        <span className="text-sm font-medium">Username</span>
        <input
          className="w-full rounded-md border p-2"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
        />
      </label>

      <label className="block space-y-1">
        <span className="text-sm font-medium">Password</span>
        <input
          type="password"
          className="w-full rounded-md border p-2"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
      </label>

      {error && <p role="alert" className="text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {submitting ? 'Logging in...' : 'Log in'}
      </button>
    </form>
  )
}