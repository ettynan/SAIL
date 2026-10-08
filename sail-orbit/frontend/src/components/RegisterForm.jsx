import { useState } from 'react'
import { registerUser } from '../api'

/**
 * Registration form for creating an Orbit account.
 *
 * @param {{ onSuccess: () => void }} props - Registration success callback.
 * @returns {import('react').JSX.Element} Registration form.
 */
export default function RegisterForm({ onSuccess }) {
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  /**
   * Submit registration data to FastAPI.
   *
   * @param {import('react').FormEvent<HTMLFormElement>} event - Form event.
   */
  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      await registerUser(form)
      onSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-2xl font-semibold">Create an account</h2>

      {[
        ['username', 'Username'],
        ['email', 'Email'],
        ['password', 'Password'],
      ].map(([name, label]) => (
        <label key={name} className="block space-y-1">
          <span className="text-sm font-medium">{label}</span>
          <input
            className="w-full rounded-md border p-2"
            type={name === 'password' ? 'password' : name === 'email' ? 'email' : 'text'}
            value={form[name]}
            onChange={(event) =>
              setForm({ ...form, [name]: event.target.value })
            }
            required
          />
        </label>
      ))}

      {error && <p role="alert" className="text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {submitting ? 'Registering...' : 'Register'}
      </button>
    </form>
  )
}