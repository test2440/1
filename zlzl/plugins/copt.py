import zipfile
import base64
import re
import typing
import ipaddress
import struct
from pathlib import Path
from typing import Type, Optional
import os
import secrets
from time import sleep
from urllib.parse import urlparse, parse_qs

try:
    import aiosqlite
    from opentele.api import API, APIData
    from pyrogram.client import Client
    from pyrogram.session.internals.data_center import DataCenter
    from pyrogram import Client as czz
    from kvsqlite.sync import Client as uu
except ModuleNotFoundError:
    os.system("pip3 install opentele aiosqlite pyrogram kvsqlite")
    import aiosqlite
    from opentele.api import API, APIData
    from pyrogram.client import Client
    from pyrogram.session.internals.data_center import DataCenter
    from pyrogram import Client as czz
    from kvsqlite.sync import Client as uu

from telethon.sessions import StringSession
import asyncio, re, json, shutil
from asyncio.exceptions import TimeoutError
from telethon.tl.types import KeyboardButtonUrl
from telethon.tl.types import KeyboardButton, ReplyInlineMarkup
from telethon import TelegramClient, events, functions, types, Button
from telethon.tl.types import DocumentAttributeFilename, PeerUser
from telethon.tl.functions.messages import GetMessagesViewsRequest
from telethon.tl.functions.channels import GetFullChannelRequest
import time, datetime, random 
from datetime import timedelta
from telethon.errors.rpcerrorlist import ForbiddenError
from telethon.errors import (
    ApiIdInvalidError,
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PasswordHashInvalidError
)
from . import bot, zedub
from ..Config import Config
from ..utils import Zed_Vip
from ..core.managers import edit_delete, edit_or_reply

        
if not os.path.isdir('database'):
    os.mkdir('database')

bot = borg = tgbot
API_ID = "22256614"
API_HASH = "4f9f53e287de541cf0ed81e12a68fa3b"
admin = Config.OWNER_ID
ZThonDev = (5746412340, 5003461173, 6227985448, 2095357462)

#Create DataBase
db = uu('database/elhakem.ss', 'bot')

if not db.exists("accounts"):
    db.set("accounts", [])

if not db.exists("bad_guys"):
    db.set("bad_guys", [])

if not db.exists("force"):
   db.set("force", [])


async def num_sign(phone_number):
    X = TelegramClient(StringSession(), 22256614, "4f9f53e287de541cf0ed81e12a68fa3b")
    try:
        await X.connect()
        code = await X.send_code_request(phone_number)
    except ApiIdInvalidError as a:
        await tgbot.send_message(admin, str(a))
        return
    except PhoneNumberInvalidError as a:
        await tgbot.send_message(admin, str(a))
        return
    except Exception as a:
        await tgbot.send_message(admin, str(a))
        return
    return str(X)


# file converter
class ValidationError(Exception):
    pass


SCHEMAT = """
CREATE TABLE version (version integer primary key);

CREATE TABLE sessions (
    dc_id integer primary key,
    server_address text,
    port integer,
    auth_key blob,
    takeout_id integer
);

CREATE TABLE entities (
    id integer primary key,
    hash integer not null,
    username text,
    phone integer,
    name text,
    date integer
);

CREATE TABLE sent_files (
    md5_digest blob,
    file_size integer,
    type integer,
    id integer,
    hash integer,
    primary key(md5_digest, file_size, type)
);

CREATE TABLE update_state (
    id integer primary key,
    pts integer,
    qts integer,
    date integer,
    seq integer
);
"""


class TeleSession:
    _STRUCT_PREFORMAT = '>B{}sH256s'
    CURRENT_VERSION = '1'
    TABLES = {
        "sessions": {
            "dc_id", "server_address", "port", "auth_key", "takeout_id"
            },
        "entities": {"id", "hash", "username", "phone", "name", "date"},
        "sent_files": {"md5_digest", "file_size", "type", "id", "hash"},
        "update_state": {"id", "pts", "qts", "date", "seq"},
        "version": {"version"},
    }

    def __init__(
        self,
        *,
        dc_id: int,
        auth_key: bytes,
        server_address: Optional[str] = None,
        port: Optional[int] = None,
        takeout_id: Optional[int] = None
    ):
        self.dc_id = dc_id
        self.auth_key = auth_key
        self.server_address = server_address
        self.port = port
        self.takeout_id = takeout_id

    @classmethod
    def from_string(cls, string: str):
        string = string[1:]
        ip_len = 4 if len(string) == 352 else 16
        dc_id, ip, port, auth_key = struct.unpack(
            cls._STRUCT_PREFORMAT.format(ip_len), cls.decode(string)
        )
        server_address = ipaddress.ip_address(ip).compressed
        return cls(
            auth_key=auth_key,
            dc_id=dc_id,
            port=port,
            server_address=server_address,
        )

    @classmethod
    async def from_file(cls, path: Path):
        if not await cls.validate(path):
            raise ValidationError()

        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions") as cursor:
                session = await cursor.fetchone()

        return cls(**session)

    @classmethod
    async def validate(cls, path: Path) -> bool:
        try:
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                sql = "SELECT name FROM sqlite_master WHERE type='table'"
                async with db.execute(sql) as cursor:
                    tables = {row["name"] for row in await cursor.fetchall()}

                if tables != set(cls.TABLES.keys()):
                    return False

                for table, session_columns in cls.TABLES.items():
                    sql = f'pragma table_info("{table}")'
                    async with db.execute(sql) as cur:
                        columns = {row["name"] for row in await cur.fetchall()}
                        if session_columns != columns:
                            return False

        except aiosqlite.DatabaseError:
            return False

        return True

    @staticmethod
    def encode(x: bytes) -> str:
        return base64.urlsafe_b64encode(x).decode('ascii')

    @staticmethod
    def decode(x: str) -> bytes:
        return base64.urlsafe_b64decode(x)

    def client(
        self,
        api: Type[APIData],
        proxy: Optional[dict] = None,
        no_updates: bool = True
    ):
        client = TelegramClient(
            session=StringSession(self.to_string()),
            api_id=api.api_id,
            api_hash=api.api_hash,
            proxy=proxy,
            device_model=api.device_model,
            system_version=api.system_version,
            app_version=api.app_version,
            lang_code=api.lang_code,
            system_lang_code=api.system_lang_code,
            receive_updates=not no_updates,
        )
        return client

    def to_string(self) -> str:
        if self.server_address is None:
            self.server_address, self.port = DataCenter(
                self.dc_id, False, False, False
            )
        ip = ipaddress.ip_address(self.server_address).packed
        return self.CURRENT_VERSION + self.encode(struct.pack(
            self._STRUCT_PREFORMAT.format(len(ip)),
            self.dc_id,
            ip,
            self.port,
            self.auth_key
        ))

    async def to_file(self, path: Path):
        async with aiosqlite.connect(path) as db:
            await db.executescript(SCHEMAT)
            await db.commit()
            sql = "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)"
            params = (
                self.dc_id,
                self.server_address,
                self.port,
                self.auth_key,
                self.takeout_id
            )
            await db.execute(sql, params)
            await db.commit()





SCHEMA = """
CREATE TABLE sessions (
    dc_id     INTEGER PRIMARY KEY,
    api_id    INTEGER,
    test_mode INTEGER,
    auth_key  BLOB,
    date      INTEGER NOT NULL,
    user_id   INTEGER,
    is_bot    INTEGER
);

CREATE TABLE peers (
    id             INTEGER PRIMARY KEY,
    access_hash    INTEGER,
    type           INTEGER NOT NULL,
    username       TEXT,
    phone_number   TEXT,
    last_update_on INTEGER NOT NULL DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
);

CREATE TABLE version (
    number INTEGER PRIMARY KEY
);

CREATE INDEX idx_peers_id ON peers (id);
CREATE INDEX idx_peers_username ON peers (username);
CREATE INDEX idx_peers_phone_number ON peers (phone_number);

CREATE TRIGGER trg_peers_last_update_on
    AFTER UPDATE
    ON peers
BEGIN
    UPDATE peers
    SET last_update_on = CAST(STRFTIME('%s', 'now') AS INTEGER)
    WHERE id = NEW.id;
END;
"""


