ver = "v000003"
print(fr"""
        _           
  _ __ (_)__ _ _  _ 
 | '  \| / _` | || |
 |_|_|_|_\__,_|\_,_|
   {ver} server                       
      """)
def log(thing):
    print(thing)
log("Importing asyncio and sys")
import asyncio
import sys
import os
import ssl
import subprocess
import importlib.util
import glob
log("Importing json and toml")
import json
import toml
import hashlib
import secrets
import getpass
import argparse
from collections import deque
log("Importing websockets")
from websockets.asyncio.server import serve
log("Finished importing")

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading users: {e}")
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        log(f"Error saving users: {e}")

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    iterations = 100000
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hashed.hex(), salt.hex()

def verify_password(username: str, password: str) -> bool:
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    stored_hash = user.get("password_hash")
    stored_salt = user.get("salt")
    if not stored_hash or not stored_salt:
        return False
    try:
        salt = bytes.fromhex(stored_salt)
        iterations = 100000
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return hashed.hex() == stored_hash
    except Exception:
        return False

def is_admin(username: str) -> bool:
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    return "admin" in user.get("roles", [])

def is_mod(username: str) -> bool:
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    roles = user.get("roles", [])
    return "mod" in roles or "admin" in roles

clients = set()
senders = set()
user_map = {} 
plugins = []

def load_plugins():
    global plugins
    plugins = []
    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)
        log("Created 'plugins' directory.")
        
    plugin_files = glob.glob(os.path.join(plugins_dir, "*.py"))
    
    class ServerWrapper:
        def __init__(self):
            self.clients = clients
            self.senders = senders
            self.user_map = user_map
            self.config = config
            
    server_wrapper = ServerWrapper()
    
    for file_path in plugin_files:
        module_name = os.path.basename(file_path)[:-3]
        if module_name == "__init__":
            continue
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            from plugin_base import ServerPlugin
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, ServerPlugin) and obj is not ServerPlugin:
                    plugin_instance = obj(server_wrapper)
                    plugins.append(plugin_instance)
                    log(f"Loaded plugin class: {name} from {file_path}")
        except Exception as e:
            log(f"Error loading plugin from {file_path}: {e}")
with open("server.toml") as f:
     config = toml.loads(f.read())
persist_chat = config["chat_history"]["persist"]
if persist_chat:
    try:
        with open("server_history.txt") as f:
            chat_history = deque(json.load(f), maxlen=config["chat_history"]["limit"])
    except FileNotFoundError:
        chat_history = deque([], maxlen=config["chat_history"]["limit"])
else:
    chat_history = deque([], maxlen=config["chat_history"]["limit"])
