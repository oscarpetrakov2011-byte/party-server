import asyncio
import websockets
import json
from typing import Dict, Set

class PartyServer:
    def __init__(self):
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.parties: Dict[str, Dict] = {}
        self.player_nicknames: Dict[str, str] = {}
        self.player_parties: Dict[str, str] = {}
        self.player_positions: Dict[str, Dict] = {}
        self.player_servers: Dict[str, str] = {}

    async def handle_client(self, websocket):
        client_id = None
        print(f"[SERVER] New connection from {websocket.remote_address}")
        try:
            async for message in websocket:
                print(f"[SERVER] Received raw message: {message}")
                data = json.loads(message)
                action = data.get("action")
                print(f"[SERVER] Action: {action}")

                if action == "connect":
                    client_id = data.get("client_id")
                    self.clients[client_id] = websocket
                    await self.send_message(websocket, {
                        "type": "connected",
                        "message": "Connected to Party Server"
                    })
                    print(f"[SERVER] Client {client_id} connected")

                elif action == "set_nickname":
                    client_id = data.get("client_id")
                    nickname = data.get("nickname")
                    server_ip = data.get("server_ip", "Unknown")
                    self.player_nicknames[client_id] = nickname
                    self.player_servers[client_id] = server_ip
                    await self.send_message(websocket, {
                        "type": "nickname_set",
                        "nickname": nickname
                    })
                    print(f"[SERVER] Client {client_id} set nickname to {nickname} on server {server_ip}")

                elif action == "create_party":
                    client_id = data.get("client_id")
                    party_id = f"party_{client_id}"
                    self.parties[party_id] = {
                        "leader": client_id,
                        "members": [client_id],
                        "invites": []
                    }
                    self.player_parties[client_id] = party_id
                    await self.send_message(websocket, {
                        "type": "party_created",
                        "party_id": party_id
                    })
                    print(f"[SERVER] Party {party_id} created by {client_id}")

                elif action == "invite_player":
                    client_id = data.get("client_id")
                    target_nickname = data.get("target_nickname")
                    print(f"[SERVER] {client_id} wants to invite {target_nickname}")

                    party_id = self.player_parties.get(client_id)
                    if not party_id or self.parties[party_id]["leader"] != client_id:
                        print(f"[SERVER] {client_id} is not a party leader")
                        await self.send_message(websocket, {
                            "type": "error",
                            "message": "You are not a party leader"
                        })
                        continue

                    target_id = None
                    for cid, nick in self.player_nicknames.items():
                        if nick == target_nickname:
                            target_id = cid
                            break

                    print(f"[SERVER] Found target_id: {target_id} for nickname {target_nickname}")
                    print(f"[SERVER] Known nicknames: {self.player_nicknames}")

                    if not target_id:
                        print(f"[SERVER] Player {target_nickname} not found")
                        await self.send_message(websocket, {
                            "type": "error",
                            "message": f"Player {target_nickname} not found"
                        })
                        continue

                    if target_id in self.parties[party_id]["members"]:
                        await self.send_message(websocket, {
                            "type": "error",
                            "message": f"{target_nickname} is already in your party"
                        })
                        continue

                    self.parties[party_id]["invites"].append(target_id)

                    if target_id in self.clients:
                        print(f"[SERVER] Sending invite to {target_id}")
                        await self.send_message(self.clients[target_id], {
                            "type": "party_invite",
                            "party_id": party_id,
                            "from": self.player_nicknames.get(client_id, client_id)
                        })

                    await self.send_message(websocket, {
                        "type": "invite_sent",
                        "target": target_nickname
                    })
                    print(f"[SERVER] Party invite sent from {client_id} to {target_id}")

                elif action == "accept_invite":
                    client_id = data.get("client_id")
                    party_id = data.get("party_id")
                    print(f"[SERVER] {client_id} wants to accept invite to {party_id}")

                    if party_id not in self.parties:
                        print(f"[SERVER] Party {party_id} not found")
                        await self.send_message(websocket, {
                            "type": "error",
                            "message": "Party not found"
                        })
                        continue

                    if client_id not in self.parties[party_id]["invites"]:
                        print(f"[SERVER] No invite found for {client_id} in party {party_id}")
                        print(f"[SERVER] Current invites: {self.parties[party_id]['invites']}")
                        await self.send_message(websocket, {
                            "type": "error",
                            "message": "No invite found"
                        })
                        continue

                    self.parties[party_id]["invites"].remove(client_id)
                    self.parties[party_id]["members"].append(client_id)
                    self.player_parties[client_id] = party_id

                    await self.send_message(websocket, {
                        "type": "party_joined",
                        "party_id": party_id,
                        "members": [self.player_nicknames.get(m, m) for m in self.parties[party_id]["members"]]
                    })
                    print(f"[SERVER] {client_id} joined party {party_id}")

                    for member_id in self.parties[party_id]["members"]:
                        if member_id != client_id and member_id in self.clients:
                            await self.send_message(self.clients[member_id], {
                                "type": "member_joined",
                                "nickname": self.player_nicknames.get(client_id, client_id)
                            })
                            print(f"[SERVER] Notified {member_id} about new member")

                    print(f"[SERVER] Client {client_id} joined party {party_id}")

                elif action == "get_online_players":
                    client_id = data.get("client_id")
                    print(f"[SERVER] {client_id} requested online players list")
                    online_list = []
                    for cid, nick in self.player_nicknames.items():
                        if cid in self.clients:
                            server_ip = self.player_servers.get(cid, "Unknown")
                            online_list.append({
                                "nickname": nick,
                                "server_ip": server_ip
                            })

                    print(f"[SERVER] All nicknames: {self.player_nicknames}")
                    print(f"[SERVER] Connected clients: {list(self.clients.keys())}")
                    print(f"[SERVER] Sending online players: {online_list}")

                    await self.send_message(websocket, {
                        "type": "online_players",
                        "players": online_list
                    })
                    print(f"[SERVER] Sent online players list to {client_id}")

                elif action == "update_position":
                    client_id = data.get("client_id")
                    position = data.get("position")
                    self.player_positions[client_id] = position

                    party_id = self.player_parties.get(client_id)
                    if party_id and party_id in self.parties:
                        for member_id in self.parties[party_id]["members"]:
                            if member_id != client_id and member_id in self.clients:
                                await self.send_message(self.clients[member_id], {
                                    "type": "position_update",
                                    "player_id": client_id,
                                    "nickname": self.player_nicknames.get(client_id, client_id),
                                    "position": position
                                })

        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_id} disconnected")
        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]

                party_id = self.player_parties.get(client_id)
                if party_id and party_id in self.parties:
                    if client_id in self.parties[party_id]["members"]:
                        self.parties[party_id]["members"].remove(client_id)

                    if self.parties[party_id]["leader"] == client_id:
                        del self.parties[party_id]
                        for member_id in self.parties.get(party_id, {}).get("members", []):
                            if member_id in self.clients:
                                await self.send_message(self.clients[member_id], {
                                    "type": "party_disbanded"
                                })
                    else:
                        for member_id in self.parties[party_id]["members"]:
                            if member_id in self.clients:
                                await self.send_message(self.clients[member_id], {
                                    "type": "member_left",
                                    "nickname": self.player_nicknames.get(client_id, client_id)
                                })

                if client_id in self.player_parties:
                    del self.player_parties[client_id]
                if client_id in self.player_positions:
                    del self.player_positions[client_id]

    async def send_message(self, websocket, data):
        try:
            await websocket.send(json.dumps(data))
        except:
            pass

async def main():
    server = PartyServer()
    print("Party WebSocket Server starting on ws://localhost:8765")
    async with websockets.serve(server.handle_client, "localhost", 8765):
        print("Server is running! Press Ctrl+C to stop.")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
