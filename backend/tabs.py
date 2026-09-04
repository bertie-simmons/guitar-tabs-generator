from models import Note, TabData
from constants import OPEN_STRING_PITCHES, MAX_FRET

def pick_string_and_fret(
    note: Note, prev_position: tuple[int, int] | None
) -> tuple[int, int]:
    
    midi_pitch = round(note.pitch)

    candidates = [
        (string, midi_pitch - open_pitch)
        for string, open_pitch in OPEN_STRING_PITCHES.items()
        if 0 <= midi_pitch - open_pitch <= MAX_FRET
    ]

    if not candidates:
        raise ValueError(
            f"pitch {note.pitch} (MIDI {midi_pitch}) is not reachable in "
            f"standard tuning within {MAX_FRET} frets"
        )

    if prev_position is None:
        return min(candidates, key=lambda pos: pos[1])

    prev_string, prev_fret = prev_position

    def distance(pos: tuple[int, int]) -> float:
        string, fret = pos
        return abs(fret - prev_fret) + 0.1 * abs(string - prev_string)

    return min(candidates, key=distance)


def notes_to_tab(notes: list[Note]) -> list[TabData]:
    
    tab_entries = []
    prev_position: tuple[int, int] | None = None

    for note in notes:
        string, fret = pick_string_and_fret(note, prev_position)
        tab_entries.append(TabData(string=string, fret=fret, time=note.start_time))
        prev_position = (string, fret)

    return tab_entries