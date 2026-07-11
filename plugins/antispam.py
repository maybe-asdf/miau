import time
import json
from plugin_base import ServerPlugin

class AntiSpamPlugin(ServerPlugin):
    def __init__(self, server):
        super().__init__(server)
        self.history = {}       # username -> list of floats (timestamps)
        self.muted_until = {}   # username -> float (timestamp)
        print("[AntiSpamPlugin] Loaded.")

    async def broadcast_to_all(self, payload):
        for client in list(self.server.clients):
            try:
                await client.send(json.dumps(payload))
            except:
                pass

    async def on_message(self, username, message_content, websocket) -> bool:
        current_time = time.time()

        # Check if currently muted
        mute_exp = self.muted_until.get(username, 0)
        if current_time < mute_exp:
            remaining = int(mute_exp - current_time)
            try:
                await websocket.send(json.dumps({
                    "sender": "SERVER",
                    "content": f"🔇 You are muted for spamming. Please wait {remaining} more seconds."
                }))
            except:
                pass
            return True

        # Clean up history for messages older than 3 seconds
        timestamps = self.history.get(username, [])
        timestamps = [t for t in timestamps if current_time - t <= 3.0]
        
        # Add current timestamp
        timestamps.append(current_time)
        self.history[username] = timestamps

        # If user exceeds threshold: 5 messages in 3 seconds
        if len(timestamps) > 5:
            self.muted_until[username] = current_time + 10.0
            
            try:
                await websocket.send(json.dumps({
                    "sender": "SERVER",
                    "content": "🔇 You have been muted for 10 seconds due to spamming."
                }))
            except:
                pass

            await self.broadcast_to_all({
                "sender": "SERVER",
                "content": f"⚠️ {username} has been muted for 10 seconds for spamming."
            })
            return True

        return False
