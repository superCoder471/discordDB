# DiscordDB

A database that lives in a Discord server. Pretty much SQLite but more buggy.

You can store anything in tables (which are threads) and then run semi-SQL queries on them.

## What It Does
- Makes a table by creating a Discord thread
- Stores each row as a JSON message
- Supports basic SQL operations (select, insert, update, delete)
- Supports basic SQL queries

## List of Commands (accessible by using `!help`)

### **dcDB Help Menu**

#### Table Operations:
- `!create_table <table_name> <columns_json>` - Creates a new table with specified columns  
  Example: `!create_table users '["id", "name", "age"]'`
- `!list_tables` - Lists all available tables
- `!delete_table <table_name>` - Deletes a table

#### Data Operations:
- `!insert <table_name> <row_data_json>` - Inserts a row into a table  
  Example: `!insert users '{"name": "Alice", "age": 30}'`  
  Attachments: Use `"ATTACHMENT:0"` to reference the first attachment
- `!select_all <table_name>` - Shows all rows in a table
- `!select <table_name> <condition>` - Selects rows matching key=value  
  Example: `!select users name=Alice`
- `!update <table_name> <condition> <new_data_json>` - Updates rows matching condition  
  Example: `!update users name=Alice '{"age": 31}'`
- `!delete <table_name> <condition>` - Deletes rows matching condition

#### Advanced Querying:
- `!query <table_name> <sql_query>` - Run SQL-like queries  
  Supported syntax:
  - `SELECT * FROM table WHERE condition`
  - Conditions: `=, !=, >, <, >=, <=, BETWEEN x & y, IS NULL, IS NOT NULL`
  - Combine with `AND`/`OR`  
  Examples:  
  `!query users "SELECT * FROM users WHERE age BETWEEN 25 & 35"`  
  `!query users "SELECT name FROM users WHERE age > 30 AND profile_pic IS NOT NULL"`

#### Other Commands:
- `!help` - Shows this message

#### Notes:
- All data is stored as JSON
- Table names are case-sensitive
- Use attachments for images/files (reference with ATTACHMENT:index)

## Setup
- Python 3 installed (I used 3.13.1)
- discord.py package installed (`pip3 install discord.py`)
- A Discord bot with the following permissions:
  - Send Messages
  - Send Messages in Threads
  - Create Public Threads
  - Create Private Threads
  - Embed Links
  - Manage Threads
  - Read Message History
Those are the permissions I used. I dont know if they are all neccesary. It confused me becasue I'm a little dumb. Feel free to experiment and let me know so I can update this.

Replace:
```python
import secret_token
TOKEN = secret_token.TOKEN
```
with your token or put your token in a file named secret_token.py with your token named TOKEN as a string.

Also replace the CHANNEL_ID with the id of the channel you want to use.

## Security
The data is in the Discord server, so its about as secure as that

**DO NOT share your token with anyone**

## The Why
I don't know. I wanted a free database system, and this seemed easiest.