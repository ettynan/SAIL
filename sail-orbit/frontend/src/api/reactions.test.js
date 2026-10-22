
/**
 * Automated tests for the Orbit reactions API client.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getOwnReaction,
  setReaction,
  getReactionCounts,
} from "./reactions";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * Create a simulated HTTP response for testing API requests.
 *
 * @param {number} status - HTTP response status.
 * @param {Object|null} data - Simulated response body.
 * @returns {Object} Mock response with status and JSON parsing.
 */
function mockResponse(status, data = null) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(data),
  };
}

/** Replace fetch with a mock before each test. */
beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

/** Restore the original fetch implementation after each test. */
afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * Verify Like and Dislike reaction API requests and responses.
 *
 * Tests cover retrieving the authenticated user's reaction, adding
 * reactions, switching reaction types, handling reaction removal,
 * retrieving counts, authentication, and unsuccessful HTTP responses.
 * Reaction uniqueness is enforced and tested by the backend.
 */
describe("Reactions API", () => {
  it("retrieves the authenticated user's existing Like reaction", async () => {
    // Simulate an existing Like reaction returned by FastAPI.
    const reaction = {
      id: 1,
      user_id: 2,
      post_id: 10,
      reaction_type: "like",
    };

    fetch.mockResolvedValue(mockResponse(200, reaction));

    const result = await getOwnReaction("test-token", 10);

    // Verify the GET endpoint and authentication header.
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/posts/10/reaction`,
      {
        headers: {
          Authorization: "Bearer test-token",
        },
      },
    );

    expect(result).toEqual(reaction);
  });

  it("retrieves the authenticated user's existing Dislike reaction", async () => {
    // Simulate a previously selected Dislike reaction.
    const reaction = {
      id: 1,
      user_id: 2,
      post_id: 10,
      reaction_type: "dislike",
    };

    fetch.mockResolvedValue(mockResponse(200, reaction));

    const result = await getOwnReaction("test-token", 10);

    // Verify the existing Dislike reaction is returned unchanged.
    expect(result).toEqual(reaction);
  });

  it("returns null when the authenticated user has not reacted", async () => {
    // FastAPI returns null when no reaction exists for this user.
    fetch.mockResolvedValue(mockResponse(200, null));

    const result = await getOwnReaction("test-token", 10);

    // Verify the client correctly handles the absence of a reaction.
    expect(result).toBeNull();
  });

  it("reports an HTTP error when retrieving the user's reaction fails", async () => {
    // Simulate an unsuccessful authenticated request.
    fetch.mockResolvedValue(mockResponse(401));

    // Verify the client rejects the request with the HTTP status.
    await expect(
      getOwnReaction("test-token", 10),
    ).rejects.toThrow("Own reaction request failed: 401");
  });

  it("adds a Like reaction with authentication", async () => {
    // Simulate a successful Like reaction response.
    const reaction = {
      id: 1,
      post_id: 10,
      user_id: 2,
      reaction_type: "like",
    };

    fetch.mockResolvedValue(mockResponse(200, reaction));

    const result = await setReaction("test-token", 10, "like");

    // Verify the endpoint, HTTP method, JWT, and reaction type.
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/posts/10/reaction`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-token",
        },
        body: JSON.stringify({ reaction_type: "like" }),
      },
    );

    expect(result).toEqual(reaction);
  });

  it("sends a Dislike reaction", async () => {
    // Simulate the backend accepting a Dislike reaction.
    const reaction = {
      id: 1,
      reaction_type: "dislike",
    };

    fetch.mockResolvedValue(mockResponse(200, reaction));

    const result = await setReaction("test-token", 10, "dislike");

    // Verify the request specifies the Dislike reaction type.
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
      reaction_type: "dislike",
    });

    expect(result).toEqual(reaction);
  });

  it("handles reaction removal returning null", async () => {
    // Selecting the same reaction again removes it on the backend.
    fetch.mockResolvedValue(mockResponse(200, null));

    const result = await setReaction("test-token", 10, "like");

    // Verify the client accepts the null response.
    expect(result).toBeNull();
  });

  it("retrieves Like and Dislike counts without authentication", async () => {
    // Simulate separate reaction totals returned by FastAPI.
    const counts = { likes: 5, dislikes: 2 };

    fetch.mockResolvedValue(mockResponse(200, counts));

    const result = await getReactionCounts(10);

    // Reaction counts are publicly accessible.
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/posts/10/reactions`,
    );

    expect(result).toEqual(counts);
  });

  it.each([
    ["reaction update", () => setReaction("token", 10, "like")],
    ["count retrieval", () => getReactionCounts(10)],
  ])("reports an HTTP error during %s", async (_operation, request) => {
    // Simulate an unsuccessful API response.
    fetch.mockResolvedValue(mockResponse(404));

    // Verify the client rejects the request with the HTTP status.
    await expect(request()).rejects.toThrow("404");
  });
});
