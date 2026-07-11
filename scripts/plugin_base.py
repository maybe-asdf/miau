class ServerPlugin:
    def __init__(self, server):
        """
        server: Reference to the server object containing:
          - clients: set of active websockets
          - senders: set of active usernames
          - user_map: dict of username -> websocket
          - config: server configuration dict
        """
        self.server = server

    async def on_join(self, username, websocket):
        pass

    async def on_leave(self, username):
        pass

    async def on_message(self, username, message_content, websocket) -> bool:
        """
        Called when a message is received.
        Return True to intercept/consume the message, preventing normal routing.
        """
        return False

    async def on_command(self, username, command, args, websocket) -> bool:
        """
        Called when a command starts with '>'.
        Return True to intercept/consume the command, preventing normal routing.
        """
        return False
