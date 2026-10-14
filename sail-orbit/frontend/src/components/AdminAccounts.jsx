/**
 * Administrator interface for activating and deactivating Orbit accounts.
 */

import { useState } from "react";
import { updateUserStatus } from "../api";

/**
 * Display administrator account management controls.
 *
 * @param {{ token: string }} props - Administrator authentication token.
 * @returns {import("react").JSX.Element} Account management interface.
 */
export default function AdminAccounts({ token }) {
  const [username, setUsername] = useState("");
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  /**
   * Submit an account activation or deactivation request.
   *
   * @param {boolean} isActive - Requested account status.
   */
  async function handleStatusUpdate(isActive) {
    const targetUsername = username.trim();

    if (!targetUsername || updating) return;

    setUpdating(true);
    setError("");
    setResult(null);

    try {
      const account = await updateUserStatus(token, targetUsername, isActive);
      setResult(account);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  }

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Account Administration</h2>

      <div className="space-y-2">
        <label htmlFor="admin-username" className="block">
          Username
        </label>
        <input
          id="admin-username"
          type="text"
          value={username}
          onChange={(event) => {
            setUsername(event.target.value);
            setResult(null);
            setError("");
          }}
          className="w-full rounded-md border p-2"
        />
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          disabled={updating || !username.trim()}
          onClick={() => handleStatusUpdate(true)}
          className="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          Activate
        </button>

        <button
          type="button"
          disabled={updating || !username.trim()}
          onClick={() => handleStatusUpdate(false)}
          className="rounded-md bg-red-600 px-4 py-2 text-white disabled:opacity-50"
        >
          Deactivate
        </button>
      </div>

      {updating && <p role="status">Updating account...</p>}

      {error && <p role="alert">{error}</p>}

      {result && (
        <div role="status" className="space-y-1">
          <p>Username: {result.username}</p>
          <p>Role: {result.role}</p>
          <p>Status: {result.is_active ? "Active" : "Inactive"}</p>
        </div>
      )}
    </section>
  );
}
