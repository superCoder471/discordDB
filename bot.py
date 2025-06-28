import secret_token
TOKEN = secret_token.TOKEN
CHANNEL_ID = 1387969514712469554  # Replace with the ID of your channel

import discord
from discord.ext import commands
import json
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison, Token
from sqlparse.tokens import Keyword, DML, Whitespace, Punctuation


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# TABLE CACHE (thread name -> discord.Thread object)
table_threads = {}


class MyHelpCommand(commands.DefaultHelpCommand):
    def __init__(self):
        super().__init__()
        self.no_category = "**📖 dcDB Commands**"
    
    async def send_bot_help(self, mapping):
        help_message = """
**dcDB Help Menu**

**Table Operations:**
- `!create_table <table_name> <columns_json>` - Creates a new table with specified columns
  Example: `!create_table users ["id", "name", "age"]`

- `!list_tables` - Lists all available tables
- `!delete_table <table_name>` - Deletes a table

**Data Operations:**
- `!insert <table_name> <row_data_json>` - Inserts a row into a table
  Example: `!insert users {"name": "Alice", "age": 30}`
  Attachments: Use `"ATTACHMENT:0"` to reference the first attachment

- `!select_all <table_name>` - Shows all rows in a table
- `!select <table_name> <condition>` - Selects rows matching key=value
  Example: `!select users name=Alice`

- `!update <table_name> <condition> <new_data_json>` - Updates rows matching condition
  Example: `!update users name=Alice {"age": 31}`

- `!delete <table_name> <condition>` - Deletes rows matching condition

**Advanced Querying:**
- `!query <table_name> <sql_query>` - Run SQL-like queries
  Supported syntax:
  - `SELECT * FROM table WHERE condition`
  - Conditions: `=, !=, >, <, >=, <=, BETWEEN x & y, IS NULL, IS NOT NULL`
  - Combine with `AND`/`OR`
  Examples:
  `!query users "SELECT * FROM users WHERE age BETWEEN 25 & 35"`
  `!query users "SELECT name FROM users WHERE age > 30 AND profile_pic IS NOT NULL"`

**Other Commands:**
- `!help` - Shows this message

**Notes:**
- All data is stored as JSON
- Table names are case-sensitive
- Use attachments for images/files (reference with ATTACHMENT:index)
"""
        channel = self.get_destination()
        await channel.send(help_message)


@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    # Cache all existing threads into table_threads
    parent_channel = bot.get_channel(CHANNEL_ID)
    threads = parent_channel.threads
    for thread in threads:
        table_threads[thread.name] = thread
    print(f"Cached tables: {list(table_threads.keys())}")

bot.help_command = MyHelpCommand()

@bot.command()
async def create_table(ctx, table_name: str, *, columns: str):
    try:
        col_list = json.loads(columns)
        if not isinstance(col_list, list):
            await ctx.send("Columns must be a JSON list.")
            return
    except json.JSONDecodeError:
        await ctx.send("JSON format error in column list.")
        return

    parent_channel = bot.get_channel(CHANNEL_ID)
    thread = await parent_channel.create_thread(
        name=table_name,
        type=discord.ChannelType.public_thread,
        auto_archive_duration=1440
    )
    await thread.send(f"columns: {json.dumps(col_list)}")
    table_threads[table_name] = thread
    await ctx.send(f"Table `{table_name}` created.")

@bot.command()
async def insert(ctx, table_name: str, *, row_data: str):
    if table_name not in table_threads:
        await ctx.send("Table not found.")
        return

    try:
        row_dict = json.loads(row_data)
        if not isinstance(row_dict, dict):
            raise ValueError
    except:
        await ctx.send("JSON format error.")
        return

    used_indexes = set()

    # Replace ATTACHMENT:x values
    for key, val in row_dict.items():
        if isinstance(val, str) and val.startswith("ATTACHMENT:"):
            try:
                index = int(val.split(":")[1])
                attachment = ctx.message.attachments[index]
                row_dict[key] = attachment.url
                used_indexes.add(index)
            except:
                await ctx.send(f"Couldn't find attachment index {index} for key `{key}`.")
                return

    # Store unused attachments as _attachments
    leftover = [a.url for i, a in enumerate(ctx.message.attachments) if i not in used_indexes]
    if leftover:
        row_dict["_attachments"] = leftover

    thread = table_threads[table_name]
    await thread.send(json.dumps(row_dict, indent=2))
    await ctx.send(f"Inserted row into `{table_name}`.")



