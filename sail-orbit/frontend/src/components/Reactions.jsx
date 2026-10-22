
/**
 * Display Like and Dislike controls for a SAIL Orbit post.
 *
 * Retrieve reaction counts and the authenticated user's existing reaction.
 * Allow users to add, switch, or remove their reaction.
 */

import { useEffect, useState } from "react";
import {
  getOwnReaction,
  getReactionCounts,
  setReaction,
} from "../api";

/**
 * Render reaction controls and counts for a post.
 *
 * @param {{ postId: number, token: string }} props
 *   - Post identification and authenticated session information.
 * @returns {import("react").JSX.Element} Post reaction controls.
 */
function Reactions({ postId, token }) {
  const [counts, setCounts] = useState({ likes: 0, dislikes: 0 });
  const [ownReaction, setOwnReaction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Retrieve reaction totals and the user's selected reaction.
  useEffect(() => {
    let active = true;

    async function loadReactions() {
      setLoading(true);
      setError("");

      try {
        const [reactionCounts, userReaction] = await Promise.all([
          getReactionCounts(postId),
          getOwnReaction(token, postId),
        ]);

        if (active) {
          setCounts(reactionCounts);
          setOwnReaction(userReaction?.reaction_type ?? null);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadReactions();

    return () => {
      active = false;
    };
  }, [postId, token]);

  /**
   * Add, switch, or remove the authenticated user's reaction.
   *
   * Refresh counts after the backend confirms the reaction change.
   *
   * @param {"like"|"dislike"} reactionType - Selected reaction.
   */
  async function handleReaction(reactionType) {
    setError("");
    setSaving(true);

    try {
      const updatedReaction = await setReaction(
        token,
        postId,
        reactionType,
      );

      const updatedCounts = await getReactionCounts(postId);

      // Update the selected reaction and totals from backend responses.
      setOwnReaction(updatedReaction?.reaction_type ?? null);
      setCounts(updatedCounts);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Loading reactions...</p>;
  }

  return (
    <section className="space-y-2" aria-label="Post reactions">
      {/* Display errors without clearing the existing reaction state. */}
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        {/* Highlight Like when it matches the user's saved reaction. */}
        <button
          type="button"
          disabled={saving}
          onClick={() => handleReaction("like")}
          aria-pressed={ownReaction === "like"}
          className={`rounded-md border px-3 py-2 text-sm disabled:opacity-50 ${
            ownReaction === "like"
              ? "border-blue-600 bg-blue-100 text-blue-800"
              : "border-gray-300"
          }`}
        >
          Like ({counts.likes})
        </button>

        {/* Highlight Dislike when it matches the user's saved reaction. */}
        <button
          type="button"
          disabled={saving}
          onClick={() => handleReaction("dislike")}
          aria-pressed={ownReaction === "dislike"}
          className={`rounded-md border px-3 py-2 text-sm disabled:opacity-50 ${
            ownReaction === "dislike"
              ? "border-blue-600 bg-blue-100 text-blue-800"
              : "border-gray-300"
          }`}
        >
          Dislike ({counts.dislikes})
        </button>
      </div>
    </section>
  );
}

export default Reactions;
