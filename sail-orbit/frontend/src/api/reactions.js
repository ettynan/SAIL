
/**
 * Post reaction API functions for SAIL Orbit.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

/**
 * Add, switch, or remove a Like/Dislike reaction.
 *
 * Selecting the same reaction again removes it.
 *
 * @param {string} token - JWT access token.
 * @param {number} postId - Post ID.
 * @param {'like'|'dislike'} reactionType - Reaction type.
 * @returns {Promise<Object|null>} Reaction or null if removed.
 * @throws {Error} If updating fails.
 */
export async function setReaction(token, postId, reactionType) {
  const response = await fetch(`${API_BASE_URL}/posts/${postId}/reaction`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ reaction_type: reactionType }),
  })

  if (!response.ok) {
    throw new Error(`Reaction update failed: ${response.status}`)
  }

  return response.json()
}

/**
 * Retrieve separate Like and Dislike counts.
 *
 * @param {number} postId - Post ID.
 * @returns {Promise<{likes: number, dislikes: number}>} Reaction counts.
 * @throws {Error} If retrieval fails.
 */
export async function getReactionCounts(postId) {
  const response = await fetch(`${API_BASE_URL}/posts/${postId}/reactions`)

  if (!response.ok) {
    throw new Error(`Reaction counts request failed: ${response.status}`)
  }

  return response.json()
}