class PyroSession:
    OLD_STRING_FORMAT = ">B?256sI?"
    OLD_STRING_FORMAT_64 = ">B?256sQ?"
    STRING_SIZE = 351
    STRING_SIZE_64 = 356
    STRING_FORMAT = ">BI?256sQ?"
    TABLES = {
        "sessions": {"dc_id", "test_mode", "auth_key", "date", "user_id", "is_bot"},
        "peers": {"id", "access_hash", "type", "username", "phone_number", "last_update_on"},
        "version": {"number"}
    }

    def __init__(
        self,
        *,
        dc_id: int,
        auth_key: bytes,
        user_id: Optional[int] = None,
        is_bot: bool = False,
        test_mode: bool = False,
        api_id: Optional[int] = None,
        **kw
    ):
        self.dc_id = dc_id
        self.auth_key = auth_key
        self.user_id = user_id
        self.is_bot = is_bot
        self.test_mode = test_mode
        self.api_id = api_id

    @classmethod
    def from_string(cls, session_string: str):
        if len(session_string) in [cls.STRING_SIZE, cls.STRING_SIZE_64]:
            string_format = cls.OLD_STRING_FORMAT_64

            if len(session_string) == cls.STRING_SIZE:
                string_format = cls.OLD_STRING_FORMAT

            api_id = None
            dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
                string_format,
                base64.urlsafe_b64decode(
                    session_string + "=" * (-len(session_string) % 4)
                )
            )
        else:
            dc_id, api_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
                cls.STRING_FORMAT,
                base64.urlsafe_b64decode(
                    session_string + "=" * (-len(session_string) % 4)
                )
            )

        return cls(
            dc_id=dc_id,
            api_id=api_id,
            auth_key=auth_key,
            user_id=user_id,
            is_bot=is_bot,
            test_mode=test_mode,
        )

    @classmethod
    async def from_file(cls, path: Path):
        if not await cls.validate(path):
            raise ValidationError()

        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions") as cursor:
                session = await cursor.fetchone()

        return cls(**session)

    @classmethod
    async def validate(cls, path: Path) -> bool:
        try:
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                sql = "SELECT name FROM sqlite_master WHERE type='table'"
                async with db.execute(sql) as cursor:
                    tables = {row["name"] for row in await cursor.fetchall()}

                if tables != set(cls.TABLES.keys()):
                    return False

                for table, session_columns in cls.TABLES.items():
                    sql = f'pragma table_info("{table}")'
                    async with db.execute(sql) as cur:
                        columns = {row["name"] for row in await cur.fetchall()}
                        if "api_id" in columns:
                            columns.remove("api_id")
                        print(columns, session_columns)
                        print(columns != session_columns)
                        if session_columns != columns:
                            return False

        except aiosqlite.DatabaseError:
            return False

        return True

    def client(
        self,
        api: Type[APIData],
        proxy: Optional[dict] = None,
        no_updates: bool = True
    ) -> Client:
        client = Client(
            name=secrets.token_urlsafe(8),
            api_id=api.api_id,
            api_hash=api.api_hash,
            app_version=api.app_version,
            device_model=api.device_model,
            system_version=api.system_version,
            lang_code=api.lang_code,
            proxy=proxy,
            session_string=self.to_string(),
            no_updates=no_updates,
            test_mode=self.test_mode,
        )
        return client

    def to_string(self) -> str:
        packed = struct.pack(
            self.STRING_FORMAT,
            self.dc_id,
            self.api_id or 0,
            self.test_mode,
            self.auth_key,
            self.user_id or 9999,
            self.is_bot
        )
        return base64.urlsafe_b64encode(packed).decode().rstrip("=")

    async def to_file(self, path: Path):
        async with aiosqlite.connect(path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
            sql = "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)"
            params = (
                self.dc_id,
                self.api_id,
                self.test_mode,
                self.auth_key,
                0,
                self.user_id or 9999,
                self.is_bot
            )
            await db.execute(sql, params)
            await db.commit()



class SessionManager:
    def __init__(
        self,
        dc_id: int,
        auth_key: bytes,
        user_id: Optional[int] = None,
        valid: Optional[bool] = None,
        api: Type[APIData] = API.TelegramDesktop,
    ):
        self.dc_id = dc_id
        self.auth_key = auth_key
        self.user_id = user_id
        self.valid = valid
        self.api = api.copy()
        self.user = None
        self.client = None

    async def __aenter__(self):
        self.client = self.telethon_client()
        await self.client.connect()
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()
        self.client = None

    @property
    def auth_key_hex(self) -> str:
        return self.auth_key.hex()

    @classmethod
    async def from_telethon_file(cls, file: Path, api=API.TelegramDesktop):
        session = await TeleSession.from_file(file)
        return cls(
            dc_id=session.dc_id,
            auth_key=session.auth_key,
            api=api
        )

    @classmethod
    def from_telethon_string(cls, string: str, api=API.TelegramDesktop):
        session = TeleSession.from_string(string)
        return cls(
            dc_id=session.dc_id,
            auth_key=session.auth_key,
            api=api
        )

    @classmethod
    async def from_pyrogram_file(cls, file: Path, api=API.TelegramDesktop):
        session = await PyroSession.from_file(file)
        return cls(
            auth_key=session.auth_key,
            dc_id=session.dc_id,
            api=api,
            user_id=session.user_id,
        )

    @classmethod
    def from_pyrogram_string(cls, string: str, api=API.TelegramDesktop):
        session = PyroSession.from_string(string)
        return cls(
            auth_key=session.auth_key,
            dc_id=session.dc_id,
            api=api,
            user_id=session.user_id,
        )



    async def to_pyrogram_file(self, path: Path):
        await self.pyrogram.to_file(path)

    def to_pyrogram_string(self) -> str:
        return self.pyrogram.to_string()

    async def to_telethon_file(self, path: Path):
        await self.telethon.to_file(path)

    def to_telethon_string(self) -> str:
        return self.telethon.to_string()



    @property
    def pyrogram(self) -> PyroSession:
        return PyroSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
            user_id=self.user_id,
        )

    @property
    def telethon(self) -> TeleSession:
        return TeleSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
        )



    def pyrogram_client(self, proxy=None, no_updates=True):
        client = self.pyrogram.client(
            api=self.api,
            proxy=proxy,
            no_updates=no_updates,
        )
        return client

    def telethon_client(self, proxy=None, no_updates=True):
        client = self.telethon.client(
            api=self.api,
            proxy=proxy,
            no_updates=no_updates,
        )
        return client

    async def validate(self) -> bool:
        user = await self.get_user()
        self.valid = bool(user)
        return self.valid

    async def get_user_id(self):
        if self.user_id:
            return self.user_id

        user = await self.get_user()

        if user is None:
            raise ValidationError()

        return user.id

    async def get_user(self):
        async with self as client:
            self.user = await client.get_me()
            if self.user:
                self.user_id = self.user.id
        return self.user


class MangSession:


    def PYROGRAM_TO_TELETHON(session_string: str):
        Session_data = SessionManager.from_pyrogram_string(session_string)
        return Session_data.to_telethon_string()
        
    def TELETHON_TO_PYROGRAM(session_string: str):
        Session_data = SessionManager.from_telethon_string(session_string)
        return Session_data.to_pyrogram_string()


# functions of get_gift | write by t.me/BBBlibot
async def get_gift(session):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    await X.connect()
    try:
        messages = await X.get_messages(777000, limit=5)
        for message in messages:
            try:
                if message.action and message.action.slug:
                    return message.action.slug
            except:
                pass
    except:
        pass
    return False

async def join_channel(session, channel):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        result = await X(functions.channels.JoinChannelRequest(
            channel=channel
        ))
        return True
    except Exception as a:
        return False

async def leave_channel(session, channel):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        result = await X(functions.channels.LeaveChannelRequest(
            channel=channel
        ))
        return True
    except Exception as a:
        return False

async def leave_all(session):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        async for dialog in X.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                await dialog.delete()
        return True
    except Exception as a:
        return False

