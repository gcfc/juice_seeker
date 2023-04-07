import io
from pydub import AudioSegment
import speech_recognition as sr
import requests
import os
import logging

logger = logging.getLogger()

# Adopted from https://github.com/eastee/rebreakcaptcha with modifications and bug fixes.


def get_challenge_audio(url):
  logger.info(f"Audio URL: {url}")
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

  audio_output = None
  # recognize speech using Google Speech Recognition and Houndify
  try:
    audio_output_google = recognizer.recognize_google(audio)
    logger.info(f"Google: {audio_output_google}")
  except sr.UnknownValueError:
    logger.error("Google Speech Recognition could not understand audio")
  except sr.RequestError as e:
    logger.error(f"Could not request results from Google Speech Recognition service; {e}")

  try:
    audio_output_houndify, confidence = recognizer.recognize_houndify(
        audio, client_id=os.environ['HOUNDIFY_CLIENT_ID'], client_key=os.environ['HOUNDIFY_CLIENT_KEY'])
    logger.info(f"Houndify: {audio_output_houndify}")
  except sr.UnknownValueError:
    logger.error("Houndify could not understand audio")
  except sr.RequestError as e:
    logger.error(f"Could not request results from Houndify; {e}")

  if audio_output_houndify:
    audio_output = audio_output_houndify
  elif audio_output_google:
    audio_output = audio_output_google
  else:
    logger.error("Both Google Speech Recognition and Houndify returned empty.")
  return audio_output
