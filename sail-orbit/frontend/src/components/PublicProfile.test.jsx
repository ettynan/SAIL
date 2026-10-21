/**
 * Automated tests for the Orbit PublicProfile component.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import PublicProfile from "./PublicProfile";
import { getPublicProfile } from "../api";

/** Mock API calls to isolate frontend behavior from the backend. */
vi.mock("../api", () => ({
  getPublicProfile: vi.fn(),
}));

/** Reset rendered components and API mocks between tests. */
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

/**
 * Verify public profile rendering and unavailable-profile error handling.
 *
 * Public profiles do not require an authentication token.
 */
describe("PublicProfile", () => {
  it("displays public profile information", async () => {
    // Simulate a successful public profile response.
    getPublicProfile.mockResolvedValue({
      username: "test2",
      bio: "Public biography",
      created_at: "2026-10-01T12:00:00Z",
    });

    render(<PublicProfile username="test2" />);

    // Confirm that the public biography and membership date section appear.
    expect(await screen.findByText("Public biography")).toBeInTheDocument();
    expect(screen.getByText("Member since")).toBeInTheDocument();

    // Verify that the requested username was passed to the API.
    expect(getPublicProfile).toHaveBeenCalledWith("test2");
  });

  it("displays an error when a profile does not exist", async () => {
    // Simulate the API rejecting a request for an unknown username.
    getPublicProfile.mockRejectedValue(new Error("User not found."));

    render(<PublicProfile username="missing-user" />);

    // Verify that the error is displayed instead of a public profile.
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "User not found.",
    );
  });
});

/**
 * Verify administrator account-management controls and API interactions.
 *
 * Tests cover disabled controls, activation, deactivation, and errors.
 * Authorization enforcement is tested separately by the backend suite.
 */
