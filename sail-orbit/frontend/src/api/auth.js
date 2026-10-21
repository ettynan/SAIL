
/**
 * Authentication API functions for SAIL Orbit.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Register a new Orbit user.
 *
 * @param {Object} userData - New account information.
 * @returns {Promise<Object>} Registration response.
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
