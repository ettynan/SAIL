/**
 * Main React application for SAIL Orbit.
 *
 * Verifies frontend-to-backend connectivity by retrieving and displaying
 * an existing user's public profile from the FastAPI backend.
 */

import { useEffect, useState } from 'react'
import { getPublicProfile } from './api'

/**
 * Render the Orbit application and display a public user profile.
 *
 * @returns {import('react').JSX.Element} The application interface.
 */
function App() {
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState(null)

  // Fetch an existing public profile when the component mounts.
  useEffect(() => {
    getPublicProfile('orbit_test_01')
      .then(setProfile)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="mb-6 text-3xl font-bold">SAIL Orbit</h1>

      {error && (
        <p className="text-red-600" role="alert">
          {error}
        </p>
      )}

      {!profile && !error && <p>Loading profile...</p>}

      {profile && (
        <section className="rounded-lg border p-6">
          <h2 className="text-xl font-semibold">
            {profile.display_name}
          </h2>

          <p className="text-sm text-gray-500">
            @{profile.username}
          </p>

          <p className="mt-4">{profile.bio}</p>
        </section>
      )}
    </main>
  )
}

export default App