/**
 * Automated tests for the Orbit UserProfile component.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

import UserProfile from "./UserProfile";
import { getOwnProfile, updateOwnProfile } from "../api";

/** Mock API calls to isolate frontend behavior from the backend. */
vi.mock("../api", () => ({
  getOwnProfile: vi.fn(),
  updateOwnProfile: vi.fn(),
}));

/** Reset rendered components and API mocks between tests. */
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

/**
 * Standard user profile fixture shared by the UserProfile tests.
 *
 * Individual tests override fields when different account permissions
 * or profile values are required.
 */
const regularProfile = {
  username: "test1",
  email: "test1@example.com",
  bio: "Original biography",
  role: "user",
  is_active: true,
};

/**
 * Verify authenticated profile rendering, role-based navigation,
 * biography editing, and error handling.
 */
describe("UserProfile", () => {
  it("displays the authenticated user's profile", async () => {
    // Simulate a successful profile request for a regular user.
    getOwnProfile.mockResolvedValue(regularProfile);

    render(<UserProfile token="test-token" onOpenAdmin={vi.fn()} />);

    // Wait for the asynchronous profile request to finish.
    expect(await screen.findByText("test1@example.com")).toBeInTheDocument();
    expect(screen.getByText("Original biography")).toBeInTheDocument();

    // Regular users must not see administrator navigation.
    expect(
      screen.queryByRole("button", { name: "Admin" }),
    ).not.toBeInTheDocument();

    // Confirm that the component supplied its authentication token.
    expect(getOwnProfile).toHaveBeenCalledWith("test-token");
  });

  it("allows an administrator to open account administration", async () => {
    // Return an administrator profile instead of a regular user profile.
    getOwnProfile.mockResolvedValue({
      ...regularProfile,
      role: "admin",
    });

    const onOpenAdmin = vi.fn();

    render(<UserProfile token="admin-token" onOpenAdmin={onOpenAdmin} />);

    // The Admin button should appear after the administrator profile loads.
    await userEvent.click(
      await screen.findByRole("button", { name: "Admin" }),
    );

    // Verify that clicking Admin requests navigation to the admin screen.
    expect(onOpenAdmin).toHaveBeenCalledOnce();
  });

  it("saves biography changes", async () => {
    // Return the original profile, then simulate a successful API update.
    getOwnProfile.mockResolvedValue(regularProfile);
    updateOwnProfile.mockResolvedValue({
      ...regularProfile,
      bio: "Updated biography",
    });

    const user = userEvent.setup();

    render(<UserProfile token="test-token" onOpenAdmin={vi.fn()} />);

    // Open the editor and replace the existing biography.
    await user.click(await screen.findByRole("button", { name: "Edit bio" }));

    await user.clear(screen.getByRole("textbox", { name: "Biography" }));
    await user.type(
      screen.getByRole("textbox", { name: "Biography" }),
      "Updated biography",
    );

    // Submit the biography update.
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Verify that the saved biography and success message are displayed.
    expect(await screen.findByText("Biography saved.")).toBeInTheDocument();
    expect(screen.getByText("Updated biography")).toBeInTheDocument();

    // Confirm that the correct token and biography were sent to the API.
    expect(updateOwnProfile).toHaveBeenCalledWith(
      "test-token",
      "Updated biography",
    );
  });

  it("displays profile loading errors", async () => {
    // Simulate a failed request when loading the authenticated profile.
    getOwnProfile.mockRejectedValue(new Error("Profile request failed"));

    render(<UserProfile token="test-token" onOpenAdmin={vi.fn()} />);

    // The API error should be presented through an accessible alert.
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Profile request failed",
    );
  });

  it("preserves biography changes after a failed save", async () => {
    // Allow profile loading but simulate a failure when saving the biography.
    getOwnProfile.mockResolvedValue(regularProfile);
    updateOwnProfile.mockRejectedValue(new Error("Save failed"));

    const user = userEvent.setup();

    render(<UserProfile token="test-token" onOpenAdmin={vi.fn()} />);

    // Enter a replacement biography without modifying the stored profile.
    await user.click(await screen.findByRole("button", { name: "Edit bio" }));

    const biography = screen.getByRole("textbox", { name: "Biography" });

    await user.clear(biography);
    await user.type(biography, "Unsaved biography");
    await user.click(screen.getByRole("button", { name: "Save" }));

    // A failed save must display an error without discarding the user's input.
    expect(await screen.findByRole("alert")).toHaveTextContent("Save failed");
    expect(biography).toHaveValue("Unsaved biography");
  });
});

/**
 * Verify public profile rendering and unavailable-profile error handling.
 *
 * Public profiles do not require an authentication token.
 */
