import json
import time
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA foreign_keys=ON")
        await self.conn.commit()

    def _conn(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Banco de dados não conectado.")
        return self.conn

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def init_schema(self) -> None:
        db = self._conn()
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER NOT NULL,
                chave TEXT NOT NULL,
                valor TEXT,
                PRIMARY KEY (guild_id, chave)
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                motivo TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS xp_users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                nivel INTEGER NOT NULL DEFAULT 0,
                last_xp_ts REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS level_rewards (
                guild_id INTEGER NOT NULL,
                nivel INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, nivel)
            );

            CREATE TABLE IF NOT EXISTS economy_users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                saldo INTEGER NOT NULL DEFAULT 0,
                last_daily TEXT,
                last_work_ts REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                preco INTEGER NOT NULL,
                descricao TEXT NOT NULL DEFAULT '',
                role_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS inventory_items (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS tickets (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )
        await db.commit()

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        cur = await self._conn().execute(query, params)
        await self._conn().commit()
        return cur

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        async with self._conn().execute(query, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        async with self._conn().execute(query, params) as cur:
            return await cur.fetchall()

    async def set_setting(self, guild_id: int, chave: str, valor: Any) -> None:
        if not isinstance(valor, str):
            valor = json.dumps(valor, ensure_ascii=False)
        await self.execute(
            "INSERT INTO guild_settings (guild_id, chave, valor) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, chave) DO UPDATE SET valor=excluded.valor",
            (guild_id, chave, valor),
        )

    async def get_setting(self, guild_id: int, chave: str, default: Any = None) -> Any:
        row = await self.fetchone("SELECT valor FROM guild_settings WHERE guild_id=? AND chave=?", (guild_id, chave))
        if row is None:
            return default
        valor = row["valor"]
        if valor is None:
            return default
        try:
            return json.loads(valor)
        except Exception:
            return valor

    async def all_settings(self, guild_id: int) -> dict[str, Any]:
        rows = await self.fetchall("SELECT chave, valor FROM guild_settings WHERE guild_id=?", (guild_id,))
        data: dict[str, Any] = {}
        for row in rows:
            try:
                data[row["chave"]] = json.loads(row["valor"])
            except Exception:
                data[row["chave"]] = row["valor"]
        return data

    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, motivo: str) -> int:
        cur = await self.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, motivo, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, motivo, int(time.time())),
        )
        return cur.lastrowid

    async def remove_warning(self, guild_id: int, warning_id: int) -> bool:
        cur = await self.execute("DELETE FROM warnings WHERE guild_id=? AND id=?", (guild_id, warning_id))
        return cur.rowcount > 0

    async def get_warnings(self, guild_id: int, user_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY created_at DESC",
            (guild_id, user_id),
        )

    @staticmethod
    def level_from_xp(xp: int) -> int:
        return int((xp / 100) ** 0.5)

    async def add_xp(self, guild_id: int, user_id: int, amount: int, cooldown: int) -> tuple[int, int, bool]:
        now = time.time()
        row = await self.fetchone("SELECT xp, nivel, last_xp_ts FROM xp_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        if row and now - float(row["last_xp_ts"]) < cooldown:
            return int(row["xp"]), int(row["nivel"]), False
        xp = int(row["xp"]) if row else 0
        old_level = int(row["nivel"]) if row else 0
        xp += max(0, amount)
        new_level = self.level_from_xp(xp)
        await self.execute(
            "INSERT INTO xp_users (guild_id, user_id, xp, nivel, last_xp_ts) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, nivel=excluded.nivel, last_xp_ts=excluded.last_xp_ts",
            (guild_id, user_id, xp, new_level, now),
        )
        return xp, new_level, new_level > old_level

    async def change_xp(self, guild_id: int, user_id: int, amount: int) -> tuple[int, int]:
        row = await self.fetchone("SELECT xp FROM xp_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        xp = max(0, (int(row["xp"]) if row else 0) + amount)
        level = self.level_from_xp(xp)
        await self.execute(
            "INSERT INTO xp_users (guild_id, user_id, xp, nivel, last_xp_ts) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, nivel=excluded.nivel",
            (guild_id, user_id, xp, level, time.time()),
        )
        return xp, level

    async def set_level(self, guild_id: int, user_id: int, level: int) -> tuple[int, int]:
        level = max(0, level)
        xp = level * level * 100
        await self.execute(
            "INSERT INTO xp_users (guild_id, user_id, xp, nivel, last_xp_ts) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, nivel=excluded.nivel",
            (guild_id, user_id, xp, level, time.time()),
        )
        return xp, level

    async def get_rank(self, guild_id: int, user_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM xp_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))

    async def get_leaderboard_xp(self, guild_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM xp_users WHERE guild_id=? ORDER BY xp DESC LIMIT ?", (guild_id, limit)
        )

    async def set_level_reward(self, guild_id: int, level: int, role_id: int) -> None:
        await self.execute(
            "INSERT INTO level_rewards (guild_id, nivel, role_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, nivel) DO UPDATE SET role_id=excluded.role_id",
            (guild_id, level, role_id),
        )

    async def get_level_reward(self, guild_id: int, level: int) -> int | None:
        row = await self.fetchone("SELECT role_id FROM level_rewards WHERE guild_id=? AND nivel=?", (guild_id, level))
        return int(row["role_id"]) if row else None

    async def list_level_rewards(self, guild_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall("SELECT * FROM level_rewards WHERE guild_id=? ORDER BY nivel ASC", (guild_id,))

    async def ensure_wallet(self, guild_id: int, user_id: int) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO economy_users (guild_id, user_id, saldo) VALUES (?, ?, 0)",
            (guild_id, user_id),
        )

    async def get_balance(self, guild_id: int, user_id: int) -> int:
        await self.ensure_wallet(guild_id, user_id)
        row = await self.fetchone("SELECT saldo FROM economy_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        return int(row["saldo"] if row else 0)

    async def change_balance(self, guild_id: int, user_id: int, amount: int) -> int:
        await self.ensure_wallet(guild_id, user_id)
        balance = max(0, await self.get_balance(guild_id, user_id) + amount)
        await self.execute("UPDATE economy_users SET saldo=? WHERE guild_id=? AND user_id=?", (balance, guild_id, user_id))
        return balance

    async def transfer(self, guild_id: int, src_id: int, dst_id: int, amount: int) -> bool:
        if amount <= 0:
            return False
        src_balance = await self.get_balance(guild_id, src_id)
        if src_balance < amount:
            return False
        await self.change_balance(guild_id, src_id, -amount)
        await self.change_balance(guild_id, dst_id, amount)
        return True

    async def mark_daily(self, guild_id: int, user_id: int, date_str: str) -> bool:
        await self.ensure_wallet(guild_id, user_id)
        row = await self.fetchone("SELECT last_daily FROM economy_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        if row and row["last_daily"] == date_str:
            return False
        await self.execute("UPDATE economy_users SET last_daily=? WHERE guild_id=? AND user_id=?", (date_str, guild_id, user_id))
        return True

    async def can_work(self, guild_id: int, user_id: int, cooldown: int = 3600) -> bool:
        await self.ensure_wallet(guild_id, user_id)
        row = await self.fetchone("SELECT last_work_ts FROM economy_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        if row and time.time() - float(row["last_work_ts"] or 0) < cooldown:
            return False
        await self.execute("UPDATE economy_users SET last_work_ts=? WHERE guild_id=? AND user_id=?", (time.time(), guild_id, user_id))
        return True

    async def add_shop_item(self, guild_id: int, nome: str, preco: int, descricao: str, role_id: int | None = None) -> int:
        cur = await self.execute(
            "INSERT INTO shop_items (guild_id, nome, preco, descricao, role_id) VALUES (?, ?, ?, ?, ?)",
            (guild_id, nome, preco, descricao, role_id),
        )
        return cur.lastrowid

    async def remove_shop_item(self, guild_id: int, item_id: int) -> bool:
        cur = await self.execute("DELETE FROM shop_items WHERE guild_id=? AND id=?", (guild_id, item_id))
        return cur.rowcount > 0

    async def list_shop(self, guild_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall("SELECT * FROM shop_items WHERE guild_id=? ORDER BY preco ASC", (guild_id,))

    async def get_shop_item(self, guild_id: int, item_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM shop_items WHERE guild_id=? AND id=?", (guild_id, item_id))

    async def add_inventory(self, guild_id: int, user_id: int, item_id: int, quantidade: int = 1) -> None:
        await self.execute(
            "INSERT INTO inventory_items (guild_id, user_id, item_id, quantidade) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id, item_id) DO UPDATE SET quantidade=quantidade+excluded.quantidade",
            (guild_id, user_id, item_id, quantidade),
        )

    async def list_inventory(self, guild_id: int, user_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT inv.quantidade, shop.id, shop.nome, shop.descricao FROM inventory_items inv "
            "JOIN shop_items shop ON inv.item_id=shop.id WHERE inv.guild_id=? AND inv.user_id=? ORDER BY shop.nome ASC",
            (guild_id, user_id),
        )

    async def leaderboard_money(self, guild_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM economy_users WHERE guild_id=? ORDER BY saldo DESC LIMIT ?", (guild_id, limit)
        )
