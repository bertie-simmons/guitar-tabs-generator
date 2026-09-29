OPEN_STRING_PITCHES: dict[int, int] = {
    1: 64,  # E4
    2: 59,  # B3
    3: 55,  # G3
    4: 50,  # D3
    5: 45,  # A2
    6: 40,  # E2
}

MAX_FRET = 24

SAMPLE_RATE = 22050

# Peak amplitude below which a clip is treated as silence
SILENCE_THRESHOLD = 1e-4
