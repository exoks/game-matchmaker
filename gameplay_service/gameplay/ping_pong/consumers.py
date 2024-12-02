#  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣦⣴⣶⣾⣿⣶⣶⣶⣶⣦⣤⣄⠀⠀⠀⠀⠀⠀⠀
#  ⠀⠀⠀⠀⠀⠀⠀⢠⡶⠻⠛⠟⠋⠉⠀⠈⠤⠴⠶⠶⢾⣿⣿⣿⣷⣦⠄⠀⠀⠀            𓐓  consumers.py 𓐔           
#  ⠀⠀⠀⠀⠀⢀⠔⠋⠀⠀⠤⠒⠒⢲⠀⠀⠀⢀⣠⣤⣤⣬⣽⣿⣿⣿⣷⣄⠀⠀
#  ⠀⠀⠀⣀⣎⢤⣶⣾⠅⠀⠀⢀⡤⠏⠀⠀⠀⠠⣄⣈⡙⠻⢿⣿⣿⣿⣿⣿⣦⠀   Student: oezzaou <oezzaou@student.1337.ma>
#  ⢀⠔⠉⠀⠊⠿⠿⣿⠂⠠⠢⣤⠤⣤⣼⣿⣶⣶⣤⣝⣻⣷⣦⣍⡻⣿⣿⣿⣿⡀
#  ⢾⣾⣆⣤⣤⣄⡀⠀⠀⠀⠀⠀⠀⠀⠉⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇
#  ⠀⠈⢋⢹⠋⠉⠙⢦⠀⠀⠀⠀⠀⠀⢀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇       Created: 2024/11/24 10:50:16 by oezzaou
#  ⠀⠀⠀⠑⠀⠀⠀⠈⡇⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠇       Updated: 2024/12/01 21:47:41 by oezzaou
#  ⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⢀⣾⣿⣿⠿⠟⠛⠋⠛⢿⣿⣿⠻⣿⣿⣿⣿⡿⠀
#  ⠀⠀⠀⠀⠀⠀⠀⢀⠇⠀⢠⣿⣟⣭⣤⣶⣦⣄⡀⠀⠀⠈⠻⠀⠘⣿⣿⣿⠇⠀
#  ⠀⠀⠀⠀⠀⠱⠤⠊⠀⢀⣿⡿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠘⣿⠏⠀⠀                             𓆩♕𓆪
#  ⠀⠀⠀⠀⠀⡄⠀⠀⠀⠘⢧⡀⠀⠀⠸⣿⣿⣿⠟⠀⠀⠀⠀⠀⠀⠐⠋⠀⠀⠀                     𓄂 oussama ezzaou𓆃
#  ⠀⠀⠀⠀⠀⠘⠄⣀⡀⠸⠓⠀⠀⠀⠠⠟⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀

# ==== [ Modules: >============================================================
from channels.generic.websocket import AsyncWebsocketConsumer
from .tasks import start_gameplay
import json
import random
import redis

# ==== [ Global: >=============================================================
r = redis.StrictRedis(host="redis", port=6379, db=0)


class PlayerConsumer(AsyncWebsocketConsumer):

    # ====[ connect: establish websocket connection: >=========================
    async def connect(self):
        self.player_id = ''.join(random.choices("abcdefghijklmnopqrs", k=10))
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.game_event_queue = f"{self.room_id}_queue"
        self.initiator = False
        await self.channel_layer.group_add(self.room_id, self.channel_name)
        await self.channel_layer.group_send(self.room_id, {
            "type": "join_lobby",
            "opponent_id": self.player_id,
        })
        await self.accept()
        print(f"[SERVER: CONNECT]: > id:{self.player_id}, room:{self.room_id}")

    # ====[ disconnect: when connection closed >===============================
    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_id, self.channel_name)
        print("[SERVER: DISCONNECT]: > connection closed")

    # ====[ receive: receive data from client-side >===========================
    async def receive(self, text_data):
        # print(f"[SERVER: RECEIVE]: <{text_data}> data is received")
        paddle_data = json.loads(text_data)
        await self.channel_layer.group_send(self.room_id, {
            "type": "paddle_state",
            "player_id": self.player_id,
            "paddle_y": paddle_data['paddle_y'],
        })
        r.rpush(self.game_event_queue, json.dumps({
            self.player_id: paddle_data['paddle_y'],
        }))

    # ====[ join_lobby: gather players in lobby to start game >================
    async def join_lobby(self, text_data):
        if (self.player_id != text_data['opponent_id']):
            self.initiator = True
            start_gameplay.delay(self.player_id, text_data['opponent_id'],
                                 self.room_id, self.game_event_queue)
            print("[SERVER: MESSAGE: > starting game")

    # ====[ gameplay_init: initiate the game for client-side >=================
    async def gameplay_init(self, game_data):
        player, opponent = (0, 1) if self.initiator is True else (1, 0)
        await self.send(json.dumps({
            "event": game_data['type'],
            "ball": game_data['ball'],
            "paddle_x": game_data['paddle_x'][player],
            "player_score": game_data['score'][player],
            "opponent_score": game_data['score'][opponent],
        }))

    # ====[ paddle_state: update paddle_state in client-side >=================
    async def paddle_state(self, paddle_data):
        # print(f"[SERVER: EVENT] > paddle state <{paddle_data}>")
        if self.player_id != paddle_data['player_id']:
            await self.send(json.dumps({
                "event": paddle_data['type'],
                "paddle_y": paddle_data['paddle_y'],
            }))

    # ====[ ball_state: update ball state in client-sdie >=====================
    async def ball_state(self, ball_data):
        await self.send(json.dumps({
            "event": ball_data['type'],
            "ball": ball_data['ball'],
        }))

    # ====[ gameplay_state: update game state in client-sdie >=============
    async def gameplay_reinit(self, reinit_data):
        player, opponent = (0, 1) if self.initiator is True else (1, 0)
        await self.send(json.dumps({
            "event": reinit_data['type'],
            "ball": reinit_data['ball'],
            "paddle_x": reinit_data['paddle_x'][player],
            "player_score": reinit_data['score'][player],
            "opponent_score": reinit_data['score'][opponent],
        }))
