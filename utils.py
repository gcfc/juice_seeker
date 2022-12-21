import io
from pydub import AudioSegment
import speech_recognition as sr
import requests
import os


# Adopted from https://github.com/eastee/rebreakcaptcha with modifications and bug fixes.
def get_challenge_audio(url):
  print("Audio URL:", url)
  # Download the challenge audio and store in memory
  request = requests.get(url)
  audio_file = io.BytesIO(request.content)

  # Convert the audio to a compatible format in memory
  converted_audio = io.BytesIO()
  sound = AudioSegment.from_mp3(audio_file)
  sound.export(converted_audio, format="wav")
  converted_audio.seek(0)

  return converted_audio


def speech_to_text(audio_source):
  # Initialize a new recognizer with the audio in memory as source
  recognizer = sr.Recognizer()
  with sr.AudioFile(audio_source) as source:
    audio = recognizer.record(source)  # read the entire audio file

  audio_output = ""
  # recognize speech using Google Speech Recognition
  try:
    audio_output = recognizer.recognize_google(audio)
    print("Google:", audio_output)
    # Check if we got harder audio captcha
    if any(character.isalpha() for character in audio_output):
      # Use Houndify to detect the harder audio captcha
      audio_output, confidence = recognizer.recognize_houndify(
          audio, client_id=os.environ['HOUNDIFY_CLIENT_ID'], client_key=os.environ['HOUNDIFY_CLIENT_KEY'])
      print("Houndify: " + audio_output)
  except sr.UnknownValueError:
    print("Google Speech Recognition could not understand audio")
  except sr.RequestError as e:
    print("Could not request results from Google Speech Recognition service; {0}".format(e))

  return audio_output
