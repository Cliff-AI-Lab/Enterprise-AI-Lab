# AgentTelegram UI/UX Package

Standalone UI/UX extraction from AgentTelegram.

This package keeps the reusable product surface:

- Telegram-like workspace shell
- room list, chat surface, composer, context drawer
- agent profile popovers
- agent status and typing states
- themes, agent personas, memory proposal UI, artifacts panel
- local mock agent runs for direct chat, mentions, and Convene

It intentionally includes only UI source and public visual assets. No server,
database, runtime worker, workspace package, or external SDK path dependency is
included.

Run it:

```bash
npm install
npm run dev
```

The app starts at `http://localhost:5183` and works without any model key or
server process. Treat `src/App.tsx`, `src/styles.css`, and `public/theme-avatars`
as the main reusable UI reference.

Runtime behavior is deliberately stubbed. The host app should own real model
calls, persistence, and streaming transport.