async def check(session, bot, user_id):
    try:
        app = czz('::memory::', api_id=API_ID, api_hash=API_HASH, in_memory=True, session_string=session)
    except Exception as a:
        print(a)
    try:
        await app.start()
    except Exception as a:
        print(a)
        await bot.send_message(user_id, str(a))
        return False
    try:
        await app.get_me()
        await app.send_message("me", ".")
        await app.stop()
        return True
    except Exception as a:
        print(a)
        await bot.send_message(user_id, str(a))
        return False

async def lllvote_liker(session, channel, msgid, tmm):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        result = await X(functions.channels.JoinChannelRequest(
            channel=channel
        ))
        joion = await X(functions.channels.JoinChannelRequest('ZThon'))
        msg = await X.get_messages(channel, ids=msgid)
        await msg.click(0)
        sleep(tmm)
        return True
    except Exception:
        return False

async def lllview_post(session, channel, msgid):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        result = await X(functions.channels.JoinChannelRequest(
            channel=channel
        ))
        ids = int(msgid)
        msg_ids = [ids]
        await X(GetMessagesViewsRequest(
                peer=channel,
                id=msg_ids,
                increment=True   
            ))
        sleep(1)
        return True
    except Exception:
        return False

async def send_txt(session, chuser, txtmsg):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        try:
            result = await X(functions.channels.JoinChannelRequest(
                channel=channel
            ))
        except Exception:
            pass
        await X.send_message(chuser, txtmsg)
        sleep(1)
        return True
    except Exception:
        return False

async def reaction_tree(session, channel, msgid): # رشق تفاعل عشوائي
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        #joion = await X(functions.channels.JoinChannelRequest('ZThon'))
        msg = await X.get_messages(channel, ids=msgid)
        getchat = await X(GetFullChannelRequest(channel=channel))
        grp_emoji = getchat.full_chat.available_reactions
        if not grp_emoji:
            return
        emoji = grp_emoji
        for i in emoji:
            try:
                await msg.react(i, True)
            except ForbiddenError:
                return False
        sleep(1)
        return True
    except Exception as a:
        print(a)
        await tgbot.send_message(admin, str(a))
        return False


async def reaction_one(session, channel, msgid, zreaction): # رشق تفاعل محدد
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        #joion = await X(functions.channels.JoinChannelRequest('ZThon'))
        msg = await X.get_messages(channel, ids=msgid)
        getchat = await X(GetFullChannelRequest(channel=channel))
        grp_emoji = getchat.full_chat.available_reactions
        if not grp_emoji:
            return
        if zreaction not in grp_emoji:
            return
        emoji = zreaction
        try:
            await msg.react(zreaction, True)
        except ForbiddenError:
            return False
        sleep(1)
        return True
    except Exception as a:
        print(a)
        await tgbot.send_message(admin, str(a))
        return False


async def userinfo(strses):
    X = TelegramClient(StringSession(strses), API_ID, API_HASH)
    await X.connect()
    k = await X.get_me()
    PHONE = f"+{k.phone}"
    #ID = k.id
    return PHONE

# رشق مشاهدات ستوري
async def view_story(session, url):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        url_split = url.text.split('/')
        username = url_split[-3]
        peer_id = int(url_split[-1])
        result = await X(functions.stories.ReadStoriesRequest(
                peer=username,
                max_id=peer_id
        ))
        sleep(1)
        return True
    except Exception as a:
        print(a)
        await tgbot.send_message(admin, str(a))
        return False

# رشق تفاعل قلب ستوري
async def reaction_story(session, url):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    try:
        await X.connect()
        url_split = url.text.split('/')
        username = url_split[-3]
        peer_id = int(url_split[-1])
        result = await X(functions.stories.SendReactionRequest(
                peer=username,
                story_id=peer_id,
                reaction=types.ReactionEmoji(
                    emoticon="❤️"
                ),
                add_to_recent=True
         ))
        sleep(1)
        return True
    except Exception as a:
        print(a)
        await tgbot.send_message(admin, str(a))
        return False

# Rection messaeg functions 
async def RECTIONS_MESSAGE(sessions_string, channel, msg_id, rections):
    app = czz('::memory::', api_id=API_ID, api_hash=API_HASH, in_memory=True, session_string=sessions_string)
    try:
        await app.start()
    except Exception as a:
        print(a)
        #await tgbot.send_message(admin, str(a))
        return False
    try:
        await app.send_reaction(channel, msg_id, rections)
        await app.stop()
        sleep(1)
        return True
    except Exception as a:
        print(a)
        #await tgbot.send_message(admin, str(a))
        return False

# Rection tree messaeg functions 
async def reaction_tree_pyro(sessions_string, channel, msg_id):
    rs = ["👍","🤩","🎉","🔥","❤️","🥰","🌚","💔","💯","😍","🕊","🐳","🤝","🦄","🎃","🤓","👀","🍓","⚡️","🏆","🆒","🙈","☃️"]
    app = czz('::memory::', api_id=API_ID, api_hash=API_HASH, in_memory=True, session_string=sessions_string)
    try:
        await app.start()
    except Exception as a:
        print(a)
        await tgbot.send_message(admin, str(a))
        return False
    try:
        await app.send_reaction(channel, msg_id, random.choice(rs))
        await app.stop()
        sleep(1)
        return True
    except Exception as a:
        print(a)
        await tgbot.send_message(admin, str(a))
        return False


async def sub_bots(sessions_string, user, text):
    app = czz('::memory::', api_id=API_ID, api_hash=API_HASH, in_memory=True, session_string=sessions_string)
    try:
        await app.start()
    except Exception as a:
        print(a)
        return False
    try:
        await app.send_message(user, text)
        await app.stop()
        sleep(1)
        return True
    except Exception:
        print(a)
        return False


async def vote_poll(sessions_string, channel, msg_id, pi, tmm):
    app = czz('::memory::', api_id=API_ID, api_hash=API_HASH, in_memory=True, session_string=sessions_string)
    try:
        await app.start()
    except Exception as a:
        print(a)
        #await tgbot.send_message(admin, str(a))
        return False
    #z = check_format(link)
    #if z:
        #channel, msg_id = z
    try:
        await app.vote_poll(channel, msg_id, [pi])
        await app.stop()
        sleep(tmm)
        return True
    except Exception as a:
        print(a)
        #await tgbot.send_message(admin, str(a))
        return False


async def send_comment(sessions_string, channel, msg_id, num, text, tmm):
    app = czz('::memory::', api_id=API_ID, api_hash=API_HASH, in_memory=True, session_string=sessions_string)
    try:
        await app.start()
    except Exception as a:
        print(a)
        #await tgbot.send_message(admin, str(a))
        return False
    try:
        await app.join_chat(channel)
        await app.send_message(channel, text, reply_to_message_id=msg_id)
        await app.leave_chat(channel)
        await app.stop()
        sleep(tmm)
        return True
    except Exception as a:
        print(a)
        #await tgbot.send_message(admin, str(a))
        return False


def check_format(link):
    pattern = r"https?://t\.me/(\w+)/(\d+)"
    match = re.match(pattern, link)
    if match:
        username = match.group(1)
        post_id = int(match.group(2))
        return username, post_id
    else:
        return False

def checks(link):
    pattern = r"https?://t\.me/(\w+)/(\d+)"
    match = re.match(pattern, link)
    if match:
        username = match.group(1)
        post_id = match.group(2)
        return username, post_id
    else:
        return False

def get_usrnm(link):
    pattern = r"https?://t.me/(w+)"
    match = re.match(pattern, link)
    if match:
        username = match.group(1)
        return username
    else:
        return False

