import discord, pymongo, datetime

mongo_client = pymongo.MongoClient("mongodb://192.168.1.144:27017/") # Connect to mongoDB
database = mongo_client["ToDo_Bot_Storage"]

guild_info_col = database["guild_info"]
bot_info_col = database["bot_info"]

TOKEN = bot_info_col.find_one()["token"]

PREFIX = "/todo"  # The prefix for all ToDo bot commands

help_message_text = open("help_message.txt", "r").read()

error_messages = {
    "id_not_an_int": "Please use an integer for <id>, for more information, check `/todo help`",
    "id_not_on_todo": "Please use an id on the To-Do list. For more information, check `/todo help`"
}
delete_delay = 60

client = discord.Client()
@client.event
async def on_ready():
    print(f'Logged in as: {client.user.name}')
    print(f'With ID: {client.user.id}')
    # update_db()
    for x in guild_info_col.find():
        print(x)
        
    

    for g in client.guilds:
        
        query = {"guild_id": g.id}
        # print(guild_info_col.find_one(query))
        if not guild_info_col.find_one(query):
            await on_guild_join(guild=g)
        else:
            # print(g.id, g.name)
            await update_messages(g)


@client.event
async def on_guild_join(guild):
    todo_channel = await guild.create_text_channel(
        "to-do",
        reason="Initial Creation of the To-Do channel by the To-Do bot",
        topic="Channel created by the To-Do Bot. This is where all of the To-Do list information will be stored.",
    )
    # await todo_channel.edit(
    #     topic="Channel created byt the ToDo Bot. Add an item to the todo list to get started!",
    # )
    todo_message = await todo_channel.send(content="To Do List:\nAdd an item to the ToDo list using `/todo add <item>`")
    await todo_message.pin()
    help_message = await todo_channel.send(content=help_message_text)
    await help_message.pin()

    update_db(
        guild,
        todo_channel_id=todo_channel.id,
        todo_message_id=todo_message.id,
        help_message_id=help_message.id,
        todo_list=[]
    )

    print(f"Bot has been added to a guild! Guild Name: \"{guild.name}\"")


@client.event
async def on_message(message):
    if message.author == client.user:
        pass
    global help_message_text
    query = {"guild_id": message.guild.id}
    db_info = guild_info_col.find_one(query)
    if message.content.startswith(PREFIX):
        command_params = message.content.split(" ")
        lowered_command = []
        for x in command_params:
            lowered_command.append(x.lower())
        print(f"{message.author}: {message.content}")
        if len(lowered_command) <= 1 or lowered_command[1] in ["help", "?"]: # /todo, /todo help, /todo ?
            await message.channel.send(content=help_message_text, delete_after=delete_delay)
            await update_messages(g=message.guild)

        elif lowered_command[1] in ["add"]: # /todo add
            todo_list_temp = db_info["todo_list"]
            new_item = " ".join(command_params[2:])
            category = ""
            if command_params[2].startswith("[") and command_params[2].endswith("]"):
                new_item = " ".join(command_params[3:]) 
                category = command_params[2][1:-1]
            
            todo_list_temp.append({
                "item": new_item,
                "completed": False,
                "date_added": datetime.datetime.now(),
                "added_by": str(message.author),
                "category": category,
                "importance": 0,
            })
            update_db(message.guild, todo_list=todo_list_temp)
            returnMessage = f"\"{new_item}\" added to ToDo list by **{message.author.name}**"
            await message.channel.send(returnMessage, delete_after=delete_delay)


        elif lowered_command[1] in ["complete", "done", "finish"]:
            if is_int(lowered_command[2]):
                index = int(lowered_command[2])-1
                todo_list = db_info["todo_list"]
                if index >= 0 and index < len(todo_list):
                    todo_list[index]["completed"] = True
                    await message.channel.send(f"`{todo_list[index]['item']}` marked as completed!", delete_after=delete_delay)
                    update_db(g=message.guild, todo_list=todo_list)
                else:
                    await message.channel.send("Please use an ID number on the todo list.", delete_after=delete_delay)
            else:
                await message.channel.send(f"Please enter an integer for `<id>`. The command should be `/todo {lowered_command[1]} <id>`", delete_after=delete_delay)
        elif lowered_command[1] in ["info", "data", "information"]:
            if is_int(lowered_command[2]):
                index = int(lowered_command[2])-1
                todo_list = db_info["todo_list"]
                if index >= 0 and index < len(todo_list):
                    item = todo_list[index]
                    msg = f"""**Showing Info for item `#{index+1}`:**
Item Name: `{item['item']}`
Category: `{item['category'] if item['category'] != '' else 'None'}`
Importance Level: `{item['importance']}`
Completed: `{item['completed']}`
Date Added: `{item['date_added'].strftime('%A, %d %B %Y')}`
Added By: `{item['added_by']}`
                    """
                    await message.channel.send(msg, delete_after=delete_delay)
                else:
                    await message.channel.send(error_messages["id_not_on_todo"], delete_after=delete_delay)
            else:
                await message.channel.send(error_messages["id_not_an_int"], delete_after=delete_delay)
        elif lowered_command[1] in ["urgency", "urgent", "urgence", "importance", "important", "imp"]:
            todo_list = db_info["todo_list"]
            index = is_int(lowered_command[2], r=True)
            if index:
                index -= 1
                if index >= 0 and index < len(todo_list):
                    imp_lvl = is_int(lowered_command[3], r=True)
                    if imp_lvl is not False and imp_lvl >= 0 and imp_lvl <= 3:
                        todo_list[index]["importance"] = imp_lvl
                        update_db(g=message.guild, todo_list=todo_list)
                        await message.channel.send(f"Importance for `{todo_list[index]['item']}` set to `{imp_lvl}` by **{message.author.name}**", delete_after=delete_delay)
                    else:
                        await message.channel.send(f"Please use an imporance value between 0 and 3. `{lowered_command[3]}` is not an acceptable value.")
                else:
                    await message.channel.send(error_messages["id_not_on_todo"], delete_after=delete_delay)
            else:
                await message.channel.send(error_messages["id_not_an_int"], delete_after=delete_delay)
        elif lowered_command[1] in ["list", "show", "l"]:
            todo_list = db_info["todo_list"]
            s = formattedToDo(todo_list)
            await message.channel.send(s, delete_after=delete_delay)

        elif lowered_command[1] in ["reload", "refresh"]:
            help_message_text = open("help_message.txt", "r").read()
            

            await message.channel.send(f"ToDo bot reloaded.", delete_after=delete_delay)
        elif lowered_command[1] in ["category", "cat"]:
            todo_list = db_info["todo_list"]
            index = is_int(lowered_command[2], r=True)
            if index:
                index -= 1
                if index >= 0 and index < len(todo_list):
                    if len(lowered_command) >= 4:
                        todo_list[index]["category"] = lowered_command[3]
                    else:
                        todo_list[index]["category"] = ""
                    update_db(g=message.guild, todo_list=todo_list)
                    await message.channel.send(f"Category for `{todo_list[index]['item']}` set to `{lowered_command[3]}` by **{message.author.name}**", delete_after=delete_delay)
                    
                else:
                    await message.channel.send(error_messages["id_not_on_todo"], delete_after=delete_delay)
            else:
                await message.channel.send(error_messages["id_not_an_int"], delete_after=delete_delay)

        elif lowered_command[1] in ["rename", "rn"]:
            todo_list = db_info["todo_list"]
            index = is_int(lowered_command[2], r=True)
            if index:
                index -= 1
                if index >= 0 and index < len(todo_list):
                    old_name = todo_list[index]["item"]
                    new_name = " ".join(command_params[3:])
                    todo_list[index]["item"] = new_name
                    update_db(g=message.guild, todo_list=todo_list)
                    await message.channel.send(f"Renamed {old_name} to {new_name} by **{message.author.name}**", delete_after=delete_delay)
                    
                else:
                    await message.channel.send(error_messages["id_not_on_todo"], delete_after=delete_delay)
            else:
                await message.channel.send(error_messages["id_not_an_int"], delete_after=delete_delay)
        elif lowered_command[1] in ["delete", "remove", "trash"]:
            todo_list = db_info["todo_list"]
            index = is_int(lowered_command[2], r=True)
            if index:
                index -= 1
                if index >= 0 and index < len(todo_list):
                    deleted_item = todo_list[index]
                    todo_list.pop(index)
                    update_db(g=message.guild, todo_list=todo_list)
                    await message.channel.send(f"`{deleted_item['item']}` has been deleted by **{message.author.name}**", delete_after=delete_delay)
                    
                else:
                    await message.channel.send(error_messages["id_not_on_todo"], delete_after=delete_delay)
            else:
                await message.channel.send(error_messages["id_not_an_int"], delete_after=delete_delay)



        else:
            await message.channel.send(f"Unknown subcommand, `{lowered_command[1]}`. Use `/todo help` for a list of commands.")

        await update_messages(message.guild)
        await message.delete(delay=0)