log("Defining..")
async def handler(websocket):
    global chat_history
    try:
        join_msg_string = await websocket.recv()
        join_msg = json.loads(join_msg_string)
    except Exception as e:
        log(f"Invalid connection attempt: {e}")
        return

    sender_name = join_msg.get("sender")
    if join_msg.get("content") != "join;" or not sender_name:
        log(f"Someone tried to log in without a valid content. Denied access")
        try:
            await websocket.send(json.dumps({"status": "error", "message": "Invalid authentication/username."}))
        except:
            pass
        return

    users = load_users()
    if sender_name in users:
        try:
            await websocket.send(json.dumps({"status": "auth_required"}))
            auth_response_string = await websocket.recv()
            auth_response = json.loads(auth_response_string)
            password = auth_response.get("password", "")
            if not verify_password(sender_name, password):
                log(f"Failed authentication attempt for {sender_name}")
                await websocket.send(json.dumps({"status": "error", "message": "Invalid password. We are done here."}))
                return
        except Exception as e:
            log(f"Authentication exception for {sender_name}: {e}")
            try:
                await websocket.send(json.dumps({"status": "error", "message": "Authentication failed."}))
            except:
                pass
            return
    
    if sender_name in senders:
        log(f"Someone tried to log in by the taken username of {sender_name}. Denied access")
        try:
            await websocket.send(json.dumps({"status": "error", "message": "Taken username. We are done here."}))
        except:
            pass
        return

    try:
        await websocket.send(json.dumps({"status": "ok"}))
    except Exception as e:
        log(f"Failed to send OK status to {sender_name}: {e}")
        return

    senders.add(sender_name)
    clients.add(websocket)
    user_map[sender_name] = websocket
    
    # Notify plugins
    for plugin in plugins:
        try:
            await plugin.on_join(sender_name, websocket)
        except Exception as e:
            log(f"Plugin error in on_join: {e}")

    # join message
    for client in clients.copy():
        try:
            await client.send(f"- {sender_name} - just joined -")
        except:
            clients.discard(client)
    for i in list(chat_history):
        await websocket.send(json.dumps(i))
    try:
        async for message_string in websocket:
            message = json.loads(message_string)
            message_content = message["content"]
            sender = message["sender"]

            # Notify plugins of message
            intercepted = False
            for plugin in plugins:
                try:
                    if await plugin.on_message(sender, message_content, websocket):
                        intercepted = True
                        break
                except Exception as e:
                    log(f"Plugin error in on_message: {e}")
            if intercepted:
                continue

            if message_content and message_content[0] == ">":
                command = message_content.split(" ")
                cmd_name = command[0]
                cmd_args = command[1:]
                
                # Notify plugins of command
                intercepted_cmd = False
                for plugin in plugins:
                    try:
                        if await plugin.on_command(sender, cmd_name, cmd_args, websocket):
                            intercepted_cmd = True
                            break
                    except Exception as e:
                        log(f"Plugin error in on_command: {e}")
                if intercepted_cmd:
                    continue

                if command[0]== ">list":
                    await websocket.send(json.dumps({"sender": "SERVER", "content": str(senders)}))
                elif command[0] == ">help":
                    await websocket.send(json.dumps({"sender": "SERVER", "content": "Commands:"}))
                    await websocket.send(json.dumps({"sender": "SERVER", "content": ">msg username content- messages another user"}))
                    await websocket.send(json.dumps({"sender": "SERVER", "content": ">list - lists all active users"}))
                    await websocket.send(json.dumps({"sender": "SERVER", "content": ">stop - stops the server (only can be used by admins)"}))
                    await websocket.send(json.dumps({"sender": "SERVER", "content": ">kick username - kicks someone (mods and admins)"}))
                    await websocket.send(json.dumps({"sender": "SERVER", "content": ">clearhistory - clears chat history ON THE SERVER! (admin only)"}))
                    await websocket.send(json.dumps({"sender": "SERVER", "content": ">clearscreen - clears screen for all active clients (mods and admins)"}))

                elif command[0] == ">kick":
                                if is_mod(sender) and len(command) > 1:
                                    target = command[1]
                                    target_ws = user_map.get(target)
                                    if target_ws:
                                        await target_ws.send("You have been kicked.")
                                        await target_ws.close()
                                        log(f"{sender} kicked {target}")
                                    else:
                                        await websocket.send(json.dumps({"sender": "SERVER", "content": "User not found."}))
                                else:
                                    await websocket.send(json.dumps({"sender": "SERVER", "content": "Usage: >kick username (only can be used by mods)"}))
                elif command[0] == ">clearhistory":
                                if is_admin(sender):
                                    chat_history = deque([], maxlen=config["chat_history"]["limit"])
                                    await websocket.send(json.dumps({"sender": "SERVER", "content": "OK"}))
                                else:
                                    await websocket.send(json.dumps({"sender": "SERVER", "content": "Who do you think you are? Insufficient permissions."}))
                elif command[0] == ">clearscreen":
                                if is_mod(sender):
                                    for client in clients.copy():
                                        try:
                                            await client.send(json.dumps({"sender": "SERVER", "action": "clear"}))
                                        except:
                                            pass
                                else:
                                    await websocket.send(json.dumps({"sender": "SERVER", "content": "Who do you think you are? Insufficient permissions."}))
                elif command[0] == ">msg":
                    if len(command) < 3:
                        await websocket.send(json.dumps({"sender": "SERVER", "content": "Usage: >msg username message"}))
                    else:
                        target = command[1]
                        msg = " ".join(command[2:])
                        target_ws = user_map.get(target)
                        if target_ws:
                            await target_ws.send(json.dumps({"sender": f"[whisper from {sender}]", "content": msg}))
                            await websocket.send(json.dumps({"sender": f"[you -> {target}]", "content": msg}))
                        else:
                            await websocket.send(json.dumps({"sender": "SERVER", "content": "User not found"}))
                elif command[0] == ">stop":
                    if is_admin(sender):
                        for client in clients.copy():
                            try:
                                await client.send(json.dumps({"sender": "SERVER", "content": "Server stopping!"}))
                            except:
                                pass
                    else:
                        await websocket.send(json.dumps({"sender": "SERVER", "content": "Who do you think you are? Insufficient permissions."}))
                else:
                    await websocket.send(json.dumps({"sender": "SERVER", "content": "Unknown command. Try >help"}))
            else:
                chat_history.append({"sender": sender, "content": message_content})
                if persist_chat:
                    with open("server_history.txt", "w") as f:
                        json.dump(list(chat_history), f)

                for client in clients.copy():
                    try:
                        await client.send(json.dumps({"sender": sender, "content": message_content}))
                    except:
                        clients.discard(client)
    finally:
        clients.discard(websocket)
        senders.discard(sender_name)
        user_map.pop(sender_name, None)
        
        # Notify plugins
        for plugin in plugins:
            try:
                await plugin.on_leave(sender_name)
            except Exception as e:
                log(f"Plugin error in on_leave: {e}")

        for client in clients.copy():
            try:
                await client.send(f"- {sender_name} - just left -")
            except:
                clients.discard(client)
