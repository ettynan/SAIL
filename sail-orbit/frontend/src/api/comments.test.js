
/**
 * Automated tests for the Orbit comments API client.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createComment,
  getComments,
  updateComment,
  deleteComment,
} from "./comments";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * Create a simulated HTTP response for testing API requests.
 *
 * @param {number} status - HTTP response status.
 * @param {Object|Array|null} data - Simulated response body.
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
 * Verify comment and reply API requests and responses.
 *
 * Tests cover creation, retrieval, editing, deletion, authentication
 * headers, nested replies, and unsuccessful HTTP responses.
 * Authorization enforcement is tested separately by the backend suite.
 */
describe("Comments API", () => {
  it("creates a comment with authentication", async () => {
    // Simulate a successful comment creation response.
    const comment = {
      id: 1,
      post_id: 10,
      content: "Test comment",
      parent_id: null,
    };

    fetch.mockResolvedValue(mockResponse(201, comment));

    const result = await createComment("test-token", 10, "Test comment");

    // Verify the endpoint, HTTP method, authentication, and request body.
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/posts/10/comments`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-token",
        },
        body: JSON.stringify({
          content: "Test comment",
          parent_id: null,
        }),
      },
    );

    expect(result).toEqual(comment);
  });

  it("creates a reply referencing its parent comment", async () => {
    // Simulate creation of a nested reply.
    const reply = {
      id: 2,
      post_id: 10,
      content: "Test reply",
      parent_id: 1,
    };

    fetch.mockResolvedValue(mockResponse(201, reply));

    const result = await createComment("test-token", 10, "Test reply", 1);

    // Verify the parent comment ID is included in the request.
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
      content: "Test reply",
      parent_id: 1,
    });

    expect(result).toEqual(reply);
  });

  it("retrieves comments without authentication", async () => {
    // Simulate a list of comments returned by FastAPI.
    const comments = [{ id: 1, content: "Test comment" }];

    fetch.mockResolvedValue(mockResponse(200, comments));

    const result = await getComments(10);

    // Public comment retrieval should not require a JWT.
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/posts/10/comments`,
    );

    expect(result).toEqual(comments);
  });

  it("updates an existing comment", async () => {
    // Simulate a successful comment update.
    const updated = { id: 1, content: "Updated comment" };

    fetch.mockResolvedValue(mockResponse(200, updated));

    const result = await updateComment(
      "test-token",
      1,
      "Updated comment",
    );

    // Verify the update uses PATCH and includes the JWT.
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/posts/comments/1`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-token",
        },
        body: JSON.stringify({ content: "Updated comment" }),
      },
    );

    expect(result).toEqual(updated);
  });

  it("deletes an existing comment", async () => {
    // FastAPI returns HTTP 204 without a response body.
    fetch.mockResolvedValue(mockResponse(204));

    await expect(
      deleteComment("test-token", 1),
    ).resolves.toBeUndefined();

    // Verify the deletion request includes authentication.
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/posts/comments/1`,
      {
        method: "DELETE",
        headers: {
          Authorization: "Bearer test-token",
        },
      },
    );
  });

  it.each([
    ["creation", () => createComment("token", 10, "Comment")],
    ["retrieval", () => getComments(10)],
    ["update", () => updateComment("token", 1, "Updated")],
    ["deletion", () => deleteComment("token", 1)],
  ])("reports an HTTP error during comment %s", async (_operation, request) => {
    // Simulate an unsuccessful API response.
    fetch.mockResolvedValue(mockResponse(403));

    // Verify the API client rejects the request with the HTTP status.
    await expect(request()).rejects.toThrow("403");
  });
});
