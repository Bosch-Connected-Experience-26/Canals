import os
import subprocess
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


def record_audio(filename):
    print("🎙️ Say: 'lights off'")
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16"
    )
    sd.wait()

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())


def transcribe_with_macos(audio_file):
    """
    Simple fallback:
    For now this does NOT use real STT.
    It asks you to confirm what you said.
    This avoids PyAudio/Whisper setup problems.
    """
    text = input("Type what voice command was recognized: ").lower().strip()
    return text


def switch_lights_off():
    with VSSClient(HOST, PORT) as client:
        print("Connected to KUKSA")

        client.set_current_values(
            {"Vehicle.RequestTakeOver": Datapoint(str([1, CLIENT_ID]))}
        )
        time.sleep(1)

        client.set_current_values(
            {
                "Vehicle.Body.Lights.ExteriorLightControl": Datapoint(
                    str([0, 5, CLIENT_ID])
                )
            }
        )
        time.sleep(1)

        client.set_current_values(
            {
                "Vehicle.Body.Lights.ExteriorLightControl": Datapoint(
                    str([0, 0, CLIENT_ID])
                )
            }
        )

        print("✅ Lights OFF command sent")


def main():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_file = tmp.name

    record_audio(audio_file)

    print(f"Audio saved: {audio_file}")

    text = transcribe_with_macos(audio_file)

    if "light" in text and "off" in text:
        print("Intent detected: LIGHTS_OFF")
        switch_lights_off()
    else:
        print("No matching intent detected.")

    os.remove(audio_file)


if __name__ == "__main__":
    main()
