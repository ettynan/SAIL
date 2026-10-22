
/**
 * Automated tests for the Orbit Comments component.
 *
 * Verify threaded discussions, comment management, authorization-related
 * controls, and API error handling.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

import Comments from "./Comments";
import {
  createComment,
  deleteComment,
  getComments,
  updateComment,
} from "../api";

/** Mock API calls to isolate frontend behavior from the backend. */
vi.mock("../api", () => ({
  createComment: vi.fn(),
  deleteComment: vi.fn(),
  getComments: vi.fn(),
  updateComment: vi.fn(),
}));

/** Reset rendered components and API mocks between tests. */
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

/**
 * Create a comment with the fields returned by the backend.
 *
 * @param {number} id - Comment ID.
 * @param {number|null} parentId - Parent comment ID.
 * @param {Object} overrides - Optional field replacements.
 * @returns {Object} Comment API response.
 */
function makeComment(id, parentId = null, overrides = {}) {
  return {
    id,
    post_id: 10,
    author_id: 2,
    parent_id: parentId,
    content: `Comment ${id}`,
    is_deleted: false,
    created_at: "2026-10-21T12:00:00Z",
    updated_at: "2026-10-21T12:00:00Z",
    ...overrides,
  };
}

/**
 * Render the comments interface with an authenticated user.
 *
 * @param {Array<Object>} comments - Initial API comments.
 * @param {number|null} currentUserId - Signed-in user ID.
 * @returns {Promise<Object>} User-event controller.
 */
async function renderComments(comments = [], currentUserId = 2) {
  getComments.mockResolvedValue(comments);

  const user = userEvent.setup();

  render(
    <Comments
      postId={10}
      token="test-token"
      currentUserId={currentUserId}
    />,
  );

  await screen.findByText("Add a comment");

  return user;
}

/**
 * Verify comment rendering and Reddit-style threaded discussions.
 *
 * Tests cover nested replies, deep reply chains, branch collapsing,
 * and preservation of soft-deleted comments.
 */
describe("Comments display", () => {
  it("displays a message when no comments exist", async () => {
    await renderComments();

    expect(screen.getByText("No comments yet.")).toBeInTheDocument();
    expect(getComments).toHaveBeenCalledWith(10);
  });

  it("displays comments and replies in their parent-child hierarchy", async () => {
    const comments = [
      makeComment(1),
      makeComment(2, 1),
      makeComment(3, 2),
      makeComment(4, 1),
    ];

    await renderComments(comments);

    // Verify all comments and nested replies are displayed.
    for (const comment of comments) {
      expect(screen.getByText(comment.content)).toBeInTheDocument();
    }

    // The root comment has three descendants.
    expect(screen.getByRole("button", { name: "Hide 3 replies" }))
      .toBeInTheDocument();

    // The nested reply has one descendant.
    expect(screen.getByRole("button", { name: "Hide 1 reply" }))
      .toBeInTheDocument();
  });

  it("supports reply depth beyond three levels", async () => {
    const comments = [
      makeComment(1),
      makeComment(2, 1),
      makeComment(3, 2),
      makeComment(4, 3),
      makeComment(5, 4),
    ];

    await renderComments(comments);

    // All descendants remain visible regardless of nesting depth.
    for (const comment of comments) {
      expect(screen.getByText(comment.content)).toBeInTheDocument();
    }
  });

  it("collapses replies while keeping the parent visible", async () => {
    const user = await renderComments([
      makeComment(1),
      makeComment(2, 1),
      makeComment(3, 2),
    ]);

    // Collapse the entire branch beneath the root comment.
    await user.click(
      screen.getByRole("button", { name: "Hide 2 replies" }),
    );

    expect(screen.getByText("Comment 1")).toBeInTheDocument();
    expect(screen.queryByText("Comment 2")).not.toBeInTheDocument();
    expect(screen.queryByText("Comment 3")).not.toBeInTheDocument();

    // Expand the branch to restore its descendants.
    await user.click(
      screen.getByRole("button", { name: "Show 2 replies" }),
    );

    expect(screen.getByText("Comment 2")).toBeInTheDocument();
    expect(screen.getByText("Comment 3")).toBeInTheDocument();
  });

  it("preserves soft-deleted comments and their replies", async () => {
    await renderComments([
      makeComment(1, null, {
        content: "[Deleted]",
        is_deleted: true,
      }),
      makeComment(2, 1),
    ]);

    // The deleted parent remains visible to preserve discussion history.
    expect(screen.getByText("[Deleted]")).toBeInTheDocument();
    expect(screen.getByText("Comment 2")).toBeInTheDocument();
  });
});

