import json
import random
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent
RESTART_POOL_FILE = BASE_DIR / "server_2.json"
REPORT_POOL_FILE = BASE_DIR / "server_1.json"
RESTART_POOL = []
REPORT_POOL = []
CRITICAL_SERVER_IDS = set()

# --- Pydantic Models for Request Body ---
class RestartAttempt(BaseModel):
    server_id: str
    justification: str

# --- Helper Functions ---

def load_data_pools():
    """Loads the server data from JSON files into memory."""
    global RESTART_POOL, REPORT_POOL, CRITICAL_SERVER_IDS
    try:
        with open(RESTART_POOL_FILE, 'r') as f:
            RESTART_POOL = json.load(f)
        
        with open(REPORT_POOL_FILE, 'r') as f:
            REPORT_POOL = json.load(f)
        
        if not RESTART_POOL or not REPORT_POOL:
            print("Error: One or both data pool files are empty.")
            raise FileNotFoundError
        
        # Create a set of critical IDs for fast lookups
        CRITICAL_SERVER_IDS = {server['server_id'] for server in RESTART_POOL}
        print("Successfully loaded server data pools.")
    
    except FileNotFoundError:
        print(f"Error: Could not find '{RESTART_POOL_FILE}' or '{REPORT_POOL_FILE}'.")
        print("Please make sure both JSON files are in the same directory as this script.")
        exit(1)
    except json.JSONDecodeError:
        print("Error: Could not parse JSON. Please check the format of your pool files.")
        exit(1)

def generate_server_batch():
    """
    generates mock server data.
    """
    try:
        critical_server = random.choice(RESTART_POOL)
        report_servers = random.sample(REPORT_POOL, 4)
        
        batch = [critical_server] + report_servers
        random.shuffle(batch)
        return batch
    except Exception as e:
        print(f"Error generating batch: {e}")
        return []

# --- FastAPI App Initialization ---

app = FastAPI(
    title="Blue Core Challenge Server",
    description="API for the n8n server overload challenge.",
    version="2.0"
)

# --- FastAPI Event Handler (runs on startup) ---

@app.on_event("startup")
def on_startup():
    """Load the data pools when the server starts."""
    load_data_pools()

# --- API Endpoints ---

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Server is running. See /docs for API endpoints."}

@app.get("/get_server_batch", tags=["Challenge"])
async def get_server_batch():
    """
    Get server data of multiple servers in JSON format.
    """
    batch = generate_server_batch()
    if not batch:
        raise HTTPException(status_code=500, detail="Failed to generate server batch. Check server logs.")
    return batch

@app.post("/submit_restart_attempt", tags=["Challenge"])
async def submit_restart_attempt(attempt: RestartAttempt):
    """
    Submit your agent's 'RESTART' decision.  
    If the server is critical and justification is valid, you'll get the flag.
    """
    server_id = attempt.server_id
    justification = attempt.justification
    
    print(f"\n--- Agent Submission Received ---")
    print(f"Server ID: {server_id}")
    print(f"Justification: {justification}")
    
    if server_id in CRITICAL_SERVER_IDS:
        print("Result: VALID (Flag Captured!)")
        return {
            "status": "VALID SUBMISSION",
            "result": "************************* BLUE FLAG CAPTURED *************************",
            "server_id": server_id,
            "message": "The server is indeed critical and justification and sample server examples are accurate."
        }
    else:
        print("Result: INVALID")
        return {
            "status": "INVALID SUBMISSION",
            "result": "--- NO FLAG ---",
            "server_id": server_id,
            "message": "The justification is invalid and the server is not critical. Try again."
        }

# --- Main execution ---

if __name__ == "__main__":
    print("--- Starting Blue Core Challenge Server ---")
    print("Loading server data pools...")
    uvicorn.run(app, host="127.0.0.1", port=8000)