import asyncio
import json
import logging
import os
import sys

import global_value as g

g.app_name = "kick_chat_bot"
g.base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

from config_helper import read_config
from fuyuka_helper import Fuyuka
from kick_message_helper import create_message_json
from random_helper import is_hit_by_message_json
from text_helper import read_text, read_text_set
from websocket_helper import websocket_listen_forever

print("前回の続きですか？(y/n) ", end="")
is_continue = input() == "y"

g.ADDITIONAL_REQUESTS_PROMPT = read_text("prompts/additional_requests_prompt.txt")

g.config = read_config()

# ロガーの設定
logging.basicConfig(filename=f"{g.app_name}.log", encoding="utf-8", level=logging.INFO)

logger = logging.getLogger(__name__)

g.map_is_first_on_stream = {}
g.set_exclude_id = read_text_set("exclude_id.txt")
g.websocket_kick_live = None
g.websocket_fuyuka = None


async def main():
    def get_fuyukaApi_baseUrl() -> str:
        conf_fa = g.config["fuyukaApi"]
        if not conf_fa:
            return ""
        return conf_fa["baseUrl"]

    def get_oneComme_baseUrl() -> str:
        conf_oc = g.config["oneComme"]
        if not conf_oc:
            return ""
        return conf_oc["baseUrl"]

    def set_ws_kick_live(ws) -> None:
        g.websocket_kick_live = ws

    async def recv_kick_live_response(message: str) -> None:
        try:
            json_data = json.loads(message)
            if json_data["type"] != "comments":
                return

            data = json_data["data"]
            for comment in data["comments"]:
                if comment["service"] != "kick":
                    continue

                logger.info(comment)
                data = comment["data"]
                json_data = create_message_json(data)
                if json_data["id"] in g.set_exclude_id:
                    # 無視するID
                    return

                answerLevel = g.config["fuyukaApi"]["answerLevel"]
                needs_response = is_hit_by_message_json(answerLevel, json_data)
                await Fuyuka.send_message_by_json_with_buf(json_data, needs_response)
        except json.JSONDecodeError as e:
            logger.error(f"Error JSONDecode: {e}")
        except Exception as e:
            logger.error(f"Error : {e}")

    def set_ws_fuyuka(ws) -> None:
        g.websocket_fuyuka = ws

    async def recv_fuyuka_response(message: str) -> None:
        return

    fuyukaApi_baseUrl = get_fuyukaApi_baseUrl()
    if fuyukaApi_baseUrl:
        websocket_uri = f"{fuyukaApi_baseUrl}/chat/{g.app_name}"
        asyncio.create_task(
            websocket_listen_forever(websocket_uri, recv_fuyuka_response, set_ws_fuyuka)
        )

    oneComme_baseUrl = get_oneComme_baseUrl()
    if oneComme_baseUrl:
        websocket_uri = f"{oneComme_baseUrl}/sub?p=comments"
        asyncio.create_task(
            websocket_listen_forever(
                websocket_uri, recv_kick_live_response, set_ws_kick_live
            )
        )

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        pass
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(main())