/**
 * Verify comment creation, replies, editing, and soft deletion.
 *
 * Tests confirm that API responses update the displayed discussion.
 */
describe("Comments management", () => {
  it("creates a top-level comment", async () => {
    const user = await renderComments();

    const created = makeComment(1, null, {
      content: "New top-level comment",
    });

    createComment.mockResolvedValue(created);

    // Submit a new comment using the authenticated account.
    await user.type(
      screen.getByLabelText("Add a comment"),
      "New top-level comment",
    );

    await user.click(screen.getByRole("button", { name: "Comment" }));

    expect(createComment).toHaveBeenCalledWith(
      "test-token",
      10,
      "New top-level comment",
    );

    expect(
      await screen.findByText("New top-level comment"),
    ).toBeInTheDocument();

    expect(screen.getByLabelText("Add a comment")).toHaveValue("");
  });

  it("creates a nested reply linked to its parent", async () => {
    const user = await renderComments([makeComment(1)]);

    const created = makeComment(2, 1, {
      content: "New nested reply",
    });

    createComment.mockResolvedValue(created);

    // Open the reply editor for the parent comment.
    await user.click(screen.getByRole("button", { name: "Reply" }));

    await user.type(
      screen.getByLabelText("Write a reply"),
      "New nested reply",
    );

    await user.click(screen.getByRole("button", { name: "Post reply" }));

    expect(createComment).toHaveBeenCalledWith(
      "test-token",
      10,
      "New nested reply",
      1,
    );

    expect(
      await screen.findByText("New nested reply"),
    ).toBeInTheDocument();
  });

  it("edits a comment owned by the authenticated user", async () => {
    const user = await renderComments([makeComment(1)]);

    updateComment.mockResolvedValue(
      makeComment(1, null, { content: "Updated comment" }),
    );

    // Open the editor and replace the existing content.
    await user.click(screen.getByRole("button", { name: "Edit" }));

    const editor = screen.getByLabelText("Edit comment content");

    await user.clear(editor);
    await user.type(editor, "Updated comment");

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(updateComment).toHaveBeenCalledWith(
      "test-token",
      1,
      "Updated comment",
    );

    expect(
      await screen.findByText("Updated comment"),
    ).toBeInTheDocument();
  });

  it("soft-deletes a comment without removing its replies", async () => {
    const user = await renderComments([
      makeComment(1),
      makeComment(2, 1),
    ]);

    deleteComment.mockResolvedValue(undefined);

    // Delete the parent comment.
    const deleteButtons = screen.getAllByRole("button", { name: "Delete" });
    await user.click(deleteButtons[0]);

    expect(deleteComment).toHaveBeenCalledWith("test-token", 1);

    // The parent becomes a placeholder, and its reply remains visible.
    expect(await screen.findByText("[Deleted]")).toBeInTheDocument();
    expect(screen.getByText("Comment 2")).toBeInTheDocument();
  });

  it("does not display editing controls for another user's comment", async () => {
    await renderComments([
      makeComment(1, null, { author_id: 99 }),
    ]);

    // Replying remains available, but ownership controls are hidden.
    expect(screen.getByRole("button", { name: "Reply" }))
      .toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Edit" }))
      .not.toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Delete" }))
      .not.toBeInTheDocument();
  });
});

/**
 * Verify that API errors are displayed without losing user input.
 */
describe("Comments errors", () => {
  it("displays an error when comment retrieval fails", async () => {
    getComments.mockRejectedValue(new Error("Unable to load comments."));

    render(
      <Comments postId={10} token="test-token" currentUserId={2} />,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to load comments.",
    );
  });

  it("preserves comment text when creation fails", async () => {
    const user = await renderComments();

    createComment.mockRejectedValue(new Error("Comment creation failed: 500"));

    await user.type(
      screen.getByLabelText("Add a comment"),
      "Keep this comment",
    );

    await user.click(screen.getByRole("button", { name: "Comment" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Comment creation failed: 500",
    );

    expect(screen.getByLabelText("Add a comment")).toHaveValue(
      "Keep this comment",
    );
  });
});
