import secret  
import openai  
 
#OPEN AI API를 사용합니다.
SELECTED_MODEL = "gpt-3.5-turbo"

# 대화를 API로 처리합니다.
def callAPI(messages):
    openai.api_key = secret.OPENAI_API_KEY

    try:
        completion = openai.ChatCompletion.create(model = SELECTED_MODEL, messages = messages)
         
        return completion.choices[0].message.content
    except:
        raise Exception("Couldn't receive ChatGPT Responce.")
    
# 대화에 응답합니다.
def generate(history, content):
    messages = [] 
    messages.append({"role": "system", "content": secret.prompt})
    
    if len(history) > 0:
        for H in history:
            messages.append({"role": "system", "content": f"{H['input']} <-- This is user's past question"})
            messages.append({"role": "system", "content": f"{H['output']} <-- This is your past answer"})

    messages.append({"role": "user", "content": content})
    
    return callAPI(messages)

failed_comment = secret.failed_comment

print("READY : CHAT GPT")  