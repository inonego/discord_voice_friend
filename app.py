import os
import bot
import secret  
import speech
import openai  
import asyncio 

os.environ['KMP_DUPLICATE_LIB_OK']='True'

from transcriber import Transcriber

from scipy.io.wavfile import write
 
#
# ----- TTS 영역
#

# VITS TTS 모델을 불러옵니다.
dir = os.getcwd() + "/model"

speaker = speech.run(dir + '/model.pth', dir + '/config.json')

# 생성된 음성을 저장합니다.
def generate_speech(path, message):
    audio = speaker.infer(message)
    
    write(path, 44100, audio)

# 기억하는 최대 대화 수
# 대화 내용이 N개가 되면 하나의 문장으로 요약합니다.
MAX_HISTORY = 6
history = []

#
# ----- Text Generation 영역
#

#OPEN AI API를 사용합니다.
SELECTED_MODEL = "gpt-3.5-turbo"

# 대화를 API로 처리합니다.
def callAPI(messages):
    openai.api_key = secret.OPENAI_API_KEY

    completion = openai.ChatCompletion.create(model = SELECTED_MODEL, messages = messages)

    return completion.choices[0].message.content

# 대화 히스토리를 추가합니다.
def appendHistory(content):
    global history
    
    if len(history) > MAX_HISTORY:
        history = history[1:]
    
    history.append(content)
    
# 대화에 응답합니다.
def answer(content):
    
    messages = [] 
    messages.append({"role": "system", "content": secret.prompt})
    
    messages.append({"role": "system", "content" : "Previous conversation is like this."})
    for H in history:
        messages.append({"role": "system", "content": H})
        
    messages.append({"role": "system", "content" : "You should answer in Korean."})
    messages.append({"role": "user", "content": content})
    
    appendHistory(content)
    
    return callAPI(messages)

print("READY : CHAT GPT") 
 
#
# ----- STT 영역
#

transcriber = Transcriber()

#
# ----- Discord 영역
#

def on_voice_callback(user, info, data: bytes):
    transcriber.SAMPLE_RATE, transcriber.SAMPLE_WIDTH = info

    transcriber.data_queue.put(data)

bot.on_voice_callback = on_voice_callback

def process_message(message):
    print(message)
    result = answer(message)
    print(result) 

    path = f'generated_audio/speech.wav'

    generate_speech(path, result)
    
    bot.play(path)

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(bot.run(secret.DISCORD_TOKEN), transcriber.execute(process_message)))