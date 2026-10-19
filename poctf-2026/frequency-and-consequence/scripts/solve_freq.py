#!/usr/bin/env python3 -I
"""
Frequency and Consequence (POCTF 2026, ID=91) - Audio frequency decoder.

Challenge: 16 tones encode base32 characters.
Formula: freq(ch) = 500 + 50 * index(ch)
Base32 alphabet: A=0, B=1, ..., Z=25, 2=26, 3=27, 4=28, 5=29, 6=30, 7=31

Usage: python3 -I solve_freq.py signal.wav
"""
import sys
import pathlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft

BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

def freq_to_char(freq):
    index = round((freq - 500) / 50)
    if 0 <= index < 32:
        return BASE32[index]
    return '?'

def solve(wav_path):
    sr, data = wavfile.read(wav_path)
    if len(data.shape) > 1:
        data = data[:, 0]
    data = data.astype(float)

    print(f"Sample rate: {sr}, Duration: {len(data)/sr:.2f}s, Samples: {len(data)}")

    total_duration = len(data) / sr
    num_tones = 16
    tone_duration = total_duration / num_tones

    print(f"Estimated tone duration: {tone_duration:.4f}s")

    nonce = []
    for i in range(num_tones):
        start = int(i * tone_duration * sr)
        end = int((i + 1) * tone_duration * sr)
        segment = data[start:end]

        margin = int(len(segment) * 0.1)
        if margin > 0:
            segment = segment[margin:-margin]

        fft = np.fft.rfft(segment)
        magnitudes = np.abs(fft)
        freqs = np.fft.rfftfreq(len(segment), 1.0 / sr)

        mask = (freqs >= 400) & (freqs <= 2200)
        filtered_mags = magnitudes.copy()
        filtered_mags[~mask] = 0

        peak_idx = np.argmax(filtered_mags)
        peak_freq = freqs[peak_idx]

        char = freq_to_char(peak_freq)
        nonce.append(char)

        expected = 500 + 50 * BASE32.index(char) if char != '?' else 0
        print(f"  Tone {i+1:2d}: peak={peak_freq:7.1f} Hz -> '{char}' (expected {expected} Hz)")

    result = ''.join(nonce)
    print(f"\nNonce: {result}")
    print(f"Flag: POCTF{{{result}}}")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -I solve_freq.py signal.wav")
        sys.exit(1)
    result = solve(sys.argv[1])
    outdir = pathlib.Path(sys.argv[1]).parent
    if outdir.name != "loot":
        outdir = outdir.parent / "loot"
    outdir.mkdir(exist_ok=True)
    (outdir / "flag.txt").write_text(f"POCTF{{{result}}}\n")
