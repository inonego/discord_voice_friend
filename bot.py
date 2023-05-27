import discord
from discord.ext import commands, voice_recv 
from discord.opus import Decoder as OpusDecoder

discord.opus._load_default()
 
import asyncio
import nest_asyncio  
nest_asyncio.apply()

import chat
import speech
from transcriber import Transcriber
   
class ChannelRunner:
    def __init__(self, channel):
        self.channel = channel

        self.history = []
        self.MAX_HISTORY = 6

        self.transcriber = Transcriber()

        self.audio = None
        
        asyncio.create_task(self.transcriber.run(self.process_message))
 
    # 실행 - 보이스 채널 접속 시
    async def connect(self):
        # 유저가 속한 보이스 채널로 봇이 들어갑니다.
        voice_client = await self.channel.connect(cls=voice_recv.VoiceRecvClient)

        SAMPLE_WIDTH = OpusDecoder.SAMPLE_SIZE // OpusDecoder.CHANNELS
        SAMPLE_RATE = OpusDecoder.SAMPLING_RATE * 2 # => 모노 1 스테레오 2

        def callback(user, data):
            self.on_voice_callback(user, (SAMPLE_RATE, SAMPLE_WIDTH), data.pcm)

        voice_client.listen(voice_recv.BasicSink(callback))

    # 정지 - 보이스 채널 퇴장 시
    async def disconnect(self):
        await self.channel.guild.voice_client.disconnect()

        runners[self.channel] = None

        self.transcriber.stop()

    # 대화 히스토리를 추가합니다.
    def append_history(self, input, output): 
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[1:]
        
        self.history.append({"input": input, "output": output})

    def answer(self, content):
        result = chat.generate(self.history, content)

        self.append_history(content, result)

        return result

    # 음성 데이터를 받았을 때 처리하는 함수
    def on_voice_callback(self, user, info, data: bytes):
        self.transcriber.SAMPLE_RATE, self.transcriber.SAMPLE_WIDTH = info

        self.transcriber.data_queue.put(data)

    # 음성을 텍스트로 변환 완료했을 때 처리하는 함수
    def process_message(self, message):
        result = None
        
        try:
            result = self.answer(message)  
        except:
            result = chat.failed_comment

        print(message)
        print(result)

        self.speak(result)

    def speak(self, message):
        path = f'generated_audio/{self.channel.guild.id}_{self.channel.id}.wav'

        voice_client = self.channel.guild.voice_client

        # 현재 재생 중인 음성을 정지합니다.
        if voice_client.is_playing():
            voice_client.stop_playing()

        # 음성을 생성합니다.
        speech.generate(path, message) 

        self.audio = discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=path)
        # 생성된 음성을 재생합니다.
        voice_client.play(self.audio) 


runners = {}
  
client = commands.Bot(command_prefix='_', intents=discord.Intents.all())

# 명령어를 입력한 유저를 따라 보이스 채널 들어가기
async def follow_user(interaction):
    # 상호작용을 한 유저가 있는 채널입니다.
    voice_channel = interaction.author.voice.channel if interaction.author.voice else None

    if voice_channel:
        # 현재 봇이 있는 채널입니다.
        current_channel = interaction.guild.voice_client.channel if interaction.guild.voice_client else None  
        
        # 이동하기 위해서 현재 있는 채널에서 나갑니다.
        if current_channel:
            runner = runners[current_channel]

            await runner.disconnect()

        # 그 다음 유저가 있는 채널에 접속합니다.
        runner = runners[voice_channel] = ChannelRunner(voice_channel)

        await runner.connect() 
        
        await interaction.send("초대해줘서 고마워!")

    else:
        print('보이스 채팅 채널에 접속해 있지 않습니다.')

# 보이스 채널에서 나가기
async def leave_voice_channel(interaction):
    voice_channel = interaction.guild.voice_client.channel if interaction.guild.voice_client else None
    
    if voice_channel:
        runner = runners[voice_channel]

        await runner.disconnect()
         
        await interaction.send("잘 있어.")
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

# 보이스 채널에서 퇴장
@client.command()
async def bye(interaction: discord.Interaction):
    await leave_voice_channel(interaction)