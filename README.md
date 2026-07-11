``` 
        _           
  _ __ (_)__ _ _  _ 
 | '  \| / _` | || |
 |_|_|_|_\__,_|\_,_|
                                               
 
```
## An open-source chat app, soon to be encrypted designed for freedom and privacy.
It's not a work of art as of now, since it only is in the alpha stages, but it's gonna
get better as time goes by. For support join server ilovefemboys.duckdns.org (may be unactive)
or dm maybe.asdf on discord. 
# VERSION 4 OUR BIGGEST UPDATE YET
# Installation (Client)
## W\*ndows
- Some day.. maybe some day.. w\*nd\*ws sucks anyways
## Linux / MacOS(?)
- First install git, which i assume you already have
- Clone this repo by running this command
```
git clone https://github.com/maybe-asdf/chaasnyx/
```
- CD into the cloned repo, and run `python3 -m venv venv` then `source venv/bin/activate` and finally `pip install -r requirements.txt`.
- Now do `./client.sh`. (if that doesnt run try `source venv/bin/activate` then `python3 scripts/client.py)
# Installation (Server)
## Linux 
- First install git, which i assume you already have
- Clone this repo by running this command
```
git clone https://github.com/maybe-asdf/chaasnyx/
```
- CD into the cloned repo, and run `python3 -m venv venv` then `source venv/bin/activate` and finally `pip install -r requirements.txt`.
- Now do `./server.sh`. (if that doesnt run try `source venv/bin/activate` then `python3 scripts/server.py)
### Port forwarding
- More details on this can be accessed on probably your router providers website, but for the service to be accessed outside of your home network you need to forward port 6741 by default.
# Roadmap
- Commands [✅]
- Whisper [✅]
- Chat history [✅]
- Role system [✅]
- Transport Encryption (WSS) [✅]
- Passwords for privileged usernames [✅]
- Plugin system [✅] (you can see example plugins in the plugins/ folder)
- Web UI [broken] (maybe vibecoded but who cares) (also probably a security risk)


# User Management & Roles

Chaasnyx implements a simple role permission system. The three available roles are:
- `admin`: Full administrative control (stopping the server, clearing server logs).
- `mod`: Channel moderator control (kicking users, clearing screen).
- `user`: Standard participant.

### CLI User Administration

Run these command utility options on the server using Python:

- **Add or Update a User**:
  ```bash
  python3 scripts/server.py --add-user <username> --role <admin/mod/user>
  ```
- **Delete a User**:
  ```bash
  python3 scripts/server.py --delete-user <username>
  ```
- **List All Registered Users**:
  ```bash
  python3 scripts/server.py --list-users
  ```

### Chat Commands
- `>stop`: Stops the chat server (Admins only).
- `>clearhistory`: Clears stored message history on the server database (Admins only).
- `>kick <username>`: Disconnects the selected user immediately (Admins & Moderators only).
- `>clearscreen`: Signals all active clients to clear their screen layouts (Admins & Moderators only).
- `>list`: Shows a list of all active online users.
- `>msg <username> <message>`: Sends a private whisper to the target user.

---

# Plugin System

The chat server includes a dynamic plugin scanner. All plugin files are placed in the `plugins/` directory and loaded on server startup.

### Developing Plugins

Plugins must subclass `ServerPlugin` from `scripts/plugin_base.py`. Developers can override the following event hook signatures:

```python
from plugin_base import ServerPlugin

class MyPlugin(ServerPlugin):
    async def on_join(self, username, websocket):
        """Called when a user logs in."""
        pass

    async def on_leave(self, username):
        """Called when a user disconnects."""
        pass

    async def on_message(self, username, message_content, websocket) -> bool:
        """Called when a text message is sent. Return True to block/consume it."""
        return False

    async def on_command(self, username, command, args, websocket) -> bool:
        """Called on commands starting with '>'. Return True to block/consume it."""
        return False
```

### Dynamic Console Output Routing
Plugins can target how outputs are displayed:
- **Server console**: Use standard `print()` functions in the plugin code.
- **Single Client (Local)**: Send messages directly to the client's `websocket` parameter.
- **All Clients (Global)**: Loop over `self.server.clients` to broadcast content.

By utilizing the `"raw": true` JSON parameter, server plugins can bypass standard chat bubbles and render custom ANSI graphics/panels on compatible terminals natively.

### Included Plugins
- **Example Plugin** (`plugins/example_plugin.py`): Demonstrates intercepting custom commands (`>localbox` & `>globalbox`) and drawing borders and layouts.
- **Anti-Spam Plugin** (`plugins/antispam.py`): Automatically blocks messages and mutes users for 10 seconds if they send more than 5 messages within 3 seconds.


