from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
from math import floor

app = FastAPI(title="Apex Intelligence Simulation API", version="0.1.0")
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

class RiskRequest(BaseModel):
    instrument: str
    stop_points: float = Field(gt=0)
    max_risk: float = Field(ge=0)
    estimated_fee_per_contract: float = Field(default=2, ge=0)

@app.get("/health")
def health():
    return {"status": "online", "mode": "simulation", "execution": "disabled"}

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
