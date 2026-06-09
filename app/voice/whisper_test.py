import sounddevice as sd
import soundfile as sf
import whisper

SAMPLE_RATE = 16000
DURATION = 5

print("🎙️ Speak now...")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32"
)

sd.wait()

sf.write("voice.wav", audio, SAMPLE_RATE)

print("Transcribing...")

model = whisper.load_model("tiny")

result = model.transcribe("voice.wav")

print("\nRecognized text:")
print(result["text"])
