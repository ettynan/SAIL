/**
 * API client for communication with the SAIL Orbit FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Retrieve a user's public profile.
 *
 * @param {string} username - Username of the requested profile.
 * @returns {Promise<Object>} Public profile data returned by FastAPI.
 * @throws {Error} If the API request returns an unsuccessful response.
 */
export async function getPublicProfile(username) {
  const response = await fetch(
    `${API_BASE_URL}/users/${encodeURIComponent(username)}`
  )

  if (!response.ok) {
    throw new Error(`Profile request failed: ${response.status}`)
  }

  return response.json()
}