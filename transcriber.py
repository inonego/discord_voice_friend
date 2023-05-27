# Code from https://github.com/davabase/whisper_real_time
# The code in this repository is public domain.

import torch

import io 
import asyncio
import speech_recognition as sr 

from sys import platform
from queue import Queue
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

from faster_whisper import WhisperModel

import secret

class Transcriber:
    model = "large-v2" #model

    loaded_model = WhisperModel(model, device="cuda", compute_type="float16")
    
    def __init__(self, record_timeout = 2, phrase_timeout = 2):
        # Select model from
        # tiny/base/small/medium/large
        # Check non_english for Korean or etc generation
        #self.non_english = non_english

        # Timeout for speech endings
        self.record_timeout = record_timeout
        self.phrase_timeout = phrase_timeout

        self.SAMPLE_RATE = 48000
        self.SAMPLE_WIDTH = 2

        self.data_queue = Queue()

        self.run_flag = False

    async def run(self, callback):
        # Current raw audio bytes.
        sample = bytes() 
        # The last time a recording was retreived from the queue.
        phrase_time = None

        audio_path = NamedTemporaryFile().name 

        print("READY : Transriber")

        self.run_flag = True

        while self.run_flag:
            try: 
                now = datetime.utcnow()

                # Pull raw recorded audio from the queue.
                if not self.data_queue.empty():
                    # This is the last time we received new audio data from the queue.
                    phrase_time = now

                    # Concatenate our current audio data with the latest audio data.
                    while not self.data_queue.empty(): sample += self.data_queue.get()

                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if not sample == bytes() and (phrase_time and now - phrase_time > timedelta(seconds=self.phrase_timeout)):
                    # Use AudioData to convert the raw data to wav data.
                    audio_data = sr.AudioData(sample, self.SAMPLE_RATE, self.SAMPLE_WIDTH)
                    wav_data = io.BytesIO(audio_data.get_wav_data())

                    # Write wav data to the temporary file as bytes.
                    with open(audio_path, 'w+b') as f:
                        f.write(wav_data.read())   
                    
                    # Read the transcription.
                    segments, _ = self.loaded_model.transcribe(audio_path, language='ko', temperature=0, no_speech_threshold=0.35, vad_filter=True, vad_parameters=dict(threshold=0.6, min_silence_duration_ms=500))

                    result = ""

                    for segment in segments:
                        result += segment.text

                    # Return transcribed sentences.
                    #yield result
                    if not (len(result) == 0 or result.isspace()):
                        if  result not in secret.noise_word:
                            def c(): callback(result)
    
                            await asyncio.get_event_loop().run_in_executor(None, c)
                        else:
                            print(f"노이즈 제거 완료 : {result}")
                        
                    # Clear the previous sample.
                    sample = bytes()

                # Infinite loops are bad for processors, must sleep.
                await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                pass

    def stop(self):
        self.run_flag = False

    # Callback function for source_callback in execute
    def use_mic(self,  default_microphone = 'pulse', energy_threshold = 1000): 
        # We use SpeechRecognizer to record our audio because it has a nice feauture where it can detect when speech ends.
        recorder = sr.Recognizer()
        recorder.energy_threshold = energy_threshold
        # Definitely do this, dynamic energy compensation lowers the energy threshold dramtically to a point where the SpeechRecognizer never stops recording.
        recorder.dynamic_energy_threshold = False

        # Important for linux users.
        # Prevents permanent application hang and crash by using the wrong Microphone
        if 'linux' in platform:
            mic_name = default_microphone
            if not mic_name or mic_name == 'list':
                print("Available microphone devices are: ")
                for index, name in enumerate(sr.Microphone.list_microphone_names()):
                    print(f"Microphone with name \"{name}\" found")   
                return
            else:
                for index, name in enumerate(sr.Microphone.list_microphone_names()):
                    if mic_name in name:
                        source = sr.Microphone(sample_rate=16000, device_index=index)
                        break
        else:
            source = sr.Microphone(sample_rate=16000)
 
        self.SAMPLE_RATE, self.SAMPLE_WIDTH = source.SAMPLE_RATE, source.SAMPLE_WIDTH
        
        with source:
            recorder.adjust_for_ambient_noise(source)

        def record_callback(_, audio:sr.AudioData) -> None:
            """
            Threaded callback function to recieve audio data when recordings finish.
            audio: An AudioData containing the recorded bytes.
            """
            # Grab the raw bytes and push it into the thread safe queue.
            self.data_queue.put(audio.get_raw_data())

        # Create a background thread that will pass us raw audio bytes.
        # We could do this manually but SpeechRecognizer provides a nice helper.
        recorder.listen_in_background(source, record_callback, phrase_time_limit=self.record_timeout)