@bot.command()
async def select_all(ctx, table_name: str):
    if table_name not in table_threads:
        await ctx.send("Table not found.")
        return

    thread = table_threads[table_name]
    messages = [m async for m in thread.history(limit=100)]

    if len(messages) <= 1:
        await ctx.send("Table is empty.")
        return

    rows = []
    for msg in reversed(messages):
        # skip header message or any that start with 'columns:'
        if msg.content.startswith("columns:"):
            continue
        try:
            row = json.loads(msg.content)
            rows.append(row)
        except:
            rows.append({"error": "Invalid JSON row", "raw": msg.content})

    if not rows:
        await ctx.send("No data rows found.")
        return

    formatted = json.dumps(rows, indent=2)
    if len(formatted) > 1900:
        await ctx.send("Too many rows, sending as file:", file=discord.File(fp=bytes(formatted, 'utf-8'), filename="rows.json"))
    else:
        await ctx.send(f"```json\n{formatted}\n```")

@bot.command()
async def select(ctx, table_name: str, *, condition: str):
    if table_name not in table_threads:
        await ctx.send("Table not found.")
        return

    # Parse key=value
    if "=" not in condition:
        await ctx.send("Invalid condition. Use: key=value")
        return

    key, value = condition.split("=", 1)
    key, value = key.strip(), value.strip()

    thread = table_threads[table_name]
    messages = [m async for m in thread.history(limit=100)]

    rows = []
    for msg in reversed(messages):
        if msg.content.startswith("columns:"):
            continue
        try:
            row = json.loads(msg.content)
            if str(row.get(key)) == value:
                rows.append(row)
        except:
            continue

    if not rows:
        await ctx.send("No matching rows.")
        return

    formatted = json.dumps(rows, indent=2)
    if len(formatted) > 1900:
        await ctx.send("Too many rows, sending as file:", file=discord.File(fp=bytes(formatted, 'utf-8'), filename="results.json"))
    else:
        await ctx.send(f"```json\n{formatted}\n```")

@bot.command()
async def update(ctx, table_name: str, condition: str, *, new_data: str):
    if table_name not in table_threads:
        await ctx.send("Table not found.")
        return

    if "=" not in condition:
        await ctx.send("Invalid condition. Use: key=value")
        return

    key, value = condition.split("=", 1)
    key, value = key.strip(), value.strip()

    try:
        update_dict = json.loads(new_data)
        if not isinstance(update_dict, dict):
            raise ValueError
    except:
        await ctx.send("New data must be a valid JSON object.")
        return

    thread = table_threads[table_name]
    messages = [m async for m in thread.history(limit=100)]

    updated = False
    for msg in reversed(messages):
        if msg.content.startswith("columns:"):
            continue
        try:
            row = json.loads(msg.content)
            if str(row.get(key)) == value:
                row.update(update_dict)
                new_content = json.dumps(row, indent=2)
                if msg.author.id == bot.user.id:
                    await msg.edit(content=new_content)
                    await ctx.send(f"✅ Row with `{key}={value}` updated.")
                    updated = True
                else:
                    await ctx.send("Can't update: original message not sent by this bot.")
                break
        except:
            continue

    if not updated:
        await ctx.send("Row not found or update failed.")

