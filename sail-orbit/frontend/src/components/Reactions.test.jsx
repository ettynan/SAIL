
/**
 * Automated tests for the SAIL Orbit Reactions component.
 *
 * Verify Like/Dislike selection, toggling, reaction counts,
 * and API error handling.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

import Reactions from "./Reactions";
import {
  getOwnReaction,
  getReactionCounts,
  setReaction,
} from "../api";

/** Mock API functions to test the component independently of the backend. */
vi.mock("../api", () => ({
  getOwnReaction: vi.fn(),
  getReactionCounts: vi.fn(),
  setReaction: vi.fn(),
}));

/** Reset rendered components and mocks between tests. */
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

/**
 * Create a reaction response matching the backend schema.
 *
 * @param {"like"|"dislike"} reactionType - Reaction type.
 * @returns {Object} Reaction API response.
 */
function makeReaction(reactionType) {
  return {
    id: 1,
    user_id: 2,
    post_id: 10,
    reaction_type: reactionType,
    created_at: "2026-10-21T12:00:00Z",
  };
}

/**
 * Render reaction controls with mocked initial API responses.
 *
 * @param {Object|null} ownReaction - Current user's reaction.
 * @param {{likes: number, dislikes: number}} counts - Initial totals.
 * @returns {Promise<Object>} User-event controller.
 */
async function renderReactions(
  ownReaction = null,
  counts = { likes: 0, dislikes: 0 },
) {
  getOwnReaction.mockResolvedValue(ownReaction);
  getReactionCounts.mockResolvedValue(counts);

  const user = userEvent.setup();

  render(<Reactions postId={10} token="test-token" />);

  await screen.findByRole("button", { name: /Like \(/ });

  return user;
}

/**
 * Verify initial reaction loading and display.
 */
describe("Reactions display", () => {
  it("loads the user's reaction and reaction counts", async () => {
    await renderReactions(makeReaction("like"), {
      likes: 4,
      dislikes: 2,
    });

    expect(getOwnReaction).toHaveBeenCalledWith("test-token", 10);
    expect(getReactionCounts).toHaveBeenCalledWith(10);

    expect(screen.getByRole("button", { name: "Like (4)" }))
      .toHaveAttribute("aria-pressed", "true");

    expect(screen.getByRole("button", { name: "Dislike (2)" }))
      .toHaveAttribute("aria-pressed", "false");
  });

  it("displays no selected reaction when the user has not reacted", async () => {
    await renderReactions(null, { likes: 3, dislikes: 1 });

    expect(screen.getByRole("button", { name: "Like (3)" }))
      .toHaveAttribute("aria-pressed", "false");

    expect(screen.getByRole("button", { name: "Dislike (1)" }))
      .toHaveAttribute("aria-pressed", "false");
  });

  it("restores a previously selected Dislike", async () => {
    await renderReactions(makeReaction("dislike"), {
      likes: 2,
      dislikes: 5,
    });

    expect(screen.getByRole("button", { name: "Dislike (5)" }))
      .toHaveAttribute("aria-pressed", "true");

    expect(screen.getByRole("button", { name: "Like (2)" }))
      .toHaveAttribute("aria-pressed", "false");
  });
});

/**
 * Verify Like/Dislike creation, removal, and switching.
 */
describe("Reactions management", () => {
  it("adds a Like and refreshes reaction counts", async () => {
    const user = await renderReactions();

    setReaction.mockResolvedValue(makeReaction("like"));
    getReactionCounts.mockResolvedValueOnce({
      likes: 1,
      dislikes: 0,
    });

    await user.click(screen.getByRole("button", { name: "Like (0)" }));

    expect(setReaction).toHaveBeenCalledWith(
      "test-token",
      10,
      "like",
    );

    expect(await screen.findByRole("button", { name: "Like (1)" }))
      .toHaveAttribute("aria-pressed", "true");
  });

  it("removes a Like when the selected reaction is clicked again", async () => {
    const user = await renderReactions(makeReaction("like"), {
      likes: 1,
      dislikes: 0,
    });

    setReaction.mockResolvedValue(null);
    getReactionCounts.mockResolvedValueOnce({
      likes: 0,
      dislikes: 0,
    });

    await user.click(screen.getByRole("button", { name: "Like (1)" }));

    expect(setReaction).toHaveBeenCalledWith(
      "test-token",
      10,
      "like",
    );

    expect(await screen.findByRole("button", { name: "Like (0)" }))
      .toHaveAttribute("aria-pressed", "false");
  });

  it("switches from Like to Dislike", async () => {
    const user = await renderReactions(makeReaction("like"), {
      likes: 1,
      dislikes: 0,
    });

    setReaction.mockResolvedValue(makeReaction("dislike"));
    getReactionCounts.mockResolvedValueOnce({
      likes: 0,
      dislikes: 1,
    });

    await user.click(screen.getByRole("button", { name: "Dislike (0)" }));

    expect(setReaction).toHaveBeenCalledWith(
      "test-token",
      10,
      "dislike",
    );

    expect(await screen.findByRole("button", { name: "Dislike (1)" }))
      .toHaveAttribute("aria-pressed", "true");

    expect(screen.getByRole("button", { name: "Like (0)" }))
      .toHaveAttribute("aria-pressed", "false");
  });

  it("adds a Dislike", async () => {
    const user = await renderReactions();

    setReaction.mockResolvedValue(makeReaction("dislike"));
    getReactionCounts.mockResolvedValueOnce({
      likes: 0,
      dislikes: 1,
    });

    await user.click(screen.getByRole("button", { name: "Dislike (0)" }));

    expect(setReaction).toHaveBeenCalledWith(
      "test-token",
      10,
      "dislike",
    );

    expect(await screen.findByRole("button", { name: "Dislike (1)" }))
      .toHaveAttribute("aria-pressed", "true");
  });
});

/**
 * Verify that API errors are displayed without losing reaction state.
 */
describe("Reactions errors", () => {
  it("displays an error when initial reaction retrieval fails", async () => {
    getOwnReaction.mockRejectedValue(
      new Error("Own reaction request failed: 500"),
    );

    getReactionCounts.mockResolvedValue({
      likes: 0,
      dislikes: 0,
    });

    render(<Reactions postId={10} token="test-token" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Own reaction request failed: 500",
    );
  });

  it("preserves the existing reaction when updating fails", async () => {
    const user = await renderReactions(makeReaction("like"), {
      likes: 3,
      dislikes: 1,
    });

    setReaction.mockRejectedValue(
      new Error("Reaction update failed: 500"),
    );

    await user.click(screen.getByRole("button", { name: "Dislike (1)" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Reaction update failed: 500",
    );

    expect(screen.getByRole("button", { name: "Like (3)" }))
      .toHaveAttribute("aria-pressed", "true");

    expect(screen.getByRole("button", { name: "Dislike (1)" }))
      .toHaveAttribute("aria-pressed", "false");
  });
});
