# NOTES

## Now

- Topics covered-day label implemented; awaiting independent verification. Uses existing digest `date` for heading/title. Web tests: 9 passed; declared test: 62 passed; production build and live-data browser reload: passed (2026-10-16, including UTC+14). Reproduce with `node core/web/scripts/verify-topics-live.mjs core/web/node_modules/playwright/index.mjs` (requires Playwright and Chromium). Full lint reports 12 errors and 8 warnings in unchanged files; changed-file lint passes. No generated JSON changes.

## Ideas

## Questions
- ~~Which notification or page showed the 4u.ai morning-run failure, and for which date?~~
  Answered 2026-10-18: https://4u.ai/topics on 2026-10-17, read as "topics from yesterday,
  not today". No 4u run failure; the Topics heading claims today for the previous day's
  digest. The 17 Oct run built `core/data/4u/archive/news/topics/2026-10-16.json`
  (`generated_at` 2026-10-17T02:00Z, `batches_failed` 0, pushed 06:48 EEST), because
  `build_topics.py` defaults to the previous complete UTC day and refuses an unfinished
  one. Follow-ups: (a) the Topics heading names the day it covers; (b) the
  k5-security-news Cloudflare Pages deploy failure, on its own.

## For me
