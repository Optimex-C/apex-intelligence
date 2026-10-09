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


## For manual TradingView + Tradovate traders
An initial Pine Script indicator is in [tradingview/Apex_Manual_Setup_Alerts.pine](tradingview/Apex_Manual_Setup_Alerts.pine). This is **not a proven strategy**. It watches the prior *closed* 4h EMA bias and looks for a 5m wick sweep/reclaim of the prior *closed* 15m high/low.

1. Open your NQ or MNQ chart on TradingView and choose the **5-minute** timeframe.
2. Open **Pine Editor**, paste the entire indicator code, **Save**, and **Add to chart**.
3. Choose **Create alert** and select this indicator's `Apex LONG_SETUP` condition. Use **Once Per Bar Close**.
4. Enable the **Webhook URL** and enter the endpoint at the top of this guide.
5. In the alert **Message**, replace `REPLACE_WITH_RAILWAY_SECRET` with the secret found in your Railway backend service's Variables tab. TradingView might prepopulate the JSON message; verify that it remains valid JSON.
6. Create a second alert using `Apex SHORT_SETUP` and the same webhook URL.
7. Confirm the event appears on the Apex Intelligence website. **Neither TradingView nor the website will place trades** through these alerts.

Do not publish an indicator containing the secret. Store your TradingView account and alert configuration securely. An indicator added to a chart is not automatically connected until you explicitly create the alerts.

### Tradovate/Apex account data
The existing TradingView Trading Panel connection is for chart-based trading and does not grant this app Tradovate API authorization. Position, fills, P&L and account-rule data are **not connected**. A separate, authorized read-only integration (if your account and vendor permissions allow it) is required. Do not send credentials or API tokens in chat or GitHub.
