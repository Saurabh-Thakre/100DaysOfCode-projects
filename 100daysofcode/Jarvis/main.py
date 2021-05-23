import pyttsx3 # pip instal pyttsx3
import speech_recognition as sr # pip install speechRecognition
import datetime
import wikipedia # pip install wikipedia
import webbrowser
import subprocess, sys
import os
import smtplib

MASTER = "Saurabh"

engine = pyttsx3.init('espeak')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[12].id)

#speak function will pronounce the string which is passed to it
def speak(text):
    engine.setProperty('rate', 200)
    engine.setProperty('volume', 1.0)
    engine.setProperty('pitch', 32)
    engine.say(text)
    engine.runAndWait()

# This function will wish you looking at the current time
def wishMe():
    hour = int(datetime.datetime.now().hour)

    if hour >= 0 and hour < 12:
        speak("Good Morning" + MASTER)
    
    elif hour >= 12 and hour < 18:
        speak("Good Afternoon" + MASTER)

    else:
        speak("Good Evening" + MASTER)

    speak("How may I help you")

# This function will take command from the microphone

def takeCommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        r.pause_threshold = 1 #seconds of non-speaking audio before a phrase is considered complete
        print("Listening...")   
        audio = r.listen(source)
    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-in')
        print(f"User Said: {query}\n")

    except Exception as e:
        print("Could you please say that again ?")
        return "None"

    return query

#Main program starts here
speak("Initializing Jarvis")
if __name__== "__main__":

    wishMe()
    while True:
        query = takeCommand().lower()
    
    # Logic for executing tasks based on query

        if 'wikipedia' in query:
            speak('Sure, Saurabh. Searchiing Wikipedia')
            query = query.replace("wikipedia", "")
            results = wikipedia.summary(query, sentences=2)
            speak("According to Wikipedia")
            print(results)
            speak(results)
        
        elif 'open youtube' in query:
            webbrowser.open('youtube.com')
        
        elif 'open google' in query:
            webbrowser.open('google.com')

        elif 'open stackoverflow' in query:
            webbrowser.open('stackoverflow.com')

        elif 'play music' in query:
            music_dir = '/home/sthakre/Desktop/py/100daysofcode/Naruto/songs'
            songs = os.listdir(music_dir)
            print(songs)
            # os.startfile(os.path.join(music_dir, songs[0]))  
            # opener = "songs" if sys.platform == "darwin" else "xdg-open"      
            webbrowser.open("/home/sthakre/Desktop/py/100daysofcode/Naruto/songs/Dance_Monkey.mp3")      

        elif 'the time' in query:
            strTime = datetime.datetime.now().strftime("%H hours %M minutes %S seconds")
            speak(f"Sir, the time is {strTime}")

        elif 'open code'  in query:
            # mode
            mode = 666
            # flags
            flags = os.O_RDWR | os.O_CREAT
            codePath = "/home/sthakre/Desktop/py/100daysofcode/Naruto/songs/code"
            os.open(codePath, flags, mode) 
        elif 'bye jarvis' in query:
            exit()








# for voice in voices:
#     # to get the info. about various voices in our PC 
#     print("Voice:")
#     print("ID: %s" %voice.id)
#     print("Name: %s" %voice.name)
#     print("Age: %s" %voice.age)
#     print("Gender: %s" %voice.gender)
#     print("Languages Known: %s" %voice.languages)

# engine = pyttsx3.init()
# voices = engine.getProperty('voices')
# for voice in voices:
#    engine.setProperty('voice', voice.id)
#    engine.say('The quick brown fox jumped over the lazy dog.')
# engine.runAndWait()
