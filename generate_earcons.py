import wave
import struct
import math
import os

SAMPLE_RATE = 44100

def generate_tone(freqs, durations_ms, filename, volume=0.3):
    """Generate a sequence of frequencies with exponential decay (soft attack/release)."""
    samples = []
    for freq, duration_ms in zip(freqs, durations_ms):
        num_samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
        for i in range(num_samples):
            t = float(i) / SAMPLE_RATE
            # Sine wave
            sample = math.sin(2 * math.pi * freq * t)
            # Apply an envelope: quick attack, smooth decay
            envelope = math.exp(-3.0 * i / num_samples)
            if i < 200: # 5ms attack
                envelope *= (i / 200.0)
            
            value = int(sample * envelope * volume * 32767.0)
            samples.append(struct.pack('<h', value))
            
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(b''.join(samples))

if __name__ == "__main__":
    os.makedirs(r"assets\sounds", exist_ok=True)
    
    # Start: Soft ascending C major third (C5 -> E5)
    generate_tone([523.25, 659.25], [100, 200], r"assets\sounds\start.wav", volume=0.4)
    
    # Stop: Soft descending C major third (E5 -> C5)
    generate_tone([659.25, 523.25], [100, 200], r"assets\sounds\stop.wav", volume=0.4)
    
    # Success: Bright resolving chord sequence (C5 -> G5 -> C6)
    generate_tone([523.25, 783.99, 1046.50], [80, 80, 250], r"assets\sounds\success.wav", volume=0.3)
    
    # Error: Low muted thump (C3 -> G2)
    generate_tone([130.81, 98.00], [150, 200], r"assets\sounds\error.wav", volume=0.5)
    print("Earcons generated successfully.")
