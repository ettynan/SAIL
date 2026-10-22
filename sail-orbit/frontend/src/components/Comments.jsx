
/**
 * Display Reddit-style threaded comments and replies for an Orbit post.
 *
 * Allow authenticated users to create comments, reply at any depth,
 * edit or delete their own comments, and collapse discussion branches.
 */

import { useEffect, useState } from "react";
import {
  createComment,
  deleteComment,
  getComments,
  updateComment,
} from "../api";

/**
 * Organize flat API comments into parent-child relationships.
 *
 * Preserve the chronological order returned by the backend.
 *
 * @param {Array<Object>} comments - Comments returned by the API.
 * @returns {Array<Object>} Root comments with nested children.
 */
function buildCommentTree(comments) {
  const commentMap = new Map();
  const roots = [];

  // Create independent nodes without modifying the API response objects.
  for (const comment of comments) {
    commentMap.set(comment.id, {
      ...comment,
      children: [],
    });
  }

  // Attach replies to their parents while preserving comment order.
  for (const comment of comments) {
    const node = commentMap.get(comment.id);
    const parent = commentMap.get(comment.parent_id);

    if (parent && parent.id !== node.id) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

/**
 * Count all replies beneath a comment, including nested descendants.
 *
 * @param {Object} comment - Comment tree node.
 * @returns {number} Total number of descendant replies.
 */
function countReplies(comment) {
  return comment.children.reduce(
    (total, child) => total + 1 + countReplies(child),
    0,
  );
}

/**
 * Render comments and replies belonging to a single post.
 *
 * @param {{ postId: number, token: string, currentUserId: number|null }} props
 *   - Post identification and authenticated session information.
 * @returns {import("react").JSX.Element} Threaded comments interface.
 */
function Comments({ postId, token, currentUserId }) {
  const [comments, setComments] = useState([]);
  const [content, setContent] = useState("");
  const [replyingToId, setReplyingToId] = useState(null);
  const [replyContent, setReplyContent] = useState("");
  const [editingCommentId, setEditingCommentId] = useState(null);
  const [editContent, setEditContent] = useState("");
  const [collapsedIds, setCollapsedIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Retrieve the post's comments when the component loads.
  useEffect(() => {
    let active = true;

    async function loadComments() {
      try {
        const commentList = await getComments(postId);

        if (active) {
          setComments(commentList);
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

    loadComments();

    return () => {
      active = false;
    };
  }, [postId]);

  /**
   * Create a top-level comment.
   */
  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    setSaving(true);

    try {
      const newComment = await createComment(token, postId, content);

      setComments((previous) => [...previous, newComment]);
      setContent("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  /**
   * Create a reply beneath the selected parent comment.
   */
  async function handleReply(event) {
    event.preventDefault();
    setError("");
    setSaving(true);

    try {
      const newReply = await createComment(
        token,
        postId,
        replyContent,
        replyingToId,
      );

      setComments((previous) => [...previous, newReply]);
      setReplyingToId(null);
      setReplyContent("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  /**
   * Populate the editor with the selected comment's content.
   */
  function beginEditing(comment) {
    setEditingCommentId(comment.id);
    setEditContent(comment.content);
    setReplyingToId(null);
    setError("");
  }

  /**
   * Save an edited comment and update the displayed discussion.
   */
  async function handleUpdate(event) {
    event.preventDefault();
    setError("");
    setSaving(true);

    try {
      const updatedComment = await updateComment(
        token,
        editingCommentId,
        editContent,
      );

      setComments((previous) =>
        previous.map((comment) =>
          comment.id === updatedComment.id ? updatedComment : comment,
        ),
      );

      setEditingCommentId(null);
      setEditContent("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  /**
   * Soft-delete a comment while preserving its replies.
   */
  async function handleDelete(commentId) {
    setError("");
    setSaving(true);

    try {
      await deleteComment(token, commentId);

      // Match the backend's representation of deleted comments.
      setComments((previous) =>
        previous.map((comment) =>
          comment.id === commentId
            ? { ...comment, content: "[Deleted]", is_deleted: true }
            : comment,
        ),
      );

      if (editingCommentId === commentId) {
        setEditingCommentId(null);
        setEditContent("");
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  /**
   * Expand or collapse the replies beneath a comment.
   */
  function toggleCollapsed(commentId) {
    setCollapsedIds((previous) =>
      previous.includes(commentId)
        ? previous.filter((id) => id !== commentId)
        : [...previous, commentId],
    );
  }

  /**
   * Render a comment and its nested replies recursively.
   *
   * Limit visual indentation to preserve screen width without
   * restricting the depth of the underlying discussion.
   *
   * @param {Object} comment - Comment tree node.
   * @param {number} depth - Current reply depth.
   * @returns {import("react").JSX.Element} Comment and reply branch.
   */
  function renderComment(comment, depth = 0) {
    const isOwner = comment.author_id === currentUserId;
    const isCollapsed = collapsedIds.includes(comment.id);
    const replyCount = countReplies(comment);
    const indentation = Math.min(depth, 3);

    return (
      <div
        key={comment.id}
        className="space-y-3 border-l-2 border-gray-200 pl-3"
        style={{ marginLeft: `${indentation * 8}px` }}
      >
        {/* Preserve deleted comments as placeholders in the thread. */}
        <div className="space-y-2">
          <p
            className={
              comment.is_deleted
                ? "whitespace-pre-wrap text-gray-500 italic"
                : "whitespace-pre-wrap"
            }
          >
            {comment.content}
          </p>

          <p className="text-xs text-gray-500">
            {new Date(comment.created_at).toLocaleString()}
          </p>

          {/* Only active comments can be edited or deleted. */}
          {!comment.is_deleted && (
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={saving}
                onClick={() => {
                  setReplyingToId(comment.id);
                  setReplyContent("");
                  setEditingCommentId(null);
                  setError("");
                }}
                className="text-sm underline disabled:opacity-50"
              >
                Reply
              </button>

              {isOwner && (
                <>
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => beginEditing(comment)}
                    className="text-sm underline disabled:opacity-50"
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => handleDelete(comment.id)}
                    className="text-sm text-red-600 underline disabled:opacity-50"
                  >
                    Delete
                  </button>
                </>
              )}
            </div>
          )}

          {/* Edit an owned comment without changing its replies. */}
          {editingCommentId === comment.id && (
            <form onSubmit={handleUpdate} className="space-y-2">
              <textarea
                aria-label="Edit comment content"
                value={editContent}
                onChange={(event) => setEditContent(event.target.value)}
                maxLength={5000}
                rows={3}
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
                  onClick={() => setEditingCommentId(null)}
                  className="text-sm underline"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* Compose a reply linked to the selected parent comment. */}
          {replyingToId === comment.id && (
            <form onSubmit={handleReply} className="space-y-2">
              <textarea
                aria-label="Write a reply"
                value={replyContent}
                onChange={(event) => setReplyContent(event.target.value)}
                maxLength={5000}
                rows={3}
                required
                className="w-full rounded-md border p-2"
              />

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={saving || !replyContent.trim()}
                  className="text-sm underline disabled:opacity-50"
                >
                  Post reply
                </button>

                <button
                  type="button"
                  onClick={() => setReplyingToId(null)}
                  className="text-sm underline"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Keep the parent visible when its reply branch is collapsed. */}
        {replyCount > 0 && (
          <button
            type="button"
            onClick={() => toggleCollapsed(comment.id)}
            aria-expanded={!isCollapsed}
            className="text-sm text-blue-600 underline"
          >
            {isCollapsed
              ? `Show ${replyCount} ${replyCount === 1 ? "reply" : "replies"}`
              : `Hide ${replyCount} ${replyCount === 1 ? "reply" : "replies"}`}
          </button>
        )}

        {/* Recursively display descendants unless the branch is collapsed. */}
        {!isCollapsed && comment.children.length > 0 && (
          <div className="space-y-3">
            {comment.children.map((child) =>
              renderComment(child, depth + 1),
            )}
          </div>
        )}
      </div>
    );
  }

  if (loading) {
    return <p>Loading comments...</p>;
  }

  const commentTree = buildCommentTree(comments);

  return (
    <section className="space-y-4">
      <h3 className="font-semibold">Comments</h3>

      {/* Display API errors without clearing the current editor. */}
      {error && (
        <p role="alert" className="text-red-600">
          {error}
        </p>
      )}

      {/* Create a new top-level comment on this post. */}
      <form onSubmit={handleCreate} className="space-y-2">
        <label
          htmlFor={`comment-content-${postId}`}
          className="block text-sm font-medium"
        >
          Add a comment
        </label>

        <textarea
          id={`comment-content-${postId}`}
          value={content}
          onChange={(event) => setContent(event.target.value)}
          maxLength={5000}
          rows={3}
          required
          className="w-full rounded-md border p-2"
        />

        <button
          type="submit"
          disabled={saving || !content.trim()}
          className="rounded-md bg-blue-600 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          Comment
        </button>
      </form>

      {/* Display the discussion using parent-child relationships. */}
      {comments.length === 0 ? (
        <p className="text-sm text-gray-500">No comments yet.</p>
      ) : (
        <div className="space-y-4">
          {commentTree.map((comment) => renderComment(comment))}
        </div>
      )}
    </section>
  );
}

export default Comments;