@bot.command()
async def delete(ctx, table_name: str, *, condition: str):
    if table_name not in table_threads:
        await ctx.send("Table not found.")
        return

    if "=" not in condition:
        await ctx.send("Invalid condition. Use: key=value")
        return

    key, value = condition.split("=", 1)
    key, value = key.strip(), value.strip()

    thread = table_threads[table_name]
    messages = [m async for m in thread.history(limit=100)]

    deleted = False
    for msg in reversed(messages):
        if msg.content.startswith("columns:"):
            continue
        try:
            row = json.loads(msg.content)
            if str(row.get(key)) == value:
                if msg.author.id == bot.user.id:
                    await msg.delete()
                    await ctx.send(f"🗑️ Row with `{key}={value}` deleted.")
                    deleted = True
                else:
                    await ctx.send("Can't delete: message not sent by this bot.")
                break
        except:
            continue

    if not deleted:
        await ctx.send("Row not found or couldn't be deleted.")

@bot.command()
async def delete_table(ctx, table_name: str):
    if table_name not in table_threads:
        await ctx.send("Table not found.")
        return

    thread = table_threads[table_name]
    try:
        await thread.delete()
        del table_threads[table_name]
        await ctx.send(f"🗑️ Table `{table_name}` deleted.")
    except Exception as e:
        await ctx.send(f"Failed to delete thread: {e}")

@bot.command()
async def list_tables(ctx):
    if not table_threads:
        await ctx.send("No tables found.")
        return

    tables = "\n".join(f"- {name}" for name in table_threads.keys())
    await ctx.send(f"**Tables:**\n{tables}")


@bot.command()
async def query(ctx, table_name: str, *, sql: str):
    if table_name not in table_threads:
        await ctx.send("Table not found.")
        return

    try:
        # Remove surrounding quotes if present
        sql = sql.strip('"\'')
        
        # Debug print the received SQL
        print(f"Received SQL: {sql}")
        
        # Get all rows from the table
        thread = table_threads[table_name]
        messages = [m async for m in thread.history(limit=200)]
        
        rows = []
        for msg in reversed(messages):
            if msg.content.startswith("columns:"):
                continue
            try:
                rows.append(json.loads(msg.content))
            except:
                continue

        # Apply WHERE filtering if present
        where_index = sql.lower().find(" where ")
        if where_index >= 0:
            where_clause = sql[where_index + 7:].strip()
            print(f"WHERE clause to evaluate: {where_clause}")  # Debug
            rows = [row for row in rows if evaluate_condition(row, where_clause)]

        if not rows:
            await ctx.send("🔍 No matching rows found.")
            return

        # Send results
        formatted = json.dumps(rows, indent=2)
        if len(formatted) > 1900:
            await ctx.send("📄 Query results:", 
                          file=discord.File(fp=bytes(formatted, 'utf-8'), filename="results.json"))
        else:
            await ctx.send(f"```json\n{formatted}\n```")

    except Exception as e:
        await ctx.send(f"Error processing query: {str(e)}")