#نقل اعضاء من جروب لجروب عبر الرابط
async def invite_member(session, tochannel, fromchannel):
    X = TelegramClient(StringSession(session), API_ID, API_HASH)
    done, notdone = 0, 0
    try:
        try:
            await X.connect()
            result = await X(functions.channels.JoinChannelRequest(
                channel=tochannel
            ))
            #if tochannel.text.startswith('https://t.me/+'):
                #link = tochannel.text.replace('https://t.me/+', '')
                #result = await X(functions.channels.JoinChannelRequest(link.strip()))
            #elif tochannel.startswith('@'):
                #get_entity_must_join = await X.get_entity(link)
                #result = await X(functions.channels.JoinChannelRequest(get_entity_must_join.id))
            #else:
                #get_entity_must_join = await X.get_entity(link)
                #result = await X(functions.channels.JoinChannelRequest(get_entity_must_join.id))
            #await asyncio.sleep(3)
            #await X(functions.messages.ImportChatInviteRequest(tochannel))
        except Exception as a:
            print(a)
            await tgbot.send_message(admin, "**- إشعار 1:**\n\n" + str(a))
            pass
        #usrm = get_usrnm(fromchannel)
        target = await X.get_entity(fromchannel)
        all_participants = await X.get_participants(target)
        for participant in all_participants:
            try:
                await X(functions.channels.InviteToChannelRequest(
                    channel=tochannel,
                    users=[types.InputUser(
                        user_id=participant.id,
                        access_hash=participant.access_hash
                    )]
                ))
                #print(F+"تم نقل العضو {} إلى القناة بنجاح".format(participant.first_name))
                done += 1
                await asyncio.sleep(15)
            except Exception as e:
                if "This user was kicked from this supergroup/channel" in str(e):
                    await tgbot.send_message(admin, "**- إشعار 3**\n**- احد الحسابات تم حظرها من المجموعة**")
                    break
                if "A wait of" in str(e):
                    #wait_time = e.seconds
                    notdone += 1
                    await tgbot.send_message(admin, "**- إشعار جديـد**\n**- الحساب بلع فلـود (حظر مؤقت)**\n\n\n" + str(e))
                    #await asyncio.sleep(wait_time + 10)
                    break
                else:
                    await tgbot.send_message(admin, "**- إشعار 3**\n\n" + str(e))
                    notdone += 1
                    #break
                #print(Z+"\nخطأ في نقل العضو {} إلى القناة: {}".format(participant.first_name, str(e)))
        k = await X.get_me()
        PHONE = f"+{k.phone}"
        #cha = client.get_entity(tochannel)
        #participants_count = X(functions.channels.GetFullChannelRequest(cha)).full_chat.participants_count
        #print(F+"عدد الأعضاء في القناة: {}".format(participants_count))
        await tgbot.send_message(admin, f"**- تم إنتهاء الاضافة .. بنجاح ☑️**\n**- مـن الحسـاب {PHONE} 🛂**\n**- تم إضافة {done} عضو ✅**\n**- فشـل بـ إضافة {notdone} ✖️**\n\n**- الاضافة مازالت جاريـه مـن بقيـة الحسابات .. انتظـر ⏳**")
        sleep(3)
        return True
    except Exception as k:
        print(k)
        await tgbot.send_message(admin, "**- إشعار 4**\n\n" + str(k))
        return False
      
# Copyright (C) 2024 Zed-Thon . All Rights Reserved
@zedub.zed_cmd(pattern="تحكم$")
async def controol(event):
    botusername = Config.TG_BOT_USERNAME
    return await edit_or_reply(event, f"**- لـ الدخـول لـ قسـم التحكـم 🕹**\n**- الخـاص بالبـوات المسـاعـد الخاص بك 💡**\n**- قم بالذهـاب الى البوت {botusername}**\n**- ثم ارسـل الامـر (** `/control` **)**")

@tgbot.on(events.NewMessage(pattern="/control", func = lambda x: x.is_private))
async def gift(event):
    user_id = event.sender_id
    chat = await event.get_chat()
    mention = f"[{chat.first_name}](tg://user?id={chat.id})"
    #if admin not in Zed_Vip:
        #return await edit_or_reply(event, "**⎉╎عـذࢪاً .. ؏ـزيـزي\n⎉╎هـذا الامـر ليـس مجـانـي📵\n⎉╎للاشتـراك في الاوامـر المدفوعـة\n⎉╎تواصـل مطـور السـورس @BBBlibot\n⎉╎او التواصـل مـع احـد المشرفيـن @AAAl1l**")
    if user_id == admin:
        bans = db.get('bad_guys') if db.exists('bad_guys') else []
        async with bot.conversation(event.chat_id) as x:
            buttons = [
                [
                    Button.inline("عدد حسابات البوت ♾", data="lllget_accounts_count"),
                ],
                [
                    Button.inline("تسجيل عبر الرقم 📲", data="addd"),
                ],
                [
                    Button.inline("تسجيل جلسة بايروجرام", data="lllpyrogram"),
                    Button.inline("تسجيل جلسة تيليثون", data="llltelethon"),
                ],
                [
                    Button.inline("جلب جلسة حساب 📤", data="lllget_session"),
                ],
                [
                    Button.inline("مغادرة قناة", data="lllleave_channel"),
                    Button.inline("الانضمام لقناة", data="llljoin_channel"),
                ],
                [
                    Button.inline("جلب نسخة احتياطية 💾", data="lllzip_all"),
                ],
                [
                    Button.inline("مغادرة القنوات", data="lllleave_all"),
                    Button.inline("فحص الحسابات", data="lllcheck"),
                ],
                [
                    Button.inline("جلب روابط السحوبات 🎁", data="lllget_gift"),
                ],
                [
                    Button.inline("ارسال رسالة لـ شخص | جروب 💌", data="lllsend_txt"),
                ],
                [
                    Button.inline("رشق تفاعل ستوري ❤️", data="reaction_story"),
                    Button.inline("رشق مشاهدات ستوري 👀", data="view_story"),
                ],
                [
                    Button.inline("رشق مشاهدات منشور 👁‍🗨", data="lllview_post"),
                ],
                [
                    Button.inline("رشق تعليقات (كومنتات) 💬", data="send_comment"),
                ],
                [
                    Button.inline("رشق تفاعل محدد ❤️", data="reaction_one_pyro"),
                    Button.inline("رشق تفاعل عشوائي 🎨", data="reaction_tree_pyro"),
                ],
                [
                    Button.inline("رشق اصوات مسابقات 🗳", data="lllvote_liker"),
                ],
                [
                    Button.inline("رشق استفتاء 🪧", data="vote_poll"),
                ],
                [
                    Button.inline("الاشتراك برابط الدعوة لـ بوت 🖇", data="sub_bots"),
                ],
                [
                    Button.inline("نقـل أعضاء من مجموعة لـ آخرى 🛗", data="invite_member"),
                ],
                [
                    Button.url("⎉ ℤ𝕋ℍ𝕆ℕ 𝔸𝕊𝕊𝕀𝕊𝕋𝔸ℕ𝕋 ⎉", "https://t.me/ZThon"),
                ],
            ]
            return await event.reply(f"**- مـرحباً بـك عزيـزي  {mention} 🧑🏻‍💻**\n\n**- في قسم بوت تحكـم زدثــون 🕹**\n**- خدمات تحكـم بالحسابات ممطروقـه 💡**\n**- لـ اول مـرة ع سـورس يوزربوت 🥇**\n**- اولاً قم باضافة حساباتك للبوت عبر تسجيل جلسة بايروجرام او تيليثون ⬇️**", buttons=buttons)
        
        
