import json
import sqlite3
import logging

from mcp import types, stdio_server
from mcp.server import Server
import requests

logger = logging.getLogger("server-platform")
formatter = logging.Formatter(
    '%(asctime)s | %(name)s |  %(levelname)s: %(message)s')
logger.setLevel(logging.INFO)


async def trigger_backup(source: str) -> bool:
    """Trigger backup for the user"""
    return True


async def trigger_granular_restore(source: str, external_ids: list[str]) -> str:
    """Trigger granular restore"""
    restore_path = "/Users/debashisdas/HYCU/restore"
    if source.lower().replace(" ", "") in ['onedrive', 'drive']:
        print("restore one drive")
        content = {}
        with sqlite3.connect('/Users/debashisdas/HYCU/dbs/od4b.sql') as conn:
            for externalId in external_ids:
                cursor = conn.cursor()
                cursor.execute(
                    f'SELECT name, type, externalId, parentExternalId from backup_catalog_resources WHERE externalId = "{externalId}"')
                item = cursor.fetchone()
                print(f'Item information : {item}')
                if item[1] == 'folder':
                    content[externalId] = 'Folder restore is not supported yet, we only support file restore currently'
                    continue
                cursor.execute(
                    f'SELECT name, type, externalId, parentExternalId from backup_catalog_resources WHERE parentExternalId = "{externalId}"')
                versions = cursor.fetchall()
                content[externalId] = {}
                for version in versions:
                    url = f"http://10.26.2.94:5001/api/v2/objects/user/5864baa1-8cbe-40ef-a5a1-186e33a16a22/b!ywc0KqYlJ0qL1AvG6J72lYPEpf1LjdJHj5xiL01ATS_rAzd7iFRyT5KL-wW4DtDr/{externalId}/{version[2]}"
                    s = requests.Session()
                    try:
                        with s.get(url, stream=True) as resp:
                            resp.raise_for_status()
                            filename = f'{version[0]}-{item[0]}'
                            output_path = f'{restore_path}/{filename}'
                            with open(output_path, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=4096):
                                    if chunk:
                                        f.write(chunk)
                            logger.info(f'File {output_path} downloaded successfully')
                    except requests.exceptions.RequestException as e:
                        logger.error(f'Error during download: {e}')
                    content[externalId][version[2]] = f'Successfully downloaded {version[0]} for file {item[0]} at location {restore_path} with name {filename}'
        return json.dumps(content)
    elif source.lower().replace(" ", "") in ['outlook', 'mail']:
        content = {}
        with sqlite3.connect('/Users/debashisdas/HYCU/dbs/od4b.sql') as conn:
            for externalId in external_ids:
                cursor = conn.cursor()
                cursor.execute(
                    f'SELECT name, type, externalId, parentExternalId from backup_catalog_resources WHERE externalId = "{externalId}"')
                item = cursor.fetchone()
                print(f'Item information : {item}')
                content[externalId] = f'Successfully found and showing details of {item[0]} of type {item[1]}'
        return json.dumps(content)
    else:
        return json.dumps({"message": "Source is not correct. Source can either be OneDrive/Drive, Outlook/Mail"})


async def search_interaction(sql_query: str):
    content = ""
    with sqlite3.connect('/Users/debashisdas/HYCU/dbs/od4b.sql') as conn:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        if sql_query.upper().startswith("CREATE"):
            raise ValueError("Operation not supported")
        elif sql_query.upper().startswith("INSERT"):
            raise ValueError("Operation not supported")
        elif sql_query.upper().startswith("SELECT"):
            rows = cursor.fetchall()
            return json.dumps(rows)
        else:
            raise ValueError("sqlite select query expected")


description = (
    "HYCU is a backup solutions company which provide option to customer to backup any SAAS app like microsoft One Drive, Outlook, Teams, Sharepoint etc."
    "Here we are building an way to search items with respect to the module they want to search into. We have a common db across all modules for the purpose"
    " of uniformity. After searching the item the user is looking for user can trigger backup to take backup of the respective SAAS app or he can also trigger"
    "restore for the items he want. This restore happens based on the SAAS app and the externalId of the item present in backup_catalog_resources table. "
    "If User wants multiple items to restore our tool should get list of comma separated external ids of all those items. Always search backup_catalog_resources"
    "for any kind of search")


async def serve():
    app = Server("resource-server)")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="search",
                description=f"Sqlite query to search item (more details : {description})",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            ),
            types.Tool(
                name="backup",
                description=f"trigger backup for the SAAS app like one drive, outlook, teams (more details : {description})",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "moduleName": {"type": "string"}
                    }
                }
            ),
            types.Tool(
                name="restore",
                description=f"trigger restore for modules like one drive, outlook, teams with externalId list (mode details : {description})",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "moduleName": {"type": "string"},
                        "externalIds": {"type": "string"}
                    }
                }
            )
        ]

    @app.call_tool()
    async def call_tool(
            name: str,
            arguments: dict
    ) -> list[types.TextContent]:
        if name == "search":
            query = arguments["query"]
            content = await search_interaction(sql_query=query)
            if content is not None:
                return [types.TextContent(type="text", text=str(content))]
            else:
                raise ValueError("Sqlite query expected")
        elif name == "backup":
            module_name = arguments["moduleName"]
            ack = await trigger_backup(source=module_name)
            return [types.TextContent(type="text",
                                      text="backup was triggered successfully"
                                      if ack else
                                      "Something went wrong while triggering the backup. Please try after sometime.")]
        elif name == "restore":
            module_name = arguments["moduleName"]
            external_ids = arguments["externalIds"]
            try:
                result = await trigger_granular_restore(source=module_name, external_ids=external_ids.split(","))
                return [types.TextContent(type="text", text=str(result))]
            except:
                raise ValueError(f"Error was thrown during restore")
        raise ValueError(f"Tool not found : {name}")

    options = app.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, options, raise_exceptions=True)


def main():
    import asyncio
    asyncio.run(serve())


if __name__ == "__main__":
    main()
    # response = trigger_granular_restore("one drive", ["01I4IEIBZI4G7LD6O4HNE2JUQF536WNKIZ"])
