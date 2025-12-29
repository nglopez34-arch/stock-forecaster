import edge_tts
import asyncio
import pygame
import random
import numpy as np
import time
import os

items = [
    # No reaction
    "wallet", "ID", "phone", "keys", "cigarettes", "lighter", "candybar", "snack",
    "handkerchief", "tissue", "pen", "notebook", "coins", "lipbalm", "gum",
    "breathmints", "earbuds", "headphones", "glasses", "sunglasses", "comb",
    "brush", "receipt", "ticket", "buspass", "notepad", "flashdrive", "charger",
    "mask", "gloves",
    # OC Spray
    "screwdriver", "metalpipe", "taser", "pepperspray", "punch", "kick", "spit",
    "scream", "rock", "fist",
    # Lethal force
    "boxcutter", "utilityknife", "handgun", "pistol", "revolver", "knife",
    "shotgun", "firearm", "grenade", "explosive", "bomb"
]

os.makedirs("word_sounds", exist_ok=True)

voices = [
    "en-US-AriaNeural", "en-US-GuyNeural",
    "en-US-JennyNeural", "en-CA-ClaraNeural",
    "en-US-EricNeural", "en-GB-RyanNeural"
]


async def generate_single_file(voice, word, filename, max_retries=3):
    """Generate a single audio file with retry logic"""
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(word, voice)
            await communicate.save(filename)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                print(f"  Error on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                print(f"  Failed after {max_retries} attempts: {e}")
                return False


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

    # Second pass: generate missing files with delays
    if files_to_generate:
        for i, (voice, word, filename) in enumerate(files_to_generate, 1):
            print(f"Generating {i}/{len(files_to_generate)}: {voice} - {word}")
            success = await generate_single_file(voice, word, filename)

            if not success:
                print(f"  Skipping failed file: {filename}")

            # Add delay every 50 files to avoid rate limiting
            if i % 50 == 0 and i < len(files_to_generate):
                print(f"  Pausing for 10 seconds to avoid rate limiting...")
                await asyncio.sleep(10)
            else:
                await asyncio.sleep(0.2)  # Small delay between each file
    else:
        print("All audio files already exist!")

    # Filter out files that don't exist (failed generations)
    existing_files = [f for f in sound_files if os.path.exists(f)]
    print(f"\nSuccessfully loaded {len(existing_files)}/{len(sound_files)} audio files")

    return existing_files


sound_files = asyncio.run(generate_audio())

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