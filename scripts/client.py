import asyncio
import json
import websockets
import getpass
import os
import ssl
import sys
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit import PromptSession

ver = "v000004"
print(fr"""
      __                               
 ____/ /  ___ ____ ____ ___  __ ____ __
/ __/ _ \/ _ `/ _ `(_-</ _ \/ // /\ \ /
\__/_//_/\_,_/\_,_/___/_//_/\_, //_\_\ 
      {ver} client         /___/       
      """)

async def send_loop(websocket, username, session):
    while True:
        msg_text = await session.prompt_async(f"[{username}] - ")  # no prompt character
        message = {"sender": username, "content": msg_text}
        await websocket.send(json.dumps(message))

async def receive_loop(websocket, username, session):
    while True:
        try:
            response = await websocket.recv()

            # try parsing
            try:
                message = json.loads(response)
            except json.JSONDecodeError:
                print(response)
                continue

            if not isinstance(message, dict):
                print(response)
                continue



            sender = message.get("sender")
            content = message.get("content")

            # skip if origin is user
            if sender == username:
                continue

            if message.get("action") == "clear" and sender == "SERVER":
                os.system("clear")
                session.app.invalidate()
                continue

            if message.get("raw") or not sender:
                sys.__stdout__.write(content + "\n")
                sys.__stdout__.flush()
                session.app.invalidate()
            else:
                print(f"[{sender}] - {content}")

        except websockets.ConnectionClosed:
            print("Connection closed")
            break


async def main():
    address = input("ip to connect : ")
    x = address.split(":")
    uri = f"wss://{address}" if len(x) == 2 else f"wss://{address}:6741"
    username = input("username to log in as : ")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with websockets.connect(uri, ssl=ssl_context) as websocket:
        # Send join message
        join_msg = {"sender": username, "content": "join;"}
        await websocket.send(json.dumps(join_msg))

        try:
            response_string = await websocket.recv()
            response = json.loads(response_string)
        except Exception as e:
            print(f"Error receiving connection response: {e}")
            return

        if response.get("status") == "auth_required":
            password = getpass.getpass(prompt=f"Password for {username}: ")
            auth_msg = {"password": password}
            await websocket.send(json.dumps(auth_msg))
            try:
                response_string = await websocket.recv()
                response = json.loads(response_string)
            except Exception as e:
                print(f"Error receiving auth response: {e}")
                return

        if response.get("status") != "ok":
            print(f"Connection failed: {response.get('message', 'Unknown error')}")
            return

        session = PromptSession()

        with patch_stdout():  # ensures prints from receive_loop don't break input
            await asyncio.gather(
                send_loop(websocket, username, session),
                receive_loop(websocket, username, session)
            )

if __name__ == "__main__":
    asyncio.run(main())
