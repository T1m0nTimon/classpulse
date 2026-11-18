# Privacy & anonymity — what ClassPulse really does

ClassPulse is designed so that **teachers cannot find out which student wrote, voted or suggested what**. This page explains honestly how that works and where its limits are.

## What students give us

Nothing personal. Students open a link, get a random device token and can take part. There are no student accounts, names, email addresses or profiles.

## What is stored in the database

| Data | Stored? | Notes |
|---|---|---|
| Student names, emails, accounts | **No** | do not exist |
| IP addresses, user agents, device fingerprints | **No** | never written to the database |
| Poll votes, quiz answers | Yes | with a per-activity pseudonym (see below), no timestamps |
| Questions, ideas, song wishes | Yes | text, votes, creation time |
| Rejected (filtered) messages | **No** | discarded immediately, only the reason is returned to the sender |
| The device token itself | **No** | stays on the student's device |
| Teacher email, name, password hash | Yes | needed for teacher login |
| Spotify tokens of the teacher | Yes | only if the teacher connects Spotify |

### The per-activity pseudonym

To stop a device from voting twice, each vote is stored together with `HMAC(SECRET_KEY, activity_id + device_token)`.

- The same device produces a **different** value in every activity, so votes cannot be linked across polls, questions or quizzes.
- The value is never sent to the teacher's browser (an automated test checks this).
- Without the device token — which only the student's browser has — the value cannot be traced back.

### Data retention

Ended or expired sessions are deleted with all their content after `DATA_RETENTION_DAYS` (default 30). Teachers can delete sessions, reset activities, or delete their account (which deletes everything) at any time.

## What the server sees but does not store

- **IP addresses** are needed to deliver web pages. ClassPulse uses them only in memory, hashed, for a few minutes, to rate-limit abuse (e.g. guessing session codes). They are not written to disk by ClassPulse.
- The bundled Caddy configuration and the uvicorn server (`--no-access-log`) have **access logging disabled**.

## Limits — please read

- **Your hosting provider, reverse proxy or school network** may log IP addresses and request times independently of ClassPulse. Check the settings of anything in front of ClassPulse (nginx, Cloudflare, school firewall). In a class of 25 on a shared school Wi-Fi, all students usually share one public IP anyway.
- **Content can identify its author.** If a student writes "I'm Lisa and …", or has a recognisable writing style, ClassPulse cannot hide that.
- **Small groups reduce anonymity.** With 3 participants, results can be guessed. Timing can also hint at authorship (e.g. a question appears right after one student typed on their phone in front of the teacher).
- **Double-vote prevention is per device.** A student who clears browser data or uses a second device can vote again. Preventing this fully would require identifying students, which ClassPulse deliberately does not do.
- **The person running the server** has database access. Choose an operator you trust — ideally your school's own server.
- **Spotify:** song searches are sent to Spotify via the teacher's Spotify account (server-side, without any student data). Spotify only sees that the teacher's app searched for a song.
- **Optional AI filter:** if configured, free-text messages are sent to the configured endpoint for a moderation check. Use a local model (e.g. Ollama) to keep data on your own server.

## No tracking

No analytics, no ads, no external fonts, scripts or CDNs. All assets are served by your own instance. Song cover images are loaded from Spotify's image CDN only for music activities.

## GDPR notes for schools

ClassPulse is built for data minimisation (Art. 5(1)(c) GDPR). The teacher account data (email, name) is personal data; the school or operator is the controller. Student contributions are, by design, not linked to identifiable persons in ClassPulse's database, but free text may still contain personal data written by students. Document the instance in your school's processing records and inform students not to write personal details.
