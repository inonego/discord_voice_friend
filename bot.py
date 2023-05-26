import discord
from discord.ext import commands, voice_recv 
from discord.opus import Decoder as OpusDecoder

discord.opus._load_default()
 
import nest_asyncio  
nest_asyncio.apply()
  
client = commands.Bot(command_prefix='_', intents=discord.Intents.all())

vc = None

on_voice_callback = None

# 명령어를 입력한 유저를 따라 보이스 채널 들어가기
async def follow_user(ctx): 
    global vc, on_voice_callback

    voice_channel = ctx.author.voice.channel 

    if voice_channel:
        # 유저가 속한 보이스 채널로 봇이 들어갑니다.
        vc = await voice_channel.connect(cls=voice_recv.VoiceRecvClient) 

        SAMPLE_WIDTH = OpusDecoder.SAMPLE_SIZE // OpusDecoder.CHANNELS
        SAMPLE_RATE = OpusDecoder.SAMPLING_RATE * 2 # => 모노 1 스테레오 2

        def callback(user, data):
            on_voice_callback(user, (SAMPLE_RATE, SAMPLE_WIDTH), data.pcm)

        vc.listen(voice_recv.BasicSink(callback))
    
    else:
        print('보이스 채팅 채널에 접속해 있지 않습니다.')
        
# 보이스 채널에서 나가기
async def leave_voice_channel(ctx):
    voice_client = ctx.guild.voice_client
    
    if voice_client:
        # 봇이 현재 보이스 채널에 있으면 나가도록 합니다.
        await voice_client.disconnect()
    else:
        print('보이스 채팅 채널에 접속해 있지 않습니다.')

@client.event
async def on_ready():
    #봇이 실행되면 콘솔창에 표시
    print('READY : DISCORD BOT {0.user}'.format(client))

# 보이스 채널에 초대
@client.command()
async def hi(interaction: discord.Interaction):
    await follow_user(interaction)
    
    await interaction.send("초대해줘서 고마워!")

# 보이스 채널에서 퇴장
@client.command()
async def bye(interaction: discord.Interaction):
    await leave_voice_channel(interaction)
    
    await interaction.send("잘 있어.")

async def run(token):
    await client.run(token)

def play(path):
    global vc

    vc.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=path))