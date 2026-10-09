from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from collections import deque
from datetime import datetime, timezone
from math import floor
import hmac
import os
import re
import time

app = FastAPI(title="Apex Intelligence Simulation API", version="0.2.0")
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
_events = deque(maxlen=50)  # temporary memory; reset on restart or scale-out
_recent_ids = {}
_allowed_actions = {"SWEEP", "RECLAIM", "BREAKOUT", "FVG", "VWAP", "LONG_SETUP", "SHORT_SETUP", "BIAS_BULL", "BIAS_BEAR", "CONFIRMATION", "INVALIDATION"}
_allowed_tf = {"1", "3", "5", "15", "60", "240", "D"}

class RiskRequest(BaseModel):
    instrument: str
    stop_points: float = Field(gt=0)
    max_risk: float = Field(ge=0)
    estimated_fee_per_contract: float = Field(default=2, ge=0)

class TradingViewEvent(BaseModel):
    secret: str = Field(min_length=1, max_length=256)
    symbol: str = Field(min_length=1, max_length=80)
    timeframe: str = Field(min_length=1, max_length=10)
    event: str = Field(min_length=1, max_length=40)
    price: float | None = None
    bar_time: str | None = Field(default=None, max_length=80)
    event_id: str | None = Field(default=None, max_length=120)

@app.get("/health")
def health():
    return {"status": "online", "mode": "simulation", "execution": "disabled", "tradingview_webhook": "configured" if os.getenv("TRADINGVIEW_WEBHOOK_SECRET") else "not_configured"}

@app.get("/agents")
def agents():
    return {"mode": "simulation", "agents": [{"name": name, "status": "demo"} for name in ["Liquidity Scout", "Structure Analyst", "VWAP Sentinel", "Macro Observer", "Historical Quant", "Risk Guardian"]]}

@app.post("/risk/calculate")
def risk(req: RiskRequest):
    symbol = req.instrument.upper()
    if symbol not in ("NQ", "MNQ"):
        raise HTTPException(status_code=422, detail="Supported instruments: NQ, MNQ")
    per = req.stop_points * (20 if symbol == "NQ" else 2) + req.estimated_fee_per_contract
    qty = floor(req.max_risk / per)
    return {"mode": "simulation", "instrument": symbol, "risk_per_contract": round(per, 2), "max_contracts": qty, "estimated_total_risk": round(qty * per, 2), "execution": "disabled", "caveat": "Excludes slippage and gaps; not broker-enforced"}

@app.post("/webhooks/tradingview")
async def tradingview(payload: TradingViewEvent, request: Request):
    configured = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "")
    if not configured:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    if not hmac.compare_digest(payload.secret, configured):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if request.headers.get("content-length") and int(request.headers["content-length"]) > 4096:
        raise HTTPException(status_code=413, detail="Payload too large")
    symbol = payload.symbol.upper().strip()
    if not re.fullmatch(r"[A-Z0-9:_!./-]{1,80}", symbol) or not re.search(r"(?:^|:|1!|2!)(?:M?NQ)", symbol):
        raise HTTPException(status_code=422, detail="Only NQ/MNQ symbols accepted")
    event = payload.event.upper().strip()
    if event not in _allowed_actions or payload.timeframe not in _allowed_tf:
        raise HTTPException(status_code=422, detail="Unsupported event or timeframe")
    now = time.monotonic()
    for key, expiry in list(_recent_ids.items()):
        if expiry < now:
            _recent_ids.pop(key, None)
    identifier = payload.event_id or f"{symbol}:{payload.timeframe}:{event}:{payload.bar_time}"
    if identifier in _recent_ids:
        return {"accepted": True, "duplicate": True, "execution": "disabled"}
    _recent_ids[identifier] = now + 900
    entry = {"symbol": symbol, "timeframe": payload.timeframe, "event": event, "price": payload.price, "bar_time": payload.bar_time, "received_at": datetime.now(timezone.utc).isoformat()}
    _events.appendleft(entry)
    return {"accepted": True, "duplicate": False, "execution": "disabled"}

@app.get("/signals/recent")
def recent_signals():
    return {"source": "TradingView alert webhooks", "storage": "volatile", "signals": list(_events), "execution": "disabled"}
