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

/**
 * Register a new Orbit user.
 *
 * @param {Object} userData - New account information.
 * @param {string} userData.username - Unique account username.
 * @param {string} userData.email - Account email address.
 * @param {string} userData.password - Account password.
 * @returns {Promise<string>} Registration response from FastAPI.
 * @throws {Error} If registration fails.
 */
export async function registerUser(userData) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userData),
  })

  if (!response.ok) {
    throw new Error(`Registration failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Authenticate an existing Orbit user.
 *
 * @param {string} username - Account username.
 * @param {string} password - Account password.
 * @returns {Promise<{access_token: string, token_type: string}>}
 *   JWT authentication response from FastAPI.
 * @throws {Error} If authentication fails.
 */
export async function loginUser(username, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    throw new Error(`Login failed: ${response.status}`)
  }

  return response.json()
}