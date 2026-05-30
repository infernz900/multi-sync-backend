from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import time

app = FastAPI()

# Stores active connections grouped by the user's account ID/Email
# Structure: { "user@email.com": [websocket1, websocket2] }
active_sessions = {}

# Stores the current playback state for each account
# Structure: { "user@email.com": {"action": "PAUSE", "trackUrl": "", "positionMs": 0, "serverTime": 0} }
room_states = {}

@app.websocket("/sync/{account_id}")
async def websocket_endpoint(websocket: WebSocket, account_id: str):
    await websocket.accept()
    
    # If this is the first device logging in, create a room for it
    if account_id not in active_sessions:
        active_sessions[account_id] = []
        room_states[account_id] = {
            "action": "PAUSE",
            "trackUrl": "",
            "positionMs": 0,
            "serverTime": time.time() * 1000
        }
        
    active_sessions[account_id].append(websocket)
    
    # Instantly send the new device the current playback state so it can catch up
    await websocket.send_text(json.dumps(room_states[account_id]))

    try:
        while True:
            # Wait for a play/pause/seek command from any phone
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # Update the central room state
            room_states[account_id].update(payload)
            room_states[account_id]["serverTime"] = time.time() * 1000 
            
            # Broadcast the new state to ALL phones logged into this account
            for client in active_sessions[account_id]:
                await client.send_text(json.dumps(room_states[account_id]))
                
    except WebSocketDisconnect:
        # If a phone disconnects, remove it from the room
        active_sessions[account_id].remove(websocket)
        if len(active_sessions[account_id]) == 0:
            del active_sessions[account_id]
            del room_states[account_id]
