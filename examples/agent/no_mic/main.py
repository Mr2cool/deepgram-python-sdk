# Copyright 2025 Deepgram SDK contributors. All Rights Reserved.
# Use of this source code is governed by a MIT license that can be found in the LICENSE file.
# SPDX-License-Identifier: MIT

# 1. Install the SDK
# pip install deepgram-sdk requests

# 2. Import dependencies and set up the main function
import requests
import wave
import io
import time
import os
import json
import threading
from datetime import datetime

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    AgentWebSocketEvents,
    AgentKeepAlive,
)
from deepgram.clients.agent.v1.websocket.options import SettingsOptions

def main():
    try:
        # 3. Initialize the Voice Agent
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
        print(f"API Key found: {api_key[:5]}...")  # Only print first 5 chars for security

        # Initialize Deepgram client
        config = DeepgramClientOptions(
            options={
                "keepalive": "true",
                "speaker_playback": "true",
            },
        )
        deepgram = DeepgramClient(api_key, config)
        connection = deepgram.agent.websocket.v("1")
        print("Created WebSocket connection...")

        # 4. Configure the Agent
        options = SettingsOptions()
        # Audio input configuration
        options.audio.input.encoding = "linear16"
        options.audio.input.sample_rate = 24000
        # Audio output configuration
        options.audio.output.encoding = "linear16"
        options.audio.output.sample_rate = 16000  # Match JS example
        options.audio.output.container = "wav"
        # Agent configuration
        options.agent.language = "en"
        options.agent.listen.provider.type = "deepgram"
        options.agent.listen.model = "nova-3"
        options.agent.think.provider.type = "open_ai"
        options.agent.think.model = "gpt-4o-mini"
        options.agent.think.prompt = "You are a friendly AI assistant."
        options.agent.speak.provider.type = "deepgram"
        options.agent.speak.model = "aura-2-thalia-en"
        options.agent.greeting = "Hello! How can I help you today?"

        # 5. Send Keep Alive messages
        def send_keep_alive():
            while True:
                time.sleep(5)
                print("Keep alive!")
                connection.send(str(AgentKeepAlive()))

        # Start keep-alive in a separate thread
        keep_alive_thread = threading.Thread(target=send_keep_alive, daemon=True)
        keep_alive_thread.start()

        # 6. Setup Event Handlers
        audio_buffer = bytearray()
        file_counter = 0

        def on_audio_data(self, data, **kwargs):
            nonlocal audio_buffer
            audio_buffer.extend(data)
            print(f"Received audio data, length: {len(data)} bytes")

        def on_agent_audio_done(self, agent_audio_done, **kwargs):
            nonlocal audio_buffer, file_counter
            print(f"Agent audio done: {agent_audio_done}")
            with open(f"output-{file_counter}.wav", 'wb') as f:
                f.write(create_wav_header())
                f.write(audio_buffer)
            audio_buffer = bytearray()
            file_counter += 1

        def on_conversation_text(self, conversation_text, **kwargs):
            print(f"Conversation Text: {conversation_text}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"{json.dumps(conversation_text.__dict__)}\n")

        def on_welcome(self, welcome, **kwargs):
            print(f"Welcome message received: {welcome}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"Welcome message: {welcome}\n")

        def on_settings_applied(self, settings_applied, **kwargs):
            print(f"Settings applied: {settings_applied}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"Settings applied: {settings_applied}\n")

        def on_user_started_speaking(self, user_started_speaking, **kwargs):
            print(f"User Started Speaking: {user_started_speaking}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"User Started Speaking: {user_started_speaking}\n")

        def on_agent_thinking(self, agent_thinking, **kwargs):
            print(f"Agent Thinking: {agent_thinking}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"Agent Thinking: {agent_thinking}\n")

        def on_agent_started_speaking(self, agent_started_speaking, **kwargs):
            print(f"Agent Started Speaking: {agent_started_speaking}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"Agent Started Speaking: {agent_started_speaking}\n")

        def on_close(self, close, **kwargs):
            print(f"Connection closed: {close}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"Connection closed: {close}\n")

        def on_error(self, error, **kwargs):
            print(f"Error: {error}")
            print(f"Error message: {error.message if hasattr(error, 'message') else 'No message'}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"Error: {error}\n")

        def on_unhandled(self, unhandled, **kwargs):
            print(f"Unhandled event: {unhandled}")
            with open("chatlog.txt", 'a') as chatlog:
                chatlog.write(f"Unhandled event: {unhandled}\n")

        # Register handlers
        connection.on(AgentWebSocketEvents.AudioData, on_audio_data)
        connection.on(AgentWebSocketEvents.AgentAudioDone, on_agent_audio_done)
        connection.on(AgentWebSocketEvents.ConversationText, on_conversation_text)
        connection.on(AgentWebSocketEvents.Welcome, on_welcome)
        connection.on(AgentWebSocketEvents.SettingsApplied, on_settings_applied)
        connection.on(AgentWebSocketEvents.UserStartedSpeaking, on_user_started_speaking)
        connection.on(AgentWebSocketEvents.AgentThinking, on_agent_thinking)
        connection.on(AgentWebSocketEvents.AgentStartedSpeaking, on_agent_started_speaking)
        connection.on(AgentWebSocketEvents.Close, on_close)
        connection.on(AgentWebSocketEvents.Error, on_error)
        connection.on(AgentWebSocketEvents.Unhandled, on_unhandled)

        # Start the connection
        print("Starting WebSocket connection...")
        if not connection.start(options):
            print("Failed to start connection")
            return
        print("WebSocket connection started successfully")

        # Stream audio
        print("Downloading and sending audio...")
        response = requests.get("https://dpgr.am/spacewalk.wav", stream=True)
        # Skip WAV header
        response.raw.read(44)

        chunk_size = 8192
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                connection.send(chunk)
                time.sleep(0.1)  # Small delay between chunks

        # Wait for processing
        print("Waiting for processing to complete...")
        time.sleep(30)  # Or use a more sophisticated completion check

        # Cleanup
        connection.finish()
        print("Finished")

    except Exception as e:
        print(f"Error: {str(e)}")

# WAV Header Functions
def create_wav_header(sample_rate=24000, bits_per_sample=16, channels=1):
    """Create a WAV header with the specified parameters"""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)

    header = bytearray(44)
    # RIFF header
    header[0:4] = b'RIFF'
    header[4:8] = b'\x00\x00\x00\x00'  # File size (to be updated later)
    header[8:12] = b'WAVE'
    # fmt chunk
    header[12:16] = b'fmt '
    header[16:20] = b'\x10\x00\x00\x00'  # Subchunk1Size (16 for PCM)
    header[20:22] = b'\x01\x00'  # AudioFormat (1 for PCM)
    header[22:24] = channels.to_bytes(2, 'little')  # NumChannels
    header[24:28] = sample_rate.to_bytes(4, 'little')  # SampleRate
    header[28:32] = byte_rate.to_bytes(4, 'little')  # ByteRate
    header[32:34] = block_align.to_bytes(2, 'little')  # BlockAlign
    header[34:36] = bits_per_sample.to_bytes(2, 'little')  # BitsPerSample
    # data chunk
    header[36:40] = b'data'
    header[40:44] = b'\x00\x00\x00\x00'  # Subchunk2Size (to be updated later)

    return header

if __name__ == "__main__":
    main()
