import sqlite3


class InteractionService:
    async def search_interaction(self, sql_query: str):
        content = ""
        with sqlite3.connect('~/HYCU/hycu-mcp/db/od4b.db') as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            if sql_query.startswith("CREATE"):
                raise ValueError("Operation not supported")
            elif sql_query.startswith("INSERT"):
                raise ValueError("Operation not supported")
            elif sql_query.startswith("SELECT"):
                rows = cursor.fetchall()
                for row in rows:
                    content += f'row\n'
                return content

    async def trigger_backup(self, source: str) -> bool:
        """Trigger backup for the user"""
        pass

    async def trigger_granular_restore(self, source: str, external_ids: list):
        """Trigger granular restore"""
        pass