async def update_messages(g=None):
    if g:
        query = {"guild_id": g.id}
        db_info = guild_info_col.find_one(query)
        todo_list = db_info["todo_list"]
        todo_channel = await client.fetch_channel(db_info["todo_channel_id"])
        todo_msg = await todo_channel.fetch_message(db_info["todo_message_id"])
        help_msg = await todo_channel.fetch_message(db_info["help_message_id"])
        s = formattedToDo(todo_list)
        await todo_msg.edit(content=s)
        await help_msg.edit(content=help_message_text)
        top = formattedToDo(todo_list, topic=True)
        await todo_channel.edit(topic=top)
    else:
        for guild in client.guilds:
            update_messages(g=guild)


def update_db(g=None, **options):
    query = {}
    GUILD_DICT = {}
    if not g:
        for guild in client.guilds:
            GUILD_DICT = {"guild_id": guild.id, "guild_name": guild.name, }
            for x in options:
                GUILD_DICT[x] = options[x]
            query = {"guild_id": guild.id}
    else:
        GUILD_DICT = {"guild_id": g.id, "guild_name": g.name, }
        for x in options:
            GUILD_DICT[x] = options[x]
        query = {"guild_id": g.id}
    if not guild_info_col.find_one(query):
        guild_info_col.insert_one(GUILD_DICT)
    else:
        guild_info_col.update_one(query, {"$set": GUILD_DICT})

def is_int(s, r=False):
    try:
        int(s)
        if not r:
            return True
        else:
            return int(s)
    except ValueError:
        return False

def formattedToDo(todo_list, topic=False):
    s = "ToDo List: "
    if not topic:
        for x in range(len(todo_list)):
            done = ":white_check_mark:" if todo_list[x]["completed"] else ""
            importance = is_int(todo_list[x]['importance'], r=True)
            importance_str = ""
            if importance:
                importance_str = f"({'!' * importance})"
            category = ""
            if todo_list[x]["category"] != "":
                category = f'[{todo_list[x]["category"]}]'

            # todo_item = todo_list[x]["item"]
            s += f"\n{x+1}: {done}{importance_str} `{todo_list[x]['item']}` {category}"
    else:
        for x in todo_list:
            done = ":white_check_mark:" if x["completed"] else ""
            s += f"{done} {x['item']}, "
    if len(todo_list) <= 0:
        s += "\nThere's nothing on your ToDo list!"
    return s

client.run(TOKEN)
