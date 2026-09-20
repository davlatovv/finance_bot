# T1: Hosting, BotFather and environment setup

Deliverable of task T1 in [MINIAPP_PLAN.md](MINIAPP_PLAN.md).

## 1. Public HTTPS hostname (no domain)

Telegram opens Mini Apps only over HTTPS with a valid certificate.

**Chosen: `sslip.io`.** Any hostname of the form `<a-b-c-d>.sslip.io` resolves to `a.b.c.d`, so Caddy can obtain a Let's Encrypt certificate for it with no DNS setup.

1. Get the VPS public IPv4, e.g. `203.0.113.5`.
2. `PUBLIC_HOST=203-0-113-5.sslip.io`
3. Open ports **80** and **443** (80 is needed for the ACME HTTP challenge) in the VPS firewall / security group. Nothing else needs to be public; Postgres and the API stay on the internal Docker network.
4. Verify before deploying: `dig +short 203-0-113-5.sslip.io` returns the VPS IP.

Caveats:
- The IP must be static. If it changes, update `PUBLIC_HOST` and re-set the BotFather URL.
- Let's Encrypt rate-limits per registered domain (`sslip.io` is shared). If issuance is rate-limited, fall back to **DuckDNS** (free `yourname.duckdns.org` + a cron/API call to update the IP). Only `PUBLIC_HOST` changes.
- Later, with a real domain: point an A record at the VPS and change `PUBLIC_HOST`. Nothing else changes.

## 2. BotFather steps (manual, done by the bot owner)

Run after the first deploy, once `https://PUBLIC_HOST` serves the app.

1. `/mybots` → choose the bot → **Bot Settings → Menu Button → Configure menu button** → URL `https://PUBLIC_HOST`, title `Open`.
   (The launcher bot also sets this programmatically with `set_chat_menu_button`; doing it in BotFather is the fallback.)
2. Optional: `/newapp` to register a Direct Link Mini App (`t.me/<bot>/<app>`), same URL. Not required for menu-button launch.
3. Keep the bot token in `.env` only; never in the frontend or the repo. If it was ever committed or pasted anywhere, rotate it with `/revoke`.
4. `/setdomain` is only for the Login Widget; not needed for Mini Apps.

## 3. Environment variables

Also captured in `.env.example`. Compose passes them to the containers listed.

| Variable | Used by | Notes |
|---|---|---|
| `PUBLIC_HOST` | caddy, bot | Hostname without scheme. Bot builds `https://$PUBLIC_HOST` for the WebApp button |
| `BOT_TOKEN` | api, bot | api uses it to verify `initData` HMAC |
| `INIT_DATA_MAX_AGE_SECONDS` | api | Reject older `auth_date`; default 86400 |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | db, api | Strong random password; DB not exposed publicly |
| `DATABASE_URL` | api | `postgresql+asyncpg://user:pass@db:5432/dbname` |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | api | Same as today |
| `WHISPER_MODEL` | api | `turbo` (~1-2 GB RAM) vs `small`/`base`; see below |
| `WHISPER_TEMP_DIR` | api | Temp audio; cleaned after each request |
| `AUTO_CLEANUP_MONTHS` | api | `0` = disabled (default). Old bot deleted data after 6 months |
| `RATE_LIMIT_*` | api | Per-user limits for `/ai/*`; port defaults from `src/security/rate_limiter.py` |
| `LOG_LEVEL` | api, bot | default `INFO` |

Removed vs. today: `DB_PATH` (SQLite) and the `data/finance_bot.db` volume; replaced by a `pgdata` volume.

## 4. VPS sizing and the Whisper decision

Stack memory estimate: Postgres ~150-300 MB, API ~200 MB, Caddy + bot ~100 MB, plus Whisper.

| Option | Extra RAM | Trade-off |
|---|---|---|
| Local `turbo` | ~1.5-2 GB | Best local accuracy, slow on CPU, needs ≥ 4 GB VPS |
| Local `small` | ~0.5-1 GB | Fits 2 GB VPS, weaker on Uzbek/Russian mix |
| Hosted STT API | ~0 | Needs an extra API key and sends audio off-server |

**Recommendation:** start with local `small` on a 2-4 GB VPS to keep parity with the current no-external-STT design; revisit if accuracy is poor. This must be confirmed before T8. Compose memory limit for `api` should be raised from the current 1 GB accordingly.

## 5. Checklist to close T1

- [ ] VPS IP known, ports 80/443 open, `PUBLIC_HOST` decided
- [ ] `dig` resolves `PUBLIC_HOST` to the VPS
- [ ] Whisper option chosen (local `turbo` / local `small` / hosted)
- [ ] Auto-cleanup decision confirmed (default: disabled)
- [ ] BotFather menu button configured (after first deploy)
