
/**
 * Comment and reply API functions for SAIL Orbit.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Create a comment or nested reply.
 *
 * @param {string} token - JWT access token.
 * @param {number} postId - Post ID.
 * @param {string} content - Comment text.
 * @param {number|null} parentId - Parent comment ID for replies.
 * @returns {Promise<Object>} Created comment or reply.
 * @throws {Error} If creation fails.
 */
export async function createComment(token, postId, content, parentId = null) {
  const response = await fetch(`${API_BASE_URL}/posts/${postId}/comments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      content,
      parent_id: parentId,
    }),
  })

  if (!response.ok) {
    throw new Error(`Comment creation failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Retrieve comments and replies in chronological order.
 *
 * @param {number} postId - Post ID.
 * @returns {Promise<Array<Object>>} Comments and replies.
 * @throws {Error} If retrieval fails.
 */
export async function getComments(postId) {
  const response = await fetch(`${API_BASE_URL}/posts/${postId}/comments`)

  if (!response.ok) {
    throw new Error(`Comment list request failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Update an owned comment or reply.
 *
 * @param {string} token - JWT access token.
 * @param {number} commentId - Comment ID.
 * @param {string} content - Replacement text.
 * @returns {Promise<Object>} Updated comment.
 * @throws {Error} If updating fails.
 */
export async function updateComment(token, commentId, content) {
  const response = await fetch(
    `${API_BASE_URL}/posts/comments/${commentId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ content }),
    }
  )

  if (!response.ok) {
    throw new Error(`Comment update failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Soft-delete an owned comment or reply.
 *
 * @param {string} token - JWT access token.
 * @param {number} commentId - Comment ID.
 * @returns {Promise<void>} Resolves after deletion.
 * @throws {Error} If deletion fails.
 */
export async function deleteComment(token, commentId) {
  const response = await fetch(
    `${API_BASE_URL}/posts/comments/${commentId}`,
    {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Comment deletion failed: ${response.status}`)
  }
}
