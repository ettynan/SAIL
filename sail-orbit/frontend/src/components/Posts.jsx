
/**
 * Display posts and allow authenticated users to create, edit, and delete
 * their own posts.
 */

import { useEffect, useState } from "react";
import {
  createPost,
  deletePost,
  getOwnProfile,
  getPosts,
  updatePost,
} from "../api";

/**
 * Render the post feed and post management controls.
 *
 * @param {{ token: string }} props - Authenticated session information.
 * @returns {import("react").JSX.Element} Posts interface.
 */
function Posts({ token }) {
  const [posts, setPosts] = useState([]);
  const [currentUserId, setCurrentUserId] = useState(null);
  const [content, setContent] = useState("");
  const [editingPostId, setEditingPostId] = useState(null);
  const [editContent, setEditContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Load the feed and identify which posts belong to the signed-in user.
  useEffect(() => {
    let active = true;

    async function loadPosts() {
      try {
        const [profile, postList] = await Promise.all([
          getOwnProfile(token),
          getPosts(),
        ]);

        if (active) {
          setCurrentUserId(profile.id);
          setPosts(postList);
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

    loadPosts();

    return () => {
      active = false;
    };
  }, [token]);

  /**
   * Create a post and add it to the beginning of the feed.
   */
  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    setSaving(true);

    try {
      const newPost = await createPost(token, content);
      setPosts((previous) => [newPost, ...previous]);
      setContent("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  /**
   * Populate the editor with an existing post's content.
   */
  function beginEditing(post) {
    setEditingPostId(post.id);
    setEditContent(post.content);
    setError("");
  }

  /**
   * Save edited content and update the displayed post.
   */
  async function handleUpdate(event) {
    event.preventDefault();
    setError("");
    setSaving(true);

    try {
      const updatedPost = await updatePost(token, editingPostId, editContent);

      setPosts((previous) =>
        previous.map((post) =>
          post.id === updatedPost.id ? updatedPost : post
        )
      );

      setEditingPostId(null);
      setEditContent("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  /**
   * Delete a post and remove it from the displayed feed.
   */
  async function handleDelete(postId) {
    setError("");
    setSaving(true);

    try {
      await deletePost(token, postId);
      setPosts((previous) => previous.filter((post) => post.id !== postId));

      if (editingPostId === postId) {
        setEditingPostId(null);
        setEditContent("");
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p>Loading posts...</p>;
  }

  return (
    <section className="space-y-6">
      <h2 className="text-xl font-semibold">Posts</h2>

      {/* Display API errors without discarding the current form contents. */}
      {error && <p role="alert" className="text-red-600">{error}</p>}

      {/* Compose a new post using the authenticated user's account. */}
      <form onSubmit={handleCreate} className="space-y-3">
        <label htmlFor="post-content" className="block font-medium">
          Create a post
        </label>

        <textarea
          id="post-content"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          maxLength={5000}
          rows={4}
          required
          className="w-full rounded-md border p-2"
        />

        <button
          type="submit"
          disabled={saving || !content.trim()}
          className="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          Publish
        </button>
      </form>

      {/* Display the posts returned by the backend. */}
      {posts.length === 0 && <p>No posts yet.</p>}

      <div className="space-y-4">
        {posts.map((post) => (
          <article key={post.id} className="space-y-3 rounded-md border p-4">
            <p className="whitespace-pre-wrap">{post.content}</p>

            <p className="text-sm text-gray-500">
              Posted {new Date(post.created_at).toLocaleString()}
            </p>

            {/* Only show editing controls for posts owned by this account. */}
            {post.author_id === currentUserId && (
              <div className="space-y-3">
                {editingPostId === post.id ? (
                  <form onSubmit={handleUpdate} className="space-y-2">
                    <textarea
                      aria-label="Edit post content"
                      value={editContent}
                      onChange={(event) => setEditContent(event.target.value)}
                      maxLength={5000}
                      rows={4}
                      required
                      className="w-full rounded-md border p-2"
                    />

                    <div className="flex gap-3">
                      <button
                        type="submit"
                        disabled={saving || !editContent.trim()}
                        className="text-sm underline disabled:opacity-50"
                      >
                        Save
                      </button>

                      <button
                        type="button"
                        onClick={() => setEditingPostId(null)}
                        className="text-sm underline"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="flex gap-3">
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => beginEditing(post)}
                      className="text-sm underline"
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => handleDelete(post.id)}
                      className="text-sm text-red-600 underline"
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

export default Posts;
