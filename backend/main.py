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
_allowed_actions = {"SWEEP", "RECLAIM", "BREAKOUT", "FVG", "VWAP", "LONG_SETUP", "SHORT_SETUP", "BIAS_BULL", "BIAS_BEAR", "CONFIRMATION", "INVALIDATION", "APPROACH_LOW", "APPROACH_HIGH"}
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


# Public, source-attributed macro calendar. No trading-price data.
from urllib.request import Request as URLRequest, urlopen
from urllib.parse import quote
from xml.etree import ElementTree as ET
from datetime import timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
_macro_cache = {"until": 0, "value": None}
def _fetch_public(url):
    with urlopen(URLRequest(url, headers={"User-Agent": "FuturesIntelligenceHub/0.3 (economic-calendar-reader)", "Accept": "text/calendar, application/rss+xml, application/xml"}), timeout=7) as response:
        return response.read(750000).decode("utf-8-sig", errors="replace")

def _parse_bls_ics(raw):
    # RFC 5545 line folding
    lines = []
    for line in raw.replace("\\r\\n", "\\n").split("\\n"):
        if line.startswith((" ", "\\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    events, current = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            k, v = line.split(":", 1)
            current[k.split(";", 1)[0]] = v.replace("\\,", ",").replace("\\n", " ")
    now = datetime.now(ZoneInfo("America/New_York"))
    output = []
    for ev in events:
        rawdate = ev.get("DTSTART", "")
        try:
            if rawdate.endswith("Z"):
                dt = datetime.strptime(rawdate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo("America/New_York"))
            elif "T" in rawdate:
                dt = datetime.strptime(rawdate[:15], "%Y%m%dT%H%M%S").replace(tzinfo=ZoneInfo("America/New_York"))
            else:
                dt = datetime.strptime(rawdate[:8], "%Y%m%d").replace(tzinfo=ZoneInfo("America/New_York"))
            if now - timedelta(hours=12) <= dt <= now + timedelta(days=14):
                output.append({"title": ev.get("SUMMARY", "BLS economic release")[:160], "time_et": dt.isoformat(), "source": "U.S. Bureau of Labor Statistics", "url": "https://www.bls.gov/schedule/news_release/", "time_precision": "date" if "T" not in rawdate else "datetime"})
        except (ValueError, IndexError):
            continue
    return sorted(output, key=lambda x: x["time_et"])[:35]

def _parse_rss(raw, source):
    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item")[:20]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        published = item.findtext("pubDate", "").strip()
        if title and link.startswith("https://"):
            items.append({"title": title[:180], "url": link, "published": published, "source": source})
    return items

@app.get("/macro/brief")
def macro_brief():
    now = time.monotonic()
    if _macro_cache["value"] is not None and now < _macro_cache["until"]:
        return _macro_cache["value"]
    tasks = {
        "nq": ("https://news.google.com/rss/search?q=" + quote('("Nasdaq 100" OR "Nasdaq futures" OR "NQ futures" OR "US tech stocks") when:2d') + "&hl=en-US&gl=US&ceid=US:en", lambda x: _parse_rss(x, "Google News / publisher headlines")),
        "calendar": ("https://www.bls.gov/schedule/news_release/bls.ics", _parse_bls_ics),
        "fed": ("https://www.federalreserve.gov/feeds/press_monetary.xml", lambda x: _parse_rss(x, "Federal Reserve")),
        "bls": ("https://www.bls.gov/feed/bls_latest.rss", lambda x: _parse_rss(x, "BLS")),
    }
    results, errors = {}, []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {name: pool.submit(_fetch_public, url) for name, (url, _) in tasks.items()}
        for name, (_, parser) in tasks.items():
            try:
                results[name] = parser(futures[name].result(timeout=9))
            except Exception:
                results[name] = []
                errors.append(name)
    value = {"fetched_at": datetime.now(timezone.utc).isoformat(), "timezone": "America/New_York", "upcoming_bls": results["calendar"], "latest_releases": (results["fed"] + results["bls"])[:12], "nq_headlines": results["nq"][:20], "unavailable_sources": errors, "disclaimer": "Publisher headlines via Google News RSS plus official-source macro releases. News may be delayed or incomplete. Verify primary reporting; not a futures price feed or trading signal."}
    _macro_cache.update(until=now+900, value=value)
    return value
