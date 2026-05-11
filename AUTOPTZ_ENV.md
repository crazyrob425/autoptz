# AutoPTZ Environment Setup

Place authentication keys and other runtime environment variables in a file at:

Windows: `%USERPROFILE%\\.autoptz\\.env`
Linux/macOS: `~/.autoptz/.env`

Example `.env` contents:

OPENAI_API_KEY=sk-REPLACE_WITH_YOUR_KEY
# or if you prefer Anthropic:
# ANTHROPIC_API_KEY=claude-REPLACE_WITH_YOUR_KEY

Google OAuth credentials are expected at:
`%USERPROFILE%\\.autoptz\\cloud\\google_credentials.json`

Notes:
- The app will load `~/.autoptz/.env` automatically on startup.
- Keep keys private. Do not commit `.env` to version control.
