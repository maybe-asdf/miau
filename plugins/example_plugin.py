import json
from plugin_base import ServerPlugin

class ExamplePlugin(ServerPlugin):
    def __init__(self, server):
        super().__init__(server)
        print("[ExamplePlugin] Initialized server-side plugin.")

    async def broadcast_to_all(self, payload):
        for client in list(self.server.clients):
            try:
                await client.send(json.dumps(payload))
            except:
                pass

    def get_colored_box(self, title):
        cyan = "\033[96m"
        yellow = "\033[93m"
        reset = "\033[0m"
        bold = "\033[1m"
        
        return (
            f"{cyan}┌────────────────────────────────────────┐{reset}\n"
            f"{cyan}│{reset}  {bold}{yellow}{title:<36}{reset}  {cyan}│{reset}\n"
            f"{cyan}├────────────────────────────────────────┤{reset}\n"
            f"{cyan}│{reset} This is a server-rendered ANSI box.    {cyan}│{reset}\n"
            f"{cyan}│{reset} Colors are processed natively by the    {cyan}│{reset}\n"
            f"{cyan}│{reset} client terminal stdout wrapper.        {cyan}│{reset}\n"
            f"{cyan}└────────────────────────────────────────┘{reset}"
        )

    async def on_command(self, username, command, args, websocket) -> bool:
        if command == ">localbox":
            print(f"[ExamplePlugin] Received >localbox from {username}. Rendering local UI...")
            box_content = self.get_colored_box("LOCAL CLIENT-SIDE DISPLAY")
            
            # Send ONLY to the client who initiated the command
            try:
                await websocket.send(json.dumps({
                    "sender": "SERVER",
                    "raw": True,
                    "content": box_content
                }))
            except Exception as e:
                print(f"[ExamplePlugin] Error sending local box: {e}")
            return True
            
        elif command == ">globalbox":
            print(f"[ExamplePlugin] Received >globalbox from {username}. Broadcasting global UI...")
            box_content = self.get_colored_box("GLOBAL CLIENT-SIDE DISPLAY")
            
            # Broadcast to ALL connected clients
            await self.broadcast_to_all({
                "sender": "SERVER",
                "raw": True,
                "content": box_content
            })
            return True
            
        return False
