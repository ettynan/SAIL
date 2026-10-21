
/**
 * User profile and account administration API functions.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Retrieve a user's public profile.
 *
 * @param {string} username - Requested username.
 * @returns {Promise<Object>} Public profile.
 * @throws {Error} If retrieval fails.
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
 * Retrieve the authenticated user's profile.
 *
 * @param {string} token - JWT access token.
 * @returns {Promise<Object>} Authenticated user's profile.
 * @throws {Error} If retrieval fails.
 */
export async function getOwnProfile(token) {
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Profile request failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Update the authenticated user's biography.
 *
 * @param {string} token - JWT access token.
 * @param {string|null} bio - Updated biography.
 * @returns {Promise<Object>} Updated profile.
 * @throws {Error} If the update fails.
 */
export async function updateOwnProfile(token, bio) {
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ bio }),
  })

  if (!response.ok) {
    throw new Error(`Profile update failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Activate or deactivate a user account.
 *
 * @param {string} token - Administrator JWT access token.
 * @param {string} username - Account username.
 * @param {boolean} isActive - Requested account status.
 * @returns {Promise<Object>} Updated account status.
 * @throws {Error} If the operation fails.
 */
export async function updateUserStatus(token, username, isActive) {
  const response = await fetch(
    `${API_BASE_URL}/users/${encodeURIComponent(username)}/status`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ is_active: isActive }),
    }
  )

  if (!response.ok) {
    throw new Error(`Account status update failed: ${response.status}`)
  }

  return response.json()
}
