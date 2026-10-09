# TradingView → Apex Intelligence (manual execution only)

Webhook URL:
`https://apex-backend-production-0c34.up.railway.app/webhooks/tradingview`

## Setup
1. In Railway → apex-intelligence → apex-backend → Variables, copy the value of `TRADINGVIEW_WEBHOOK_SECRET`. **Never commit or share it publicly.** The value is a shared secret for authenticating alerts, not a TradingView account credential.
2. In TradingView create a chart alert and enable **Webhook URL**. Paste the URL above.
3. In **Message**, paste the JSON below and replace `PASTE_SECRET_FROM_RAILWAY` with your Railway secret. TradingView sends this as the alert body. Be aware that the secret is present in TradingView's alert configuration; restrict access to your TradingView account.
4. Use a supported NQ/MNQ chart symbol and choose a relevant timeframe. The message below records a manually selected event label. It **does not detect** liquidity sweeps, FVGs, or 4h bias by itself; use an actual Pine condition before interpreting it as a strategy signal.
5. Create the alert. When it fires, open the Apex Trading City → **Market Event Feed**. It refreshes approximately every 15 seconds.

```json
{
  "secret": "PASTE_SECRET_FROM_RAILWAY",
  "symbol": "{{ticker}}",
  "timeframe": "{{interval}}",
  "event": "CONFIRMATION",
  "price": {{close}},
  "bar_time": "{{time}}",
  "event_id": "{{ticker}}-{{interval}}-{{time}}-CONFIRMATION"
}
```

Supported event labels: `SWEEP`, `RECLAIM`, `BREAKOUT`, `FVG`, `VWAP`, `LONG_SETUP`, `SHORT_SETUP`, `BIAS_BULL`, `BIAS_BEAR`, `CONFIRMATION`, `INVALIDATION`. Supported intervals: 1, 3, 5, 15, 60, 240, D. TradingView's `{{ticker}}` must identify an NQ/MNQ contract. Some chart types or custom scripts may need a hardcoded symbol or timeframe.

## Important limits
- This is **alert ingestion**, not direct TradingView account access or continuous real-time quotes.
- No trades are placed; alerts are informational and are not financial advice.
- The initial feed is kept in application memory only (up to 50 events) and is cleared by restart or redeployment. Multiple backend replicas would not share events. Do not use it as a permanent trading journal.
- The event feed is publicly readable at `GET /signals/recent`. Do not include personal or account information in alert messages. Authentication and persistent storage are required before handling private trading data.
- The backend accepts only authenticated NQ/MNQ event messages. Rotate the shared secret if compromised.
- TradingView webhooks may require a qualifying subscription, two-factor authentication, and successful public HTTPS access; check current TradingView requirements in your account.
