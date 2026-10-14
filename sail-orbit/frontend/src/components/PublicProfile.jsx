/**
 * Display an Orbit user's public profile.
 */

import { useEffect, useState } from "react";
import { getPublicProfile } from "../api";

/**
 * Retrieve and display a public user profile.
 *
 * @param {{ username: string }} props - Username of the requested profile.
 * @returns {import('react').JSX.Element} Public profile screen.
 */
export default function PublicProfile({ username }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    /**
     * Retrieve the requested public profile from FastAPI.
     *
     * @returns {Promise<void>} Resolves when the request finishes.
     */
    async function loadProfile() {
      setLoading(true);
      setError("");
      setProfile(null);

      try {
        const data = await getPublicProfile(username);

        // Update the displayed profile only while this request is active.
        if (active) {
          setProfile(data);
        }
      } catch (err) {
        // Display API errors, including unavailable profiles.
        if (active) {
          setError(err.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadProfile();

    // Ignore responses from requests associated with an earlier username.
    return () => {
      active = false;
    };
  }, [username]);

  if (loading) return <p>Loading profile...</p>;
  if (error) return <p role="alert">{error}</p>;
  if (!profile) return <p>Profile unavailable.</p>;

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">{profile.username}</h2>

      <dl className="space-y-3">
        {/* Display the user's public biography. */}
        <div>
          <dt className="font-medium">Bio</dt>
          <dd className="whitespace-pre-wrap">
            {profile.bio || "No biography added."}
          </dd>
        </div>

        {/* Display the account creation date in the user's locale. */}
        <div>
          <dt className="font-medium">Member since</dt>
          <dd>{new Date(profile.created_at).toLocaleDateString()}</dd>
        </div>
      </dl>
    </section>
  );
}
