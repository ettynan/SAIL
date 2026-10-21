
/**
 * Post API functions for SAIL Orbit.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Create a post for the authenticated user.
 *
 * @param {string} token - JWT access token.
 * @param {string} content - New post content.
 * @returns {Promise<Object>} Newly created post.
 * @throws {Error} If creation fails.
 */
export async function createPost(token, content) {
  const response = await fetch(`${API_BASE_URL}/posts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
    throw new Error(`Post creation failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Retrieve posts ordered from newest to oldest by the backend.
 *
 * @returns {Promise<Array<Object>>} List of posts.
 * @throws {Error} If retrieval fails.
 */
export async function getPosts() {
  const response = await fetch(`${API_BASE_URL}/posts`)

  if (!response.ok) {
    throw new Error(`Post list request failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Retrieve a single post.
 *
 * @param {number} postId - Requested post ID.
 * @returns {Promise<Object>} Requested post.
 * @throws {Error} If retrieval fails.
 */
export async function getPost(postId) {
  const response = await fetch(`${API_BASE_URL}/posts/${postId}`)

  if (!response.ok) {
    throw new Error(`Post request failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Update an owned post.
 *
 * @param {string} token - JWT access token.
 * @param {number} postId - Post ID.
 * @param {string} content - Replacement content.
 * @returns {Promise<Object>} Updated post.
 * @throws {Error} If updating fails.
 */
export async function updatePost(token, postId, content) {
  const response = await fetch(`${API_BASE_URL}/posts/${postId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
    throw new Error(`Post update failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Delete an owned post.
 *
 * @param {string} token - JWT access token.
 * @param {number} postId - Post ID.
 * @returns {Promise<void>} Resolves after deletion.
 * @throws {Error} If deletion fails.
 */
export async function deletePost(token, postId) {
  const response = await fetch(`${API_BASE_URL}/posts/${postId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Post deletion failed: ${response.status}`)
  }
}
