from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio, uuid, random
from typing import Dict, List

router = APIRouter(prefix="/battle", tags=["battle"])

# In-memory matchmaking queue and rooms
waiting_players: List[dict] = []
rooms: Dict[str, dict] = {}

@router.post("/find")
async def find_battle(device_id: str):
    """Add player to matchmaking queue. Returns room_id when matched."""
    room_id = None

    # Check if someone is waiting
    if waiting_players:
        opponent = waiting_players.pop(0)
        room_id = str(uuid.uuid4())[:8]
        rooms[room_id] = {
            "players": [opponent["device_id"], device_id],
            "scores": {opponent["device_id"]: 0, device_id: 0},
            "current_question": 0,
            "status": "ready",
        }
        return {"status": "matched", "room_id": room_id, "opponent_id": opponent["device_id"]}
    else:
        # Add to queue
        waiting_players.append({"device_id": device_id})
        return {"status": "waiting", "room_id": None}


@router.get("/status/{room_id}")
async def battle_status(room_id: str):
    """Poll for room status (for players waiting for match)."""
    if room_id not in rooms:
        # Check if still in queue
        return {"status": "waiting"}
    return {"status": "ready", "room": rooms[room_id]}


@router.websocket("/ws/{room_id}")
async def battle_websocket(websocket: WebSocket, room_id: str, device_id: str):
    await websocket.accept()

    if room_id not in rooms:
        await websocket.send_json({"type": "error", "message": "Room not found"})
        await websocket.close()
        return

    room = rooms[room_id]

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "answer":
                choice = data.get("choice")  # "a" or "b"
                question_idx = data.get("question_idx", 0)

                # Simple scoring: majority wins
                # In real implementation, track both players' answers
                correct = random.choice([True, False])
                if correct:
                    room["scores"][device_id] = room["scores"].get(device_id, 0) + 1

                await websocket.send_json({
                    "type": "answer_result",
                    "correct": correct,
                    "your_score": room["scores"].get(device_id, 0),
                })

                if question_idx >= 9:  # Last question
                    scores = room["scores"]
                    player_score = scores.get(device_id, 0)
                    opponent_id = [p for p in room["players"] if p != device_id][0]
                    opponent_score = scores.get(opponent_id, 0)

                    await websocket.send_json({
                        "type": "game_over",
                        "your_score": player_score,
                        "opponent_score": opponent_score,
                        "winner": device_id if player_score > opponent_score else opponent_id,
                    })
                    break
    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        if room_id in rooms:
            del rooms[room_id]
