# Spotify setup (optional)

Without Spotify, music wishes work as plain text ("Title – Artist"). With Spotify, students search real songs (with covers), and approved songs are added automatically to a private playlist in the teacher's account.

## Spotify's rules (as of 2026)

Spotify changed its Web API in February 2026. ClassPulse uses the current endpoints (`POST /me/playlists`, `POST`/`DELETE /playlists/{id}/items`, search with max. 10 results). For apps in **Development Mode**:

- The **owner of the developer app needs an active Spotify Premium subscription**, otherwise the app stops working.
- Only **up to 5 Spotify users** that you add to the app's allow-list can connect.
- Each school/instance should therefore create **its own** Spotify app. A teacher only needs to connect if they want playlist sync.

Extended Quota Mode (for more users) is only granted by Spotify to registered organisations; for a school instance Development Mode is normally enough.

## 1. Create the Spotify app (operator, once)

1. Go to <https://developer.spotify.com/dashboard> and log in (with the Premium account that will own the app).
2. **Create app**: any name (e.g. "ClassPulse – My School"), description, and select **Web API**.
3. **Redirect URI** — must match exactly:
   - Server: `https://your.domain/api/spotify/callback` (same as `PUBLIC_URL`)
   - Local laptop: `http://127.0.0.1:8000/api/spotify/callback`
     (Spotify does not allow `localhost`; use the IP `127.0.0.1` and open ClassPulse on the laptop via `http://127.0.0.1:8000` when connecting.)
4. Save, open **Settings**, copy **Client ID** and **Client secret**.
5. **User Management**: add the name and Spotify email of each teacher who will connect (max. 5).

## 2. Configure ClassPulse

In `.env`:

```env
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
```

Restart ClassPulse. The secret never leaves the server.

## 3. Connect (teacher)

1. In ClassPulse: **⚙︎ Settings → Connect Spotify**.
2. Log in to Spotify and allow access (ClassPulse asks only for permission to create and edit playlists; it never reads your listening history).
3. Start "Music wishes". A private playlist "ClassPulse – <topic>" is created; the playlist link appears on the activity card.

## How it behaves

- Students search; explicit songs are hidden unless the teacher allows them.
- The same song suggested twice becomes one entry with two votes.
- With "only visible after my approval" (default), a song goes into the playlist when the teacher approves it; rejecting or deleting removes it again.
- If Spotify is unreachable or the connection expired, the wish is kept and the card shows a warning; nothing breaks.

## Troubleshooting

| Problem | Fix |
|---|---|
| "INVALID_CLIENT: Invalid redirect URI" | Redirect URI in the dashboard must match exactly, including `https`/port. |
| Login works but connecting fails / 403 | The teacher's Spotify account is not in the app's User Management list, or the app owner's Premium expired. |
| Connecting from an iPad to a laptop installation | The `127.0.0.1` redirect only works on the laptop itself. Connect Spotify on the laptop, or use a server with HTTPS. |
