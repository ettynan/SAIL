/**
 * Display and manage the authenticated user's Orbit profile.
 */

import { useEffect, useState } from "react";
import { getOwnProfile, updateOwnProfile } from "../api";

/**
 * Display the authenticated user's account profile.
 *
 * @param {{ token: string, onOpenAdmin: () => void }} props - Authentication token and administrator navigation callback.
 * @returns {import('react').JSX.Element} User profile screen.
 */
export default function UserProfile({ token, onOpenAdmin }) {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [bio, setBio] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadProfile() {
      try {
        const data = await getOwnProfile(token);
        // Initialize the profile and biography editor from the API response.
        if (active) {
          setProfile(data);
          setBio(data.bio ?? "");
        }
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    }

    loadProfile();

    return () => {
      active = false;
    };
  }, [token]);

  /**
   * Save biography changes to the authenticated user's profile.
   * @param {import('react').SubmitEvent<HTMLFormElement>} event - Form submission event.
   * @returns {Promise<void>} Resolves when the save operation finishes.
   */
  async function handleSave(event) {
    event.preventDefault();

    // Prevent duplicate submissions and clear previous messages.
    setSaving(true);
    setSaveError("");
    setSaveSuccess(false);

    try {
      // Save the biography through the authenticated API endpoint.
      const updatedProfile = await updateOwnProfile(token, bio);

      // Update the displayed profile with the saved database values.
      setProfile(updatedProfile);
      setBio(updatedProfile.bio ?? "");
      setEditing(false);
      setSaveSuccess(true);
    } catch (err) {
      // Keep the entered biography available for another save attempt.
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p>Loading profile...</p>;
  if (error) return <p role="alert">{error}</p>;
  if (!profile) return <p>Profile unavailable.</p>;

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">My Profile</h2>

      <dl className="space-y-3">
        <div>
          <dt className="font-medium">Username</dt>
          <dd>{profile.username}</dd>
        </div>
        <div>
          <dt className="font-medium">Email</dt>
          <dd>{profile.email}</dd>
        </div>
        {/* Display the saved biography or the editing form. */}
        <div>
          <dt className="font-medium">Bio</dt>
          <dd>
            {editing ? (
              <form onSubmit={handleSave} className="mt-2 space-y-3">
                {/* Edit the biography using the current form state. */}
                <textarea
                  value={bio}
                  onChange={(event) => setBio(event.target.value)}
                  rows={4}
                  className="w-full rounded-md border p-2"
                  aria-label="Biography"
                />

                {/* Display errors returned by the save operation. */}
                {saveError && (
                  <p role="alert" className="text-red-600">
                    {saveError}
                  </p>
                )}

                <div className="flex gap-3">
                  {/* Save the biography and prevent repeated submissions. */}
                  <button
                    type="submit"
                    disabled={saving}
                    className="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
                  >
                    {saving ? "Saving..." : "Save"}
                  </button>

                  {/* Discard unsaved changes and close the editor. */}
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => {
                      setBio(profile.bio ?? "");
                      setEditing(false);
                      setSaveError("");
                    }}
                    className="rounded-md border px-4 py-2"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <div className="mt-1 space-y-2">
                {/* Display the saved biography or its placeholder. */}
                <p className="whitespace-pre-wrap">
                  {profile.bio || "No biography added."}
                </p>

                {/* Open the biography editor. */}
                <button
                  type="button"
                  onClick={() => {
                    setSaveSuccess(false);
                    setEditing(true);
                  }}
                  className="text-sm underline"
                >
                  Edit bio
                </button>

                {/* Confirm a successful profile update. */}
                {saveSuccess && <p role="status">Biography saved.</p>}
              </div>
            )}
          </dd>
        </div>
        <div>
          <dt className="font-medium">Role</dt>
          <dd>{profile.role}</dd>
        </div>
        <div>
          <dt className="font-medium">Account status</dt>
          <dd>{profile.is_active ? "Active" : "Inactive"}</dd>
        </div>
      </dl>
      {/* Show administrator navigation only for administrator accounts. */}
      {profile.role === "admin" && (
        <button
          type="button"
          onClick={onOpenAdmin}
          className="rounded-md bg-blue-600 px-4 py-2 text-white"
        >
          Admin
        </button>
      )}
    </section>
  );
}
