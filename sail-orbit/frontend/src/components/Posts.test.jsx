
/**
 * Automated tests for the SAIL Orbit Posts component.
 *
 * Verify post management, ownership controls, API error handling,
 * and integration with Comments and Reactions.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

import Posts from "./Posts";
import {
  createPost,
  deletePost,
  getOwnProfile,
  getPosts,
  updatePost,
} from "../api";

/** Mock API calls to isolate frontend behavior from the backend. */
vi.mock("../api", () => ({
  createPost: vi.fn(),
  deletePost: vi.fn(),
  getOwnProfile: vi.fn(),
  getPosts: vi.fn(),
  updatePost: vi.fn(),
}));

/**
 * Mock child components to verify their integration without
 * duplicating their independent component tests.
 */
vi.mock("./Comments", () => ({
  default: ({ postId, token, currentUserId }) => (
    <div
      data-testid={`comments-${postId}`}
      data-token={token}
      data-user-id={currentUserId}
    >
      Comments for post {postId}
    </div>
  ),
}));

vi.mock("./Reactions", () => ({
  default: ({ postId, token }) => (
    <div
      data-testid={`reactions-${postId}`}
      data-token={token}
    >
      Reactions for post {postId}
    </div>
  ),
}));

/** Reset rendered components and API mocks between tests. */
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

/**
 * Create a post matching the backend response structure.
 *
 * @param {number} id - Post ID.
 * @param {Object} overrides - Optional field replacements.
 * @returns {Object} Post API response.
 */
function makePost(id, overrides = {}) {
  return {
    id,
    author_id: 2,
    content: `Post ${id}`,
    is_deleted: false,
    created_at: "2026-10-21T12:00:00Z",
    updated_at: "2026-10-21T12:00:00Z",
    ...overrides,
  };
}

/**
 * Render the post feed with mocked profile and post responses.
 *
 * @param {Array<Object>} posts - Initial posts.
 * @param {number} currentUserId - Authenticated user ID.
 * @returns {Promise<Object>} User-event controller.
 */
async function renderPosts(posts = [], currentUserId = 2) {
  getOwnProfile.mockResolvedValue({ id: currentUserId });
  getPosts.mockResolvedValue(posts);

  const user = userEvent.setup();

  render(<Posts token="test-token" />);

  // Wait until the initial feed request completes.
  await screen.findByRole("heading", { name: "Posts" });

  return user;
}

/**
 * Verify post feed rendering and child component integration.
 */
describe("Posts display and integration", () => {
  it("loads the authenticated profile and post feed", async () => {
    await renderPosts([makePost(1)]);

    expect(getOwnProfile).toHaveBeenCalledWith("test-token");
    expect(getPosts).toHaveBeenCalled();

    expect(screen.getByText("Post 1")).toBeInTheDocument();
  });

  it("displays a message when the feed is empty", async () => {
    await renderPosts();

    expect(screen.getByText("No posts yet.")).toBeInTheDocument();
  });

  it("renders Comments and Reactions for each active post", async () => {
    await renderPosts([
      makePost(1),
      makePost(2),
    ]);

    for (const postId of [1, 2]) {
      const comments = screen.getByTestId(`comments-${postId}`);
      const reactions = screen.getByTestId(`reactions-${postId}`);

      expect(comments).toBeInTheDocument();
      expect(reactions).toBeInTheDocument();

      // Verify that both components receive the correct post ID and token.
      expect(comments).toHaveAttribute("data-token", "test-token");
      expect(comments).toHaveAttribute("data-user-id", "2");
      expect(reactions).toHaveAttribute("data-token", "test-token");
    }
  });

  it("does not render reactions for a soft-deleted post", async () => {
    await renderPosts([
      makePost(1, {
        content: "[Deleted]",
        is_deleted: true,
      }),
    ]);

    // Preserve comment history but disable reactions on deleted posts.
    expect(screen.getByTestId("comments-1")).toBeInTheDocument();
    expect(screen.queryByTestId("reactions-1")).not.toBeInTheDocument();
  });

  it("renders child components for a newly created post", async () => {
    const user = await renderPosts();

    createPost.mockResolvedValue(
      makePost(3, { content: "New post" }),
    );

    await user.type(
      screen.getByLabelText("Create a post"),
      "New post",
    );

    await user.click(screen.getByRole("button", { name: "Publish" }));

    expect(await screen.findByText("New post")).toBeInTheDocument();
    expect(screen.getByTestId("comments-3")).toBeInTheDocument();
    expect(screen.getByTestId("reactions-3")).toBeInTheDocument();
  });
});