def handle_user_management(args):
    users = load_users()
    if args.add_user:
        username = args.add_user
        role = args.role
        
        password = getpass.getpass(prompt=f"Enter password for {username}: ")
        password_confirm = getpass.getpass(prompt="Confirm password: ")
        if password != password_confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)
            
        hashed_pw, salt = hash_password(password)
        roles = []
        if role != "user":
            roles = [role]
            
        users[username] = {
            "password_hash": hashed_pw,
            "salt": salt,
            "roles": roles
        }
        save_users(users)
        print(f"User {username} successfully added/updated with role: {role}")
        
    elif args.delete_user:
        username = args.delete_user
        if username in users:
            del users[username]
            save_users(users)
            print(f"User {username} deleted successfully.")
        else:
            print(f"Error: User {username} not found.")
            sys.exit(1)
            
    elif args.list_users:
        if not users:
            print("No users registered.")
        else:
            print(f"{'Username':<20} {'Roles':<20}")
            print("-" * 40)
            for name, details in users.items():
                roles_str = ", ".join(details.get("roles", [])) or "user"
                print(f"{name:<20} {roles_str:<20}")

def generate_self_signed_cert():
    if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
        log("Self-signed certificates not found. Generating...")
        try:
            subprocess.run([
                "openssl", "req", "-new", "-newkey", "rsa:2048", "-days", "365",
                "-nodes", "-x509", "-keyout", "key.pem", "-out", "cert.pem",
                "-subj", "/C=US/ST=Development/L=Local/O=Chaasnyx/CN=localhost"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log("Self-signed certificates generated successfully (cert.pem, key.pem).")
        except Exception as e:
            log(f"Error generating self-signed certificates: {e}")

async def handle_http(reader, writer):
    try:
        request = b""
        while not request.endswith(b"\r\n\r\n"):
            chunk = await reader.read(1024)
            if not chunk:
                break
            request += chunk
            if len(request) > 8192:
                break
                
        try:
            req_line = request.split(b"\r\n")[0].decode("utf-8")
            path = req_line.split(" ")[1]
        except Exception:
            path = "/"
            
        if path == "/" or path == "/index.html":
            try:
                with open("webui/index.html", "r", encoding="utf-8") as f:
                    content = f.read()
                body = content.encode("utf-8")
                header = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n\r\n"
                )
            except FileNotFoundError:
                body = b"webui/index.html not found. Place index.html under webui/ directory."
                header = (
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/plain; charset=utf-8\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n\r\n"
                )
        else:
            body = b"Not Found"
            header = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            )
            
        writer.write(header.encode("utf-8") + body)
        await writer.drain()
    except Exception as e:
        log(f"HTTP handler exception: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

async def main(port=6741):
    generate_self_signed_cert()
    load_plugins()
    
    webui_port = 0
    if "webui" in config and "port" in config["webui"]:
        webui_port = int(config["webui"]["port"])
        
    log(f"Open for business on port {port} (WSS secure)!")
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    
    ws_server = serve(handler, "0.0.0.0", port, ssl=ssl_context)
    
    tasks = []
    if webui_port > 0:
        log(f"Web UI server active on http://localhost:{webui_port}")
        http_server = await asyncio.start_server(handle_http, "0.0.0.0", webui_port)
        tasks.append(http_server.serve_forever())
        
    async with ws_server:
        if tasks:
            await asyncio.gather(asyncio.Future(), *tasks)
        else:
            await asyncio.Future()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the chat server or manage users.")
    parser.add_argument("--add-user", type=str, help="Username to add or update")
    parser.add_argument("--role", type=str, choices=["admin", "mod", "user"], default="user", help="Role for the new/updated user")
    parser.add_argument("--delete-user", type=str, help="Username to delete")
    parser.add_argument("--list-users", action="store_true", help="List all registered users and their roles")
    parser.add_argument("--port", type=int, default=6741, help="Port to run the server on")
    
    args = parser.parse_args()
    
    if args.add_user or args.delete_user or args.list_users:
        handle_user_management(args)
    else:
        asyncio.run(main(args.port))
