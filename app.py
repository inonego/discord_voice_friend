import os
import bot
import secret   
import asyncio 

os.environ['KMP_DUPLICATE_LIB_OK']='True' 
   
asyncio.run(bot.client.start(secret.DISCORD_TOKEN))