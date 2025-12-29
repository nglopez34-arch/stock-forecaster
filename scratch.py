import edge_tts
import asyncio
import pygame
import random
import numpy as np
import time
import os

items = [
    # No reaction
    "wallet",
    "ID",
    "phone",
    "keys",
    "cigarettes",
    "lighter",
    "candybar",
    "snack",
    "handkerchief",
    "tissue",
    "pen",
    "notebook",
    "coins",
    "lipbalm",
    "gum",
    "breathmints",
    "earbuds",
    "headphones",
    "glasses",
    "sunglasses",
    "comb",
    "brush",
    "receipt",
    "ticket",
    "buspass",
    "notepad",
    "flashdrive",
    "charger",
    "mask",
    "gloves",

    # OC Spray
    "screwdriver",
    "metalpipe",
    "taser",
    "pepperspray",
    "punch",
    "kick",
    "spit",
    "scream",
    "rock",
    "fist",

    # Lethal force
    "boxcutter",
    "utilityknife",
    "handgun",
    "pistol",
    "revolver",
    "knife",
    "shotgun",
    "firearm",
    "grenade",
    "explosive",
    "bomb"
]

os.makedirs("word_sounds", exist_ok=True)

voices = [
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-GB-SoniaNeural",
    "en-US-JennyNeural",
    "en-AU-NatashaNeural",
    "en-CA-ClaraNeural",
    "en-US-EricNeural",
    "en-GB-RyanNeural"
]


async def generate_audio():
    print("Checking and generating audio files...")
    sound_files = []
    files_to_generate = []
    files_already_exist = []

    # First pass: check what exists
    for voice in voices:
        for word in items:
            filename = f"word_sounds/{voice}_{word}.mp3"
            sound_files.append(filename)
            if os.path.exists(filename):
                files_already_exist.append(filename)
            else:
                files_to_generate.append((voice, word, filename))

    print(f"Found {len(files_already_exist)} existing audio files")
    print(f"Need to generate {len(files_to_generate)} new audio files")

    # Second pass: generate missing files
    if files_to_generate:
        for i, (voice, word, filename) in enumerate(files_to_generate, 1):
            print(f"Generating {i}/{len(files_to_generate)}: {voice} - {word}")
            communicate = edge_tts.Communicate(word, voice)
            await communicate.save(filename)
    else:
        print("All audio files already exist!")

    return sound_files


sound_files = asyncio.run(generate_audio())
print(f"Total audio files ready: {len(sound_files)}")

pygame.mixer.init()
sounds = [pygame.mixer.Sound(f) for f in sound_files]

print("Starting playback loop... (Ctrl+C to stop)")

while True:
    interval = np.random.normal(5, 1)
    interval = max(1, interval)

    print(f"Waiting {interval:.2f} seconds...")
    time.sleep(interval)

    sound = random.choice(sounds)
    sound.play()
    print("Playing sound")