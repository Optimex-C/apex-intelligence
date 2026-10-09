# Apex Intelligence — Trading City

Simulation-only prototype of a 3D financial research command center. No brokerage connection, live quotes, predictive claims or order execution.

## Architecture
- `frontend/`: Next.js 15 + React Three Fiber interactive 3D metropolis; five clickable districts and risk calculator.
- `backend/`: FastAPI health, demo agents and fee-inclusive risk calculator.

## Local development
```sh
cd frontend && npm install && npm run dev
```
In another terminal:
```sh
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
```
Frontend: http://localhost:3000; backend docs: http://localhost:8000/docs.

## Railway
Deploy frontend and backend as separate services from this repo. Set root directories to `/frontend` and `/backend`, respectively. Each has its own Dockerfile. Add frontend variable `NEXT_PUBLIC_API_URL=https://YOUR-API-DOMAIN` and backend variable `ALLOWED_ORIGINS=https://YOUR-FRONTEND-DOMAIN`, then redeploy both.

## Safety
This is not financial advice or a verified strategy. UI demo data is fictional. Risk calculator excludes slippage and gaps; frontend excludes fees while backend supports estimated fees. No authentication or trading webhook endpoint has been added yet; do not expose private trading records or credentials. Keep the repository private before adding proprietary strategies.
