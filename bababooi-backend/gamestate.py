from dataclasses import dataclass, field
import random, base64
from datetime import datetime, timezone
from PIL import Image
import io
import base64
import requests

MAX_GAMES = 10
START_DELAY_IN_SECS = 3
ROUND_LEN_IN_SECS = 30

@dataclass
class Player:
    name: str
    isOwner: bool = False
    gameScore: int = 0
    totalScore: int = 0
    gameSpecificData: dict = field(default_factory=dict)
    def to_dict(self):
        return {"name": self.name,
            "isOwner": self.isOwner,
            "gameScore": self.gameScore,
            "totalScore": self.totalScore,
            "gameSpecificData": self.gameSpecificData}

@dataclass
class GameSession:
    room: str
    players: list = field(default_factory=list)
    gameType: str = "bababooi"
    gameState: str = "lobby"
    gameSpecificData: dict = field(default_factory=dict)
    roundNo: int = 0
    roundLimit: int = 3 # can be changed per-game

    def get_player_array(self):
        player_array = []
        for player in self.players:
            player_array.append(player.to_dict())
        return player_array

    def get_player(self, name):
        for player in self.players:
            if player.name == name:
                return player
        return None

games = {}

bababooi_data = {}

def create_room_with_player(room, user):
    if room in games.keys():
        return 'Room id already exists!'
    if len(games) >= MAX_GAMES:
        return 'Room quantity exceeded!'
    games[room] = GameSession(room)
    games[room].players.append(Player(user, True))
    return ''

def create_player_in_room(room, user):
    if room not in games.keys():
        return "Room doesn't exist!"
    for player in games[room].players:
        if player.name == user:
            return 'Player name is taken!'
    games[room].players.append(Player(user, False))
    return ''

def remove_player(json):
    room = json['room']
    name = json['name']
    if room not in games.keys():
        return
    game = games[room]
    isOwner = False
    for i in range(0, len(game.players)):
        if game.players[i].name == name:
            isOwner = game.players[i].isOwner
            game.players.pop(i)
            break
    if isOwner and len(game.players) > 0:
        game.players[0].isOwner = True
    elif len(game.players) == 0:
        games.pop(room)

def choose_game(json):
    room = json['room']
    name = json['name']
    game = json['game']
    if room not in games.keys():
        return "Room doesn't exist!"
    player = games[room].get_player(name)
    if player == None:
        return "Player doesn't exist in room!"
    if player.isOwner == False:
        return "Player isn't an owner!"
    if games[room].gameState != 'lobby':
        return "Can't choose the game mode while playing!"
    games[room].gameType = game
    # TODO: Validate game type
    return ''

def init_game(room):
    if room not in games.keys():
        return "Room doesn't exist!"
    game = games[room]
    mode = game.gameType
    game.gameSpecificData = {}
    for player in game.players:
        player.gameSpecificData = {}
    if mode == 'bababooi':
        game.roundLimit = 3
        bababooi_init_round(game)

def bababooi_init_round(game):
    state = {}
    num_classes = len(bababooi_data['info']['class_names'])
    classes = random.sample(range(0, num_classes), 2)
    startClassName = bababooi_data['info']['class_names'][classes[0]]
    img_idx = random.randint(0, len(bababooi_data['img'][startClassName]))
    state['startingClassIdx'] = classes[0]
    state['targetClassIdx'] = classes[1]
    state['startingClassName'] = bababooi_data['info']['proper_names'][classes[0]]
    state['targetClassName'] = bababooi_data['info']['proper_names'][classes[1]]
    state['startingImg'] = bababooi_data['img'][startClassName][img_idx]['drawing']
    state['startingTime'] = str(datetime.now(timezone.utc).isoformat())
    state['startDelayInSecs'] = START_DELAY_IN_SECS
    state['roundLengthInSecs'] = ROUND_LEN_IN_SECS
    state['state'] = 'playing'
    game.gameSpecificData = state

def bababooi_start_next_round(game):
    game = games[room]
    if game.gameSpecificData['state'] == 'playing':
        return ''
    game.gameSpecificData['state'] = 'playing'
    game.gameSpecificData['']

def bababooi_end_round(game):
    game.gameSpecificData['state'] = 'reviewing'
    # TODO: Collect images, fire off ML thingy
    images = []
    for player in game.players:
        im = Image.open(io.BytesIO(base64.b64decode(player.gameSpecificData['img'])))
        im.resize((256, 256), resample=PIL.Image.NEAREST)
        image_bytes = io.BytesIO()
        image.save(image_bytes, 'png')
        images.append(base64.b64encode(image_bytes.getvalue()).decude('ascii'))

    json = request.post('endpt', json=images)
    print(json.content)

def start_game(json):
    room = json['room']
    name = json['name']
    if room not in games.keys():
        return "Room doesn't exist!"
    player = games[room].get_player(name)
    if player == None:
        return "Player doesn't exist in room!"
    if player.isOwner == False:
        return "Player isn't an owner!"
    if games[room].gameState != 'lobby':
        return "Can't start the game while already playing!"
    # Clear player prev round scores
    for player in games[room].players:
        player.gameScore = 0
    games[room].gameState = 'playing'
    games[room].roundNo = 0
    init_game(room)
    return ''

def get_gamestate(room):
    if room not in games.keys():
        return None
    res = {}
    game = games[room]
    res['room'] = room
    res['gameType'] = game.gameType
    res['gameState'] = game.gameState
    res['gameSpecificData'] = game.gameSpecificData
    res['roundNo'] = game.roundNo
    res['roundLimit'] = game.roundLimit
    res['players'] = game.get_player_array()
    return res

def submit_image(json):
    room = json['room']
    name = json['name']
    img = json['data'] # TODO: decode img
    game = games[room]
    if game.gameType != 'bababooi':
        return 'Wrong game type for submit_image'
    if game.gameState != 'playing':
        return 'Can\'t submit an image in lobby'
    if game.gameSpecificData['state'] != 'playing':
        return "Can't submit an image after round is over"
    player = game.get_player(name)
    # Determine if player is final player
    lastPlayer = True
    for p in game.players:
        if 'img' not in p.gameSpecificData.keys():
            lastPlayer = False
            break
    if hasRoundExpired(game.gameSpecificData['startingTime'], ROUND_LEN_IN_SECS + START_DELAY_IN_SECS):
        lastPlayer = True
    if 'img' in player.gameSpecificData.keys():
        return "Can't submit an image twice in a round!"
    player.gameSpecificData['img'] = img
    if lastPlayer:
        bababooi_end_round(game)
    return ''

def hasRoundExpired(startTimeStr, durationInSecs):
    roundStart = datetime.fromisoformat(startTimeStr.replace("Z", "+00:00"))
    roundEnd = roundStart + datetime.timedelta(0, durationInSecs)
    return roundEnd <= datetime.now(timezone.utc)

def get_server_status():
    result = {}
    result['maxRooms'] = MAX_GAMES
    result['rooms'] = []
    for game in games.values():
        entry = {}
        entry['sessionId'] = game.room
        entry['userCount'] = len(game.players)
        result['rooms'].append(entry)
    return result

def can_create_new_game():
    return len(games) < MAX_GAMES