def evaluate_condition(row, condition):
    """Evaluates WHERE conditions against a row with maximum debugging"""
    print(f"\n=== NEW CONDITION EVALUATION ===")
    print(f"Full condition: {condition}")
    print(f"Row being evaluated: {row}")

    original_condition = condition
    condition_lower = condition.lower()
    
    # 1. Handle compound conditions first (AND/OR)
    if " and " in condition_lower:
        and_pos = condition_lower.find(" and ")
        left = original_condition[:and_pos].strip()
        right = original_condition[and_pos+5:].strip()
        print(f"[DEBUG] Found AND, splitting into: '{left}' AND '{right}'")
        left_result = evaluate_condition(row, left)
        right_result = evaluate_condition(row, right)
        print(f"[DEBUG] AND results: {left_result} AND {right_result} = {left_result and right_result}")
        return left_result and right_result
        
    if " or " in condition_lower:
        or_pos = condition_lower.find(" or ")
        left = original_condition[:or_pos].strip()
        right = original_condition[or_pos+4:].strip()
        print(f"[DEBUG] Found OR, splitting into: '{left}' OR '{right}'")
        left_result = evaluate_condition(row, left)
        right_result = evaluate_condition(row, right)
        print(f"[DEBUG] OR results: {left_result} OR {right_result} = {left_result or right_result}")
        return left_result or right_result
    
    # 2. Handle BETWEEN (after splitting compound conditions)
    between_index = condition_lower.find(" between ")
    if between_index > 0:
        try:
            column = original_condition[:between_index].strip()
            remaining = original_condition[between_index+8:].strip()
            
            # Find the & separator
            amp_index = remaining.find(" & ")
            if amp_index < 0:
                print(f"[DEBUG] BETWEEN missing required & separator")
                return False
                
            lower_str = remaining[:amp_index].strip().strip("'\"")
            upper_str = remaining[amp_index+3:].strip().strip("'\"")
            
            print(f"[DEBUG] BETWEEN expression: {column} BETWEEN {lower_str} & {upper_str}")
            
            row_value = row.get(column)
            print(f"[DEBUG] Row value for '{column}': {row_value} (type: {type(row_value)})")
            
            if row_value is None:
                print("[DEBUG] Row value is None, returning False")
                return False
                
            # Numeric comparison first
            try:
                lower_num = float(lower_str)
                upper_num = float(upper_str)
                row_num = float(row_value)
                print(f"[DEBUG] Numeric comparison: {lower_num} <= {row_num} <= {upper_num}")
                result = lower_num <= row_num <= upper_num
                print(f"[DEBUG] Numeric result: {result}")
                return result
            except ValueError:
                # String comparison
                print(f"[DEBUG] String comparison: '{lower_str}' <= '{row_value}' <= '{upper_str}'")
                result = str(lower_str) <= str(row_value) <= str(upper_str)
                print(f"[DEBUG] String result: {result}")
                return result
        except Exception as e:
            print(f"[DEBUG] BETWEEN evaluation error: {type(e).__name__}: {e}")
            return False
    
    # 3. Handle NULL checks
    if " is not null" in condition_lower:
        null_index = condition_lower.find(" is not null")
        column = original_condition[:null_index].strip()
        print(f"[DEBUG] IS NOT NULL check for column: {column}")
        value = row.get(column)
        result = not (value is None or str(value).strip().lower() in ('', 'null'))
        print(f"[DEBUG] IS NOT NULL result: {result}")
        return result
    
    if " is null" in condition_lower:
        null_index = condition_lower.find(" is null")
        column = original_condition[:null_index].strip()
        print(f"[DEBUG] IS NULL check for column: {column}")
        value = row.get(column)
        result = value is None or str(value).strip().lower() in ('', 'null')
        print(f"[DEBUG] IS NULL result: {result}")
        return result
    
    # 4. Handle basic operators
    operators = ['!=', '>=', '<=', '=', '>', '<']
    for op in operators:
        if op in condition:
            parts = condition.split(op, 1)
            if len(parts) == 2:
                column = parts[0].strip()
                value = parts[1].strip().strip("'\"")
                row_value = row.get(column)
                
                print(f"[DEBUG] Found operator {op} for column {column}")
                
                # Numeric comparison
                try:
                    value_num = float(value) if '.' in value else int(value)
                    row_num = float(row_value) if row_value is not None else None
                    if row_num is not None:
                        if op == '=': return row_num == value_num
                        if op == '!=': return row_num != value_num
                        if op == '>': return row_num > value_num
                        if op == '<': return row_num < value_num
                        if op == '>=': return row_num >= value_num
                        if op == '<=': return row_num <= value_num
                except ValueError:
                    pass
                
                # String comparison
                str_row = str(row_value).lower() if row_value is not None else ""
                str_value = str(value).lower()
                if op == '=': return str_row == str_value
                if op == '!=': return str_row != str_value
                if op == '>': return str_row > str_value
                if op == '<': return str_row < str_value
                if op == '>=': return str_row >= str_value
                if op == '<=': return str_row <= str_value
    
    print(f"[DEBUG] No matching operator found, returning False")
    return False


bot.run(TOKEN)