/**
 * Verify creation, editing, deletion, and ownership controls.
 */
describe("Posts management", () => {
  it("creates a post and adds it to the feed", async () => {
    const user = await renderPosts([makePost(1)]);

    createPost.mockResolvedValue(
      makePost(2, { content: "Created post" }),
    );

    await user.type(
      screen.getByLabelText("Create a post"),
      "Created post",
    );

    await user.click(screen.getByRole("button", { name: "Publish" }));

    expect(createPost).toHaveBeenCalledWith(
      "test-token",
      "Created post",
    );

    expect(await screen.findByText("Created post")).toBeInTheDocument();
    expect(screen.getByLabelText("Create a post")).toHaveValue("");
  });

  it("edits a post owned by the authenticated user", async () => {
    const user = await renderPosts([makePost(1)]);

    updatePost.mockResolvedValue(
      makePost(1, { content: "Updated post" }),
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));

    const editor = screen.getByLabelText("Edit post content");

    await user.clear(editor);
    await user.type(editor, "Updated post");

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(updatePost).toHaveBeenCalledWith(
      "test-token",
      1,
      "Updated post",
    );

    expect(await screen.findByText("Updated post")).toBeInTheDocument();
  });

  it("cancels editing without changing the post", async () => {
    const user = await renderPosts([makePost(1)]);

    await user.click(screen.getByRole("button", { name: "Edit" }));

    const editor = screen.getByLabelText("Edit post content");

    await user.clear(editor);
    await user.type(editor, "Discard this edit");

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByText("Post 1")).toBeInTheDocument();
    expect(updatePost).not.toHaveBeenCalled();
  });

  it("deletes a post and removes its child components", async () => {
    const user = await renderPosts([makePost(1)]);

    deletePost.mockResolvedValue(undefined);

    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.queryByText("Post 1")).not.toBeInTheDocument();
    });

    expect(deletePost).toHaveBeenCalledWith("test-token", 1);
    expect(screen.queryByTestId("comments-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("reactions-1")).not.toBeInTheDocument();
  });

  it("hides editing and deletion controls for another user's post", async () => {
    await renderPosts([
      makePost(1, { author_id: 99 }),
    ]);

    expect(screen.getByText("Post 1")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Edit" }))
      .not.toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Delete" }))
      .not.toBeInTheDocument();

    // Comments and reactions remain available on other users' posts.
    expect(screen.getByTestId("comments-1")).toBeInTheDocument();
    expect(screen.getByTestId("reactions-1")).toBeInTheDocument();
  });
});

/**
 * Verify API errors and preservation of unsaved content.
 */
describe("Posts errors", () => {
  it("displays an error when loading posts fails", async () => {
    getOwnProfile.mockResolvedValue({ id: 2 });
    getPosts.mockRejectedValue(new Error("Unable to load posts."));

    render(<Posts token="test-token" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to load posts.",
    );
  });

  it("preserves post content when creation fails", async () => {
    const user = await renderPosts();

    createPost.mockRejectedValue(
      new Error("Post creation failed: 500"),
    );

    await user.type(
      screen.getByLabelText("Create a post"),
      "Keep this draft",
    );

    await user.click(screen.getByRole("button", { name: "Publish" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Post creation failed: 500",
    );

    expect(screen.getByLabelText("Create a post")).toHaveValue(
      "Keep this draft",
    );
  });

  it("preserves edited content when updating fails", async () => {
    const user = await renderPosts([makePost(1)]);

    updatePost.mockRejectedValue(
      new Error("Post update failed: 500"),
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));

    const editor = screen.getByLabelText("Edit post content");

    await user.clear(editor);
    await user.type(editor, "Unsaved changes");

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Post update failed: 500",
    );

    expect(editor).toHaveValue("Unsaved changes");
    expect(screen.getByText("Post 1")).toBeInTheDocument();
  });

  it("keeps a post visible when deletion fails", async () => {
    const user = await renderPosts([makePost(1)]);

    deletePost.mockRejectedValue(
      new Error("Post deletion failed: 500"),
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Post deletion failed: 500",
    );

    expect(screen.getByText("Post 1")).toBeInTheDocument();
    expect(screen.getByTestId("comments-1")).toBeInTheDocument();
    expect(screen.getByTestId("reactions-1")).toBeInTheDocument();
  });
});
