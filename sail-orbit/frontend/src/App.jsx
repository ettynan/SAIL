/**
 * Main Orbit application with authentication and profile navigation.
 */

import { useState } from "react";
import RegisterForm from "./components/RegisterForm";
import LoginForm from "./components/LoginForm";
import UserProfile from "./components/UserProfile";
import PublicProfile from "./components/PublicProfile";
import AdminAccounts from "./components/AdminAccounts";

/**
 * Render authentication screens and authenticated profile navigation.
 *
 * @returns {import('react').JSX.Element} Application interface.
 */
function App() {
  const [screen, setScreen] = useState("login");
  const [accessToken, setAccessToken] = useState(null);
  const [profileScreen, setProfileScreen] = useState("own");
  const [usernameInput, setUsernameInput] = useState("");
  const [selectedUsername, setSelectedUsername] = useState("");

  /**
   * Open a public profile using the entered username.
   *
   * @param {import('react').SubmitEvent<HTMLFormElement>} event - Form submission event.
   */
  function handleProfileSearch(event) {
    event.preventDefault();

    const username = usernameInput.trim();

    if (!username) return;

    setSelectedUsername(username);
    setProfileScreen("public");
  }

  /**
   * End the current session and reset profile navigation.
   */
  function handleLogout() {
    setAccessToken(null);
    setProfileScreen("own");
    setUsernameInput("");
    setSelectedUsername("");
    setScreen("login");
  }

  if (accessToken) {
    return (
      <main className="mx-auto max-w-md space-y-6 p-8">
        <header className="space-y-4">
          <h1 className="text-3xl font-bold">SAIL Orbit</h1>

          {/* Navigate between account and public profile screens. */}
          <nav className="flex gap-4" aria-label="Profile navigation">
            <button
              type="button"
              className="text-sm underline"
              onClick={() => setProfileScreen("own")}
            >
              My Profile
            </button>

            <button
              type="button"
              className="text-sm underline"
              onClick={handleLogout}
            >
              Log out
            </button>
          </nav>

          {/* Look up a public profile by username. */}
          <form onSubmit={handleProfileSearch} className="flex gap-2">
            <input
              type="text"
              value={usernameInput}
              onChange={(event) => setUsernameInput(event.target.value)}
              placeholder="Search username"
              aria-label="Search username"
              className="min-w-0 flex-1 rounded-md border p-2"
              required
            />

            <button
              type="submit"
              className="rounded-md bg-blue-600 px-4 py-2 text-white"
            >
              View
            </button>
          </form>
        </header>

        {/* Display the authenticated profile, administration screen, or public profile. */}
        {profileScreen === "own" ? (
          <UserProfile
            token={accessToken}
            onOpenAdmin={() => setProfileScreen("admin")}
          />
        ) : profileScreen === "admin" ? (
          <AdminAccounts token={accessToken} />
        ) : (
          <>
            <button
              type="button"
              className="text-sm underline"
              onClick={() => setProfileScreen("own")}
            >
              Back to My Profile
            </button>

            <PublicProfile key={selectedUsername} username={selectedUsername} />
          </>
        )}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md space-y-6 p-8">
      <h1 className="text-3xl font-bold">SAIL Orbit</h1>

      {/* Display login or registration according to the selected screen. */}
      {screen === "login" ? (
        <LoginForm onSuccess={setAccessToken} />
      ) : (
        <RegisterForm onSuccess={() => setScreen("login")} />
      )}

      <button
        type="button"
        className="text-sm underline"
        onClick={() => setScreen(screen === "login" ? "register" : "login")}
      >
        {screen === "login"
          ? "Need an account? Register"
          : "Already have an account? Log in"}
      </button>
    </main>
  );
}

export default App;
