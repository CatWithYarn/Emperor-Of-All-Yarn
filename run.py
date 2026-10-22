"""Ladder entry point for AI Arena.

The arena client starts SC2 itself and then launches this file with
--GamePort / --LadderServer / --StartPort (and sometimes --OpponentId, --RealTime).
We connect to that existing SC2 instance and play the game. Like the long-standing
python-sc2 ladder scripts, we only close our websocket afterwards; the arena client
owns the SC2 process (and its replay saving), so we do not send leave/quit.
"""
import argparse
import asyncio

import aiohttp

from sc2.client import Client
from sc2.data import Race
from sc2.main import _play_game
from sc2.player import Bot
from sc2.portconfig import Portconfig
from sc2.protocol import ConnectionAlreadyClosedError

from bot import MyBot


async def join_ladder_game(host, port, bot, realtime, portconfig):
    ws_url = f"ws://{host}:{port}/sc2api"
    session = aiohttp.ClientSession()
    ws = await session.ws_connect(ws_url, timeout=120)
    client = Client(ws)
    try:
        result = await _play_game(bot, client, realtime, portconfig)
    except ConnectionAlreadyClosedError:
        print("Connection was closed before the game ended")
        result = None
    finally:
        await ws.close()
        await session.close()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--GamePort", type=int)
    parser.add_argument("--StartPort", type=int)
    parser.add_argument("--LadderServer", type=str)
    parser.add_argument("--OpponentId", type=str)
    parser.add_argument("--RealTime", action="store_true")
    args, _unknown = parser.parse_known_args()

    host = args.LadderServer or "127.0.0.1"

    ai = MyBot()
    ai.opponent_id = args.OpponentId  # available as self.opponent_id inside the bot
    bot = Bot(Race.Terran, ai, name="The Emperor of all Yarn, Catigula")

    # Same port layout the ladder gives every bot, so bot-vs-bot games can connect.
    ports = [args.StartPort + p for p in range(1, 6)]
    portconfig = Portconfig()
    portconfig.shared = ports[0]
    portconfig.server = [ports[1], ports[2]]
    portconfig.players = [[ports[3], ports[4]]]

    result = asyncio.run(join_ladder_game(host, args.GamePort, bot, args.RealTime, portconfig))
    print(result, "against opponent", args.OpponentId)


if __name__ == "__main__":
    main()