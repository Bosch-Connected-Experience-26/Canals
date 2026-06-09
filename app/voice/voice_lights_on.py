import os
import tempfile
import time
import wave

import numpy as np
import sounddevice as sd
from kuksa_client.grpc import Datapoint, VSSClient

HOST = "192.168.56.6"
PORT = 55555
CLIENT_ID = 120

SAMPLE_RATE = 16000
DURATION = 4


def record_audio(filename: str):
    print("🎙️ Say: 'turn on lights'")
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    print("✅ Voice recorded")


def recognize_command():
    # Hackathon fallback: record voice, then type recognized text manually.
    # Later replace this with Whisper / Picovoice Rhino.
    text = input("Recognized text: ").lower().strip()
    return text


def switch_lights_on():
    with VSSClient(HOST, PORT) as client:
        print("Connected to KUKSA")

        client.set_current_values(
            {"Vehicle.RequestTakeOver": Datapoint(str([1, CLIENT_ID]))}
        )
        time.sleep(1)

        client.set_current_values(
            {
                "Vehicle.Body.Lights.ExteriorLightControl": Datapoint(
                    str([1, 5, CLIENT_ID])
                )
            }
        )

        print("✅ Low beam ON command sent")


def main():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_file = tmp.name

    record_audio(audio_file)
    print(f"Audio saved: {audio_file}")

    text = recognize_command()

    if ("light" in text or "lights" in text or "headlight" in text) and (
        "on" in text or "turn on" in text
    ):
        print("Intent detected: LIGHTS_ON")
        switch_lights_on()
    else:
        print("No LIGHTS_ON intent detected.")

    os.remove(audio_file)


if __name__ == "__main__":
    main()
