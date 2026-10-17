# NOTES

## Now

- Topics covered-day label awaits independent verification. Uses existing digest `date` for heading/title. Rework exposes web verification through the existing declared host check: `run_declared_check({"check":"test","args":["-s","core/web/tests","-v"]})`. Passed all three checks: 9 web tests; 4 Topics tests reject the old fixed labels in a temporary copy; production build renders live date 2026-10-16 in heading/title and after reload in UTC+14. Plain declared `test` also passed 62 Python tests. Playwright is pinned in the web dev dependencies; setup and selective check commands are in README. No generated JSON changes.

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