@tgbot.on(events.callbackquery.CallbackQuery())
async def start_lis(event):
    data = event.data.decode('utf-8')
    user_id = event.chat_id
    if data == "lllpyrogram":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسل الان كود جلسة بايروجرام**\n**- بوت استخراج تيرمكس بايروجرام @T66bot**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            txt = await x.get_response()
            if "/stop" in txt.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            session = txt.text
            try:
                Convert_sess = MangSession.PYROGRAM_TO_TELETHON(session)
            except:
                return await x.send_message("**- كود تيرمكس بايروجرام .. غير صحيح ✖️**")
            iphon = await userinfo(Convert_sess)
            data = {"phone_number": iphon, "two-step": "لايوجد", "session": Convert_sess}
            acc = db.get("accounts")
            acc.append(data)
            db.set("accounts", acc)
            with open('session.txt', 'w') as file:
                file.write(str(session) + '\n')
            await x.send_message("**- تم حفظ الجلسة بنجاح ✅**\n**- واضافة الحساب للبوت 🚹**")
            folder_path = f"./database"
            zip_file_name = f"database.zip"
            zip_file_nam = f"database"
            try:
                shutil.make_archive(zip_file_nam, 'zip', folder_path)
                with open(zip_file_name, 'rb') as zip_file:
                    await tgbot.send_file(user_id, zip_file, caption="**• ملف خزن البوت آخر تحديث 💾☑️**\n\n**• ملاحظـات هامـة 💡**\n- هذه النسخه متجددة تأتيك بعد اضافة كل حساب للبوت تلقائياً 🛃\n- هيروكو تقوم بإعادة التشغيل كل 24 ساعة تلقائياً ⏳\n- تخزين البوت ينحذف مع كل إعادة تشغيل سواء انت تقوم بها او هيروكو 🗑\n- لذلك عندما تتفاجئ ان البوت فاضي من الحسابات 0⃣\n- في هذه الحالة كل ماعليك القيام به هو اعاده توجيه ملف آخر نسخه احتياطيه للبوت 🔁\n- وسوف يتم ارجاع تخزين الحسابات بسهوله للبوت بدون تعب او جهد ✔️", attributes=[DocumentAttributeFilename(file_name="database.zip")])
                os.remove(zip_file_name)
            except Exception as a:
                print(a)
    
    if data == "llltelethon":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسل الان كود جلسة تيليثـون**\n**- بوت استخراج كـود تيليثـون @T66bot**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            txt = await x.get_response()
            if "/stop" in txt.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            session = txt.text
            iphon = await userinfo(session)
            data = {"phone_number": iphon, "two-step": "لايوجد", "session": session}
            acc = db.get("accounts")
            acc.append(data)
            db.set("accounts", acc)
            with open('session.txt', 'w') as file:
                file.write(str(session) + '\n')
            await x.send_message("**- تم حفظ الجلسة بنجاح ✅**\n**- واضافة الحساب للبوت 🚹**")
            folder_path = f"./database"
            zip_file_name = f"database.zip"
            zip_file_nam = f"database"
            try:
                shutil.make_archive(zip_file_nam, 'zip', folder_path)
                with open(zip_file_name, 'rb') as zip_file:
                    await tgbot.send_file(user_id, zip_file, caption="**• ملف خزن البوت آخر تحديث 💾☑️**\n\n**• ملاحظـات هامـة 💡**\n- هذه النسخه متجددة تأتيك بعد اضافة كل حساب للبوت تلقائياً 🛃\n- هيروكو تقوم بإعادة التشغيل كل 24 ساعة تلقائياً ⏳\n- تخزين البوت ينحذف مع كل إعادة تشغيل سواء انت تقوم بها او هيروكو 🗑\n- لذلك عندما تتفاجئ ان البوت فاضي من الحسابات 0⃣\n- في هذه الحالة كل ماعليك القيام به هو اعاده توجيه ملف آخر نسخه احتياطيه للبوت 🔁\n- وسوف يتم ارجاع تخزين الحسابات بسهوله للبوت بدون تعب او جهد ✔️", attributes=[DocumentAttributeFilename(file_name="database.zip")])
                os.remove(zip_file_name)
            except Exception as a:
                print(a)
            
    if data == "back" or data == "cancel":
        buttons = [
            [
                Button.inline("عدد حسابات البوت ♾", data="lllget_accounts_count"),
            ],
            [
                Button.inline("تسجيل عبر الرقم 📲", data="addd"),
            ],
            [
                Button.inline("تسجيل جلسة بايروجرام", data="lllpyrogram"),
                Button.inline("تسجيل جلسة تيليثون", data="llltelethon"),
            ],
            [
                Button.inline("جلب جلسة حساب 📤", data="lllget_session"),
            ],
            [
                Button.inline("مغادرة قناة", data="lllleave_channel"),
                Button.inline("الانضمام لقناة", data="llljoin_channel"),
            ],
            [
                Button.inline("جلب نسخة احتياطية 💾", data="lllzip_all"),
            ],
            [
                Button.inline("مغادرة القنوات", data="lllleave_all"),
                Button.inline("فحص الحسابات", data="lllcheck"),
            ],
            [
                Button.inline("جلب روابط السحوبات 🎁", data="lllget_gift"),
            ],
            [
                Button.inline("ارسال رسالة لـ شخص | جروب 💌", data="lllsend_txt"),
            ],
            [
                Button.inline("رشق تفاعل ستوري ❤️", data="reaction_story"),
                Button.inline("رشق مشاهدات ستوري 👀", data="view_story"),
            ],
            [
                Button.inline("رشق مشاهدات منشور 👁‍🗨", data="lllview_post"),
            ],
            [
                Button.inline("رشق تعليقات (كومنتات) 💬", data="send_comment"),
            ],
            [
                Button.inline("رشق تفاعل محدد ❤️", data="reaction_one_pyro"),
                Button.inline("رشق تفاعل عشوائي 🎨", data="reaction_tree_pyro"),
            ],
            [
                Button.inline("رشق اصوات مسابقات 🗳", data="lllvote_liker"),
            ],
            [
                Button.inline("رشق استفتاء 🪧", data="vote_poll"),
            ],
            [
                Button.inline("الاشتراك برابط الدعوة لـ بوت 🖇", data="sub_bots"),
            ],
            [
                Button.inline("نقـل أعضاء من مجموعة لـ آخرى 🛗", data="invite_member"),
            ],
            [
                Button.url("⎉ ℤ𝕋ℍ𝕆ℕ 𝔸𝕊𝕊𝕀𝕊𝕋𝔸ℕ𝕋 ⎉", "https://t.me/ZThon"),
            ],
        ]
        await event.edit(f"**- مـرحباً بـك مجـدداً 🧑🏻‍💻**\n\n**- في قسم بوت تحكـم زدثــون 🕹**\n**- خدمات تحكـم بالحسابات ممطروقـه 💡**\n**- لـ اول مـرة ع سـورس يوزربوت 🥇**\n**- تحكـم بالخدمـات عبـر الازرار بالاسفـل ⬇️**", buttons=buttons)
    if data == "addd":
        #if event.query.user_id not in ZThonDev:
            #return await event.answer("⤶ عـذراً عـزيـزي 🤷🏻‍♀\n⤶ هـذه الخدمة قيد التحديث حالياً 🛠\n⤶ قم باضافة الحسابات عبـر الـزر 👇\n\n⤶ تسجيل جلسة بايروجرام\nاو\n⤶ تسجيل جلسة تليثون", cache_time=0, alert=True)
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسل الان رقمك مع رمز الدولة**\n**- مثـال : +964000000000**")
            try:
                txt = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if txt.text.startswith("**"):
                txt = txt.text.replace("**", "")
            if not txt.text.startswith("+"):
                await x.send_message("**- اعد كتابة الرقم بشكل صحيح**\n**- يرجى اضافة كود رمز الدولة +**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            phone_number = txt.text.replace(" ", "")
            password=None
            api_id = int(API_ID)
            api_hash = API_HASH
            app = TelegramClient(StringSession(), api_id=api_id, api_hash=api_hash)
            await app.connect()
            password=None
            try:
                code = await app.send_code_request(phone_number)
            except ApiIdInvalidError as a:
                await x.send_message(str(a))
                return
            except PhoneNumberInvalidError as a:
                await x.send_message(str(a))
                return
            #except Exception as a:
                #await x.send_message("." + str(a))
                #return
            await x.send_message("- تم ارسال كود التحقق الخاص بك على حسابك على تليجرام.\n\n- ارسل الكود بالتنسيق التالي : 1 2 3 4 5")
            try:
                txt = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /start  لـ البـدء مـن جديـد**")
                return
            if not " " in txt.text:
                await x.send_message("**- اعد كتابة الكود بشكل صحيح**\n**- يرجى ادخال الكود بالشكل: 1 2 3 4 5 مع موجود مسافة بين كل رقم والاخر**\n**- ارسـل  /start  لـ البـدء مـن جديـد**")
                return
            code = txt.text.replace(" ", "")
            try:
                await app.sign_in(phone_number, code, password=None)
                string_session = app.session.save()
                data = {"phone_number": phone_number, "two-step": "لا يوجد", "session": string_session}
                accounts = db.get("accounts")
                accounts.append(data)
                db.set("accounts", accounts)
                return await x.send_message("**- تم حفظ الحساب بنجاح ✅**")
            except (PhoneCodeInvalidError):
                await x.send_message("ᴛʜᴇ ᴏᴛᴩ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs **ᴡʀᴏɴɢ.**")
                return
            except (PhoneCodeExpiredError):
                await x.send_message("ᴛʜᴇ ᴏᴛᴩ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs **ᴇxᴩɪʀᴇᴅ.**")
                return
            except (SessionPasswordNeededError):
                await x.send_message("**- ارسل رمز التحقق بخطوتين الخاص بحسابك**")
                try:
                    txt = await x.get_response()
                except TimeoutError:
                    await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                    return
                password = txt.text
                try:
                    await app.sign_in(password=password)
                except (PasswordHashInvalidError):
                    await x.send_message("ᴛʜᴇ ᴩᴀssᴡᴏʀᴅ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs ᴡʀᴏɴɢ.")
                    return
                string_session = app.session.save()
                data = {"phone_number": phone_number, "two-step": password, "session": string_session}
                accounts = db.get("accounts")
                accounts.append(data)
                db.set("accounts", accounts)
                return await x.send_message("**- تم حفظ الحساب بنجاح ✅**")
    if data == "lllget_accounts_count":
        acc = db.get("accounts")
        await event.answer(f"- عدد الحسابات المسجلة ; {len(acc)}", alert=True)
    if data == "lllget_gift":
        await event.answer(f"- تم بدا جلب روابط المميز من الحسابات برجاء انتظار اشعار", alert=True)
        acc = db.get("accounts")
        count = 0
        for i in acc:
            x = await get_gift(i["session"])
            if x != False:
                text = f"**• رابط تليجرام مميز جديد 🎁**\n\n**• الرابط :** https://t.me/giftcode/{x}\n**• رقم الهاتف :** `{i['phone_number']}`"
                count += 1
                await tgbot.send_message(admin, text)
            else:
                pass
        await tgbot.send_message(admin, f"**- تم الانتهاء من فحص الحسابات ☑️**\n**- تم ايجاد** {count} **رابط 🎈**")
    if data == "llljoin_channel":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان يـوزر او رابـط القنـاة**\n**- التي تريـد الانضمـام لهـا بكـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "@" not in ch.text:
                if "/t.me/" not in ch.text:
                    await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل يوزر او رابط القنـاة بشكل صحيح**")
                    return 
            channel = ch.text.replace("https://t.me/", "").replace("http://t.me/", "").replace("@", "")
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ الانضمام من {len(acc)} حساب**")
            for i in acc:
                xx = await join_channel(i["session"], channel)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانضمـام لـ القنـاة .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "lllleave_channel":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان يـوزر او رابـط القنـاة**\n**- التي تريـد المغـادرة منهـا بكـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "@" not in ch.text:
                if "/t.me/" not in ch.text:
                    await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل يوزر او رابط القنـاة بشكل صحيح**")
                    return 
            channel = ch.text.replace("https://t.me/", "").replace("http://t.me/", "").replace("@", "")
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ المغادرة من {len(acc)} حساب**")
            for i in acc:
                xx = await leave_channel(i["session"], channel)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم مغـادرة القنـاة .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "lllvote_liker":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط منشـور المسابقـة**\n**- التي تريـد التصـويت لهـا مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            urls = re.findall(r'https://t\.me/(.*?)/(\d+)', ch.text)  # البحث عن روابط واستخراج الأجزاء المهمة
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            await x.send_message(f"**- ارسل الان وقت التأخير بين كل طلب والاخر ⏳\n**- ارسل عدد بين 200 - 0 ثانية ⏱**")
            try:
                tnn = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in tnn.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            try:
                tmm = int(tnn.text)
            except:
                await x.send_message("• رجاء ارسل الوقت بشكل صحيح")
                return
            if tmm < 0 or tmm > 200:
                await x.send_message("• رجاء ارسل وقت الرشق بين 0 و 200")
                return
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ التصويت من {len(acc)} حساب 🚹**\n**- وقت التأخير بين كل صوت والاخر** {tmm} **ثانية ⏳**\n\n**- ملاحظـه ⚠️**\nلا تقم بعمل إعادة تشغيل او تحديث لكي لا تتوقف العملية")
            for i in acc:
                xx = await lllvote_liker(i["session"], chn, msg_id, tmm)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن التصـويت .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "reaction_tree":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط المنشـور**\n**- التي تريـد رشـق تفاعـلات لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            urls = re.findall(r'https://t\.me/(.*?)/(\d+)', ch.text)  # البحث عن روابط واستخراج الأجزاء المهمة
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ رشـق التفاعـلات من {len(acc)} حساب**")
            for i in acc:
                xx = await reaction_tree(i["session"], chn, msg_id)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن رشـق التفاعـلات .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "reaction_one":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط المنشـور**\n**- التي تريـد رشـق تفاعـلات لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            urls = re.findall(r'https://t\.me/(.*?)/(\d+)', ch.text)  # البحث عن روابط واستخراج الأجزاء المهمة
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            await x.send_message("**- ارسـل الان ايمـوجي التفاعـل**\n**- الذي تريـد رشـقـه للمنشـور مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                imoji = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in imoji.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            emoji = imoji.message
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ رشـق تفاعـل {emoji} من {len(acc)} حساب**")
            for i in acc:
                xx = await reaction_one(i["session"], chn, msg_id, emoji)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن رشـق تفاعـل {emoji} .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "reaction_one_pyro":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط المنشـور**\n**- التي تريـد رشـق تفاعـلات لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                url = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in url.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in url.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            urls = re.findall(r'https://t\.me/(.*?)/(\d+)', url.text)  # البحث عن روابط واستخراج الأجزاء المهمة
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            await x.send_message("**- ارسـل الان ايمـوجي التفاعـل**\n**- الذي تريـد رشـقـه للمنشـور مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                imoji = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in imoji.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            rections = imoji.message
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ رشـق تفاعـل {rections} من {len(acc)} حساب**")
            for i in acc:
                try:
                    sessions_string = MangSession.TELETHON_TO_PYROGRAM(i["session"])
                except:
                    return
                xx = await RECTIONS_MESSAGE(sessions_string, chn, msg_id, rections)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن رشـق تفاعـل {rections} .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "reaction_tree_pyro":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- هـذا القسـم تحت التحديث حالياً ♻️**\n**- سوف يتوفر قريباً بالتحديثات الجايه 🔰**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
            return
            await x.send_message("**- ارسـل الان رابـط المنشـور**\n**- التي تريـد رشـق تفاعـلات لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                url = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in url.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in url.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ رشـق التفاعـلات من {len(acc)} حساب**")
            for i in acc:
                try:
                    sessions_string = MangSession.TELETHON_TO_PYROGRAM(i["session"])
                except:
                    return
                xx = await reaction_tree_pyro(sessions_string, chn, msg_id)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن رشـق التفاعـلات .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "lllview_post":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط المنشـور**\n**- التي تريـد رشـق مشاهـدات لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط المنشور بشكل صحيح**")
                return
            urls = re.findall(r'https://t\.me/(.*?)/(\d+)', ch.text)  # البحث عن روابط واستخراج الأجزاء المهمة
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ رشق المشاهدات من {len(acc)} حساب**")
            for i in acc:
                xx = await lllview_post(i["session"], chn, msg_id)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن رشـق المنشـور .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "view_story":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط الستـوري**\n**- التي تريـد رشـق مشـاهـدات لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                url = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in url.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in url.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط الستـوري بشكل صحيح**")
                return
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ رشـق المشـاهـدات من {len(acc)} حساب**")
            for i in acc:
                xx = await view_story(i["session"], url)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن رشـق مشـاهـدات الستـوري .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "reaction_story":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط الستـوري**\n**- التي تريـد رشـق تفـاعـل ❤️ لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                url = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in url.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in url.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط الستـوري بشكل صحيح**")
                return
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ رشـق تفـاعـل ❤️ من {len(acc)} حساب**")
            for i in acc:
                xx = await reaction_story(i["session"], url)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن رشـق تفـاعـل ❤️ للستـوري .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "sub_bots":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط رابـط الدعـوة**\n**- التي تريـد الاشتـراك فيـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**\n\n**- مـلاحظـة هـامــه :**\n¹- قبل استخدام هذا الامر قم بالذهاب اولاً للبوت الهدف\n²- تحقق من قنوات الاشتراك الاجباري وقم باخذ يوزراتها\n³- بعدها استخدم امر الانضمام لها عبر زر الانضمام لقناة\n⁴- بعدها قم باستخدام الانضمام لرابط الدعوة")
            try:
                ch = await x.get_response()
                url = ch.text
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in ch.text and "start=" not in ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            bot_id, user_id = url.split("?start=")[0].split("/")[-1], url.split("?start=")[1]
            #bot_username = invite_link.split("=")[0]
            #user_id = invite_link.split("=")[1]
            #if user_id and bot_username:
            try:
                tex = "/start " + user_id
                channel = "@" + bot_id
            except ValueError:
                tex = "/start " + user_id
                channel = "@" + bot_id
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ الاشتـراك من {len(acc)} حساب**")
            for i in acc:
                try:
                    sessions_string = MangSession.TELETHON_TO_PYROGRAM(i["session"])
                except:
                    return
                xx = await sub_bots(sessions_string, channel, tex)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن الاشتـراك .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "lllsend_txt":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان يـوزر الشخـص او الجـروب**\n**- التي تريـد إرسـال رسـالة لـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                chh = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in chh.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "@" not in chh.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل يوزر الشخص/ الجروب بشكل صحيح**")
                return
            if "/stop" in chh.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            ch_user = chh.text.replace("@", "")
            await x.send_message(f"**- ارسل الان الرسالة التي تريد ارسالها لـ** @{ch_user} 🚹\n**- سوف يتم ارسالها من جميع الحسابات 💌**")
            try:
                txt = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in txt.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ الارسال من {len(acc)} حساب**")
            for i in acc:
                xx = await send_txt(i["session"], ch_user, txt)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم إرسـال الرسـالة .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "send_comment":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط المنشـور الذي تريد التعليق عليـه**\n**- انسخ رابط المنشور من داخل مجموعة المناقشة**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**/n/n**- ملاحظـه هامـه ⚠️**\nيجب عليك ان تنسخ رابط المنشور\nمن مجموعة المناقشة وليس من القناة نفسها")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            urls = re.findall(r'https://t\.me/(.*?)/(\d+)', ch.text)  # البحث عن روابط واستخراج الأجزاء المهمة
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            await x.send_message(f"**- ارسل الان عدد التعليقات او الحسابات 🖥**\n**- التي تريد التعليـق منهـا 🏑**\n**- ارسل عدد فقط**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ptxt = await x.get_response()
                pnn = ptxt.text
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in pnn or "/start" in pnn:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            acc = db.get("accounts")
            if int(pnn) > len(acc):
                await x.send_message("**- عـذراً .. عـزيـزي**\n**- العـدد المدخـل اكبـر مـن عـدد حساباتك في البوت**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            pi = int(pnn)
            await x.send_message(f"**- ارسل الان نص التعليـق**\n**- الذي تريد التعليـق فيه من** {pi} **حسـاب**\n**- ارسل نص لايزيـد عـن 100 حـرف**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                txt = await x.get_response()
                tmsg = txt.text
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in pnn or "/start" in pnn:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if len(tmsg) > 100:
                await x.send_message("**- النـص طويـل جـداً .. اطـول من 100 حـرف**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            acc = db.get("accounts")
            if int(pnn) > len(acc):
                await x.send_message("**- عـذراً .. عـزيـزي**\n**- العـدد المدخـل اكبـر مـن عـدد حساباتك في البوت**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            await x.send_message(f"**- ارسل الان وقت التأخير بين كل طلب والاخر ⏳\n**- ارسل عدد بين 200 - 0 ثانية ⏱**")
            try:
                tnn = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in tnn.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            try:
                tmm = int(tnn.text)
            except:
                await x.send_message("• رجاء ارسل الوقت بشكل صحيح")
                return
            if tmm <0:
                await x.send_message("• رجاء ارسل وقت الرشق بين 0 و 200")
                return
            if tmm >200:
                await x.send_message("• رجاء ارسل وقت الرشق بين 0 و 200")
                return
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ التعليـق من {pi} حساب 🚹**\n**- وقت التأخير بين كل تعليـق والاخر** {tmm} **ثانية ⏳**\n\n**- ملاحظـه ⚠️**\nلا تقم بعمل إعادة تشغيل او تحديث لكي لا تتوقف العملية")
            for i in acc:
                try:
                    sessions_string = MangSession.TELETHON_TO_PYROGRAM(i["session"])
                except:
                    return
                xx = await send_comment(sessions_string, chn, msg_id, pi, tmsg, tmm)
                if xx is True:
                    true += 1
                else:
                    false += 1
                if true >= pi:
                    break
            await x.send_message(f"**- تم الانتهـاء مـن التعليـق ع المنشـور .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "vote_poll":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط منشـور المسابقـة**\n**- التي تريـد التصـويت لهـا مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                ch = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            urls = re.findall(r'https://t\.me/(.*?)/(\d+)', ch.text)  # البحث عن روابط واستخراج الأجزاء المهمة
            if urls:
                chn = urls[0][0]  # استخراج القيمة الأولى من الرابط للمتغير chn
                msg_id = int(urls[0][1])  # استخراج القيمة الثانية من الرابط للمتغير msg_id
            await x.send_message(f"**- ارسل الان رقم الاجابة او الخيار 🖥**\n**- الذي تريد التصويت عليه من جميع الحسابات 🏑**\n**- ارسل عدد فقط مثل 1 للخيار الاول او 2 للخيار الثاني وهكذا**")
            try:
                ptxt = await x.get_response()
                pnn = ptxt.text
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in pnn or "/start" in pnn:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if pnn == "1":
                pi = int(0)
            elif pnn == "2":
                pi = int(1)
            elif pnn == "3":
                pi = int(2)
            elif pnn == "4":
                pi = int(3)
            elif pnn == "5":
                pi = int(4)
            elif pnn == "6":
                pi = int(5)
            elif pnn == "7":
                pi = int(6)
            elif pnn == "8":
                pi = int(7)
            elif pnn == "9":
                pi = int(8)
            elif pnn == "10":
                pi = int(9)
            else:
                await x.send_message("**- ارسل الاختيار بشكل صحيح**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            await x.send_message(f"**- ارسل الان وقت التأخير بين كل طلب والاخر ⏳\n**- ارسل عدد بين 200 - 0 ثانية ⏱**")
            try:
                tnn = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in tnn.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            try:
                tmm = int(tnn.text)
            except:
                await x.send_message("• رجاء ارسل الوقت بشكل صحيح")
                return
            if tmm <0:
                await x.send_message("• رجاء ارسل وقت الرشق بين 0 و 200")
                return
            if tmm >200:
                await x.send_message("• رجاء ارسل وقت الرشق بين 0 و 200")
                return
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ التصويت من {len(acc)} حساب 🚹**\n**- وقت التأخير بين كل صوت والاخر** {tmm} **ثانية ⏳**\n\n**- ملاحظـه ⚠️**\nلا تقم بعمل إعادة تشغيل او تحديث لكي لا تتوقف العملية")
            for i in acc:
                try:
                    sessions_string = MangSession.TELETHON_TO_PYROGRAM(i["session"])
                except:
                    return
                xx = await vote_poll(sessions_string, chn, msg_id, pi, tmm)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن التصـويت .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == 'lllzip_all':
        folder_path = f"./database"
        zip_file_name = f"database.zip"
        zip_file_nam = f"database"
        try:
            shutil.make_archive(zip_file_nam, 'zip', folder_path)
            with open(zip_file_name, 'rb') as zip_file:
                await tgbot.send_file(user_id, zip_file, caption="**• ملف خزن البوت آخر تحديث 💾☑️**\n\n**• ملاحظـات هامـة 💡**\n- هذه النسخه متجددة تأتيك بعد اضافة كل حساب للبوت تلقائياً 🛃\n- هيروكو تقوم بإعادة التشغيل كل 24 ساعة تلقائياً ⏳\n- تخزين البوت ينحذف مع كل إعادة تشغيل سواء انت تقوم بها او هيروكو 🗑\n- لذلك عندما تتفاجئ ان البوت فاضي من الحسابات 0⃣\n- في هذه الحالة كل ماعليك القيام به هو اعاده توجيه ملف آخر نسخه احتياطيه للبوت 🔁\n- وسوف يتم ارجاع تخزين الحسابات بسهوله للبوت بدون تعب او جهد ✔️", attributes=[DocumentAttributeFilename(file_name="database.zip")])
            os.remove(zip_file_name)
        except Exception as a:
            print(a)
    if data == "lllleave_all":
        buttons = [
            [
                Button.inline("تأكيد ✅", data="leave_all_channels"),
                Button.inline("الغاء ❌", data="cancel"),
            ]
        ]
        await event.edit("**- هل تود فعلاً تأكيد المغادرة من كل الحسابات؟**", buttons=buttons)
    if data == "leave_all_channels":
        async with bot.conversation(event.chat_id) as x:
            acc = db.get("accounts")
            await event.edit(f"**- جـارِ مغادرة كل القنوات من {len(acc)} حساب, سيصلك اشعار عند الانتهاء **")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ المغادرة من {len(acc)} حساب**")
            for i in acc:
                xx = await leave_all(i["session"])
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم مغـادرة القنـوات .. بنجـاح ☑️**\n\n**- نجاح :** {true} ✅\n**- فشل :** {false} ❌")
    if data == "lllcheck":
        buttons = [
            [
                Button.inline("تأكيد ✅", data="check_accounts"),
                Button.inline("الغاء ❌", data="cancel"),
            ]
        ]
        await event.edit("**- هل تود بدء عملية فحص كل الحسابات ؟!**", buttons=buttons)
    if data == "check_accounts":
        async with bot.conversation(event.chat_id) as x:
            acc = db.get("accounts")
            await event.edit(f"**- جـارِ فحص جميع الحسابات من إجمالي {len(acc)} حساب**\n**- سيصلك اشعار عند الانتهاء**")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ فحص {len(acc)} حساب**")
            for i in acc:
                Convert_sess = MangSession.TELETHON_TO_PYROGRAM(i["session"])
                xx = await check(Convert_sess, tgbot, user_id)
                if xx is True:
                    true += 1
                else:
                    false += 1
                    acc.remove(i)
                    db.set("accounts", acc)
                await event.edit(f"**- جـارِ فحص الحسابات . . .**\n\n- حسابات شغالة : {true} ✅\n- حسابات محذوفة : {false} ❌")
            await x.send_message(f"**- تم انتهاء فحص الحسابات بنجاح ✅**\n\n- حسابات شغالة : {true}\n- حسابات محذوفة : {false}")
    if data == "lllget_session":
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسل الان رقم هاتف الحساب المسجل في البوت**\n**- لـ جلب كود تيرمكس الخاص به**")
            try:
                txt = await x.get_response()
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in txt.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            phone_number = txt.text.replace(" ", "")
            acc = db.get("accounts")
            for i in acc:
                if phone_number == i['phone_number']:
                    text = f"• رقم الهاتف : {phone_number}\n\n• كود تيرمكس : `{i['session']}"
                    await x.send_message(text)
                    return
            await x.send_message("**- لم يتم العثور على هذا الرقم ؟!**\n**- ضمن قائمة حسابات البوت**")
    if data == "invite_member":
        if event.query.user_id not in ZThonDev:
            return await event.answer("- هـذه الخدمـة قيـد التحـديث .. حاليـاً", alert=False)
        async with bot.conversation(event.chat_id) as x:
            await x.send_message("**- ارسـل الان رابـط جروبك**\n**- الذي تريـد نقـل الاعضـاء له مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                to_ch = await x.get_response()
                too_ch = to_ch.text
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in to_ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in to_ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط منشور المسابقه بشكل صحيح**")
                return
            if too_ch.startswith('https://t.me/+'):
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط الجروب بشكل صحيح**\n\n**- ملاحظـات هامـه ℹ️**\n**- يجب ان يكون جروب عام وليس خاص**\n**- يجب ان يكون الرابط بالشكل التالي:**\nhttps://t.me/AAAl1l")
                return
            else:
                to_ch = too_ch.replace('https://t.me/', '')
            await x.send_message("**- ارسـل الان رابـط الجروب الهـدف**\n**- الذي تريـد سحب الاعضـاء منـه مـن كـل الحسـابات**\n\n**- لـ الالغـاء والخـروج ارسـل الامـر  /stop**")
            try:
                from_ch = await x.get_response()
                froom_ch = from_ch.text
            except TimeoutError:
                await x.send_message("**- لقـد انتهـى الوقت**\n**- يرجى البدء من جديد مرة أخرى**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/stop" in from_ch.text:
                await x.send_message("**- تم الالغاء .. بنجاح ✅**\n**- ارسـل  /control  لـ البـدء مـن جديـد**")
                return
            if "/t.me/" not in from_ch.text:
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط الجروب بشكل صحيح**\n\n**- ملاحظـات هامـه ℹ️**\n**- يجب ان يكون جروب عام وليس خاص**\n**- يجب ان يكون الرابط بالشكل التالي:**\nhttps://t.me/AAAl1l")
                return
            if froom_ch.startswith('https://t.me/+'):
                await x.send_message("**- عـذراً عـزيـزي ❌**\n**- ارسل رابط الجروب بشكل صحيح**\n\n**- ملاحظـات هامـه ℹ️**\n**- يجب ان يكون جروب عام وليس خاص**\n**- يجب ان يكون الرابط بالشكل التالي:**\nhttps://t.me/AAAl1l")
                return
            else:
                from_ch = froom_ch.replace('https://t.me/', '')
            await asyncio.sleep(3)
            acc = db.get("accounts")
            true, false = 0, 0
            await x.send_message(f"**- جـارِ عملية النقـل من {len(acc)} حساب 🚹**\n\n**- ملاحظـه ⚠️**\nلا تقم بعمل إعادة تشغيل او تحديث لكي لا تتوقف العملية")
            for i in acc:
                xx = await invite_member(i["session"], to_ch, from_ch)
                if xx is True:
                    true += 1
                else:
                    false += 1
            await x.send_message(f"**- تم الانتهـاء مـن نقـل الاعضـاء .. بنجـاح ☑️**\n\n**- نجاح من :** {true} **حساب** ✅\n**- فشل من :** {false} **حساب**  ❌")


@tgbot.on(events.NewMessage())
async def handle_zip_file(event):
    user_id = event.sender_id
    if not event.is_private:
        return
    if user_id != admin:
        return
    async with bot.conversation(event.chat_id) as x:
        try:
            if event.media and event.media.document:
                message = event.message
                file = await message.download_media()

                if not os.path.exists('olddata'):
                    os.makedirs('olddata')

                if not os.path.isdir('database'):
                    os.mkdir('database')

                with zipfile.ZipFile(file, 'r') as zip_ref:
                    zip_ref.extractall('database')
                    
                os.remove(file)
                await x.send_message('**- تم فك الضغط عن الملف 📤**\n**- جـارِ إستعـادة خـزن البـوت . . .**')
                olddb = uu('database/elhakem.ss', 'bot')
                accs = db.get("accounts")
                if db.exists("accounts") and len(db.get("accounts")) > 0:
                    await x.send_message(f'**- تم بنجـاح .. استعـادة** {len(db.get("accounts"))} **حساب 🚹**\n**- الى خـزن البوت الحالي 📂**')
                else: 
                    await x.send_message('**- عـذراً عـزيـزي 🤷🏻‍♀**\n**- هـذا الخـزن لا يحتـوي على أي حسـابات؟!**')
        except Exception as e:
            return


#@zzzzl1l
#https://t.me/ZThon