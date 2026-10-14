/**
 * Automated tests for the Orbit AdminAccounts component.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

import AdminAccounts from "./AdminAccounts";
import { updateUserStatus } from "../api";

/** Mock API calls to isolate frontend behavior from the backend. */
vi.mock("../api", () => ({
  updateUserStatus: vi.fn(),
}));

/** Reset rendered components and API mocks between tests. */
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

/**
 * Verify administrator account-management controls and API interactions.
 *
 * Tests cover disabled controls, activation, deactivation, and errors.
 * Authorization enforcement is tested separately by the backend suite.
 */
describe("AdminAccounts", () => {
  it("disables account actions until a username is entered", () => {
    render(<AdminAccounts token="admin-token" />);

    // Prevent account-management requests without a target username.
    expect(screen.getByRole("button", { name: "Activate" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Deactivate" })).toBeDisabled();
  });

  it("deactivates an account and displays the result", async () => {
    // Simulate a successful account deactivation response.
    updateUserStatus.mockResolvedValue({
      username: "test2",
      role: "user",
      is_active: false,
    });

    const user = userEvent.setup();

    render(<AdminAccounts token="admin-token" />);

    // Identify the target account and request deactivation.
    await user.type(screen.getByRole("textbox", { name: "Username" }), "test2");
    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    // Verify the displayed status and exact API request arguments.
    expect(await screen.findByText("Status: Inactive")).toBeInTheDocument();
    expect(updateUserStatus).toHaveBeenCalledWith(
      "admin-token",
      "test2",
      false,
    );
  });

  it("activates an account and displays the result", async () => {
    // Simulate a successful account activation response.
    updateUserStatus.mockResolvedValue({
      username: "test2",
      role: "user",
      is_active: true,
    });

    const user = userEvent.setup();

    render(<AdminAccounts token="admin-token" />);

    // Identify the target account and request activation.
    await user.type(screen.getByRole("textbox", { name: "Username" }), "test2");
    await user.click(screen.getByRole("button", { name: "Activate" }));

    // Verify the displayed status and exact API request arguments.
    expect(await screen.findByText("Status: Active")).toBeInTheDocument();
    expect(updateUserStatus).toHaveBeenCalledWith(
      "admin-token",
      "test2",
      true,
    );
  });

  it("displays errors returned by account management", async () => {
    // Simulate an API error when the requested account does not exist.
    updateUserStatus.mockRejectedValue(new Error("User not found."));

    const user = userEvent.setup();

    render(<AdminAccounts token="admin-token" />);

    // Attempt to deactivate an unknown account.
    await user.type(
      screen.getByRole("textbox", { name: "Username" }),
      "missing-user",
    );
    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    // The error should be visible without displaying a successful result.
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "User not found.",
    );
  });
});
