"""Tab stage of the pipeline: detected notes -> fretboard positions.

For any pitch there are usually several playable (string, fret) pairs. We pick
one per note, preferring positions close to the previous note so the resulting
tab does not jump around the neck.
"""

import logging

from constants import MAX_FRET, OPEN_STRING_PITCHES
from models import Note, Tab, TabPosition

logger = logging.getLogger(__name__)

Position = tuple[int, int]  # string, fret


def candidate_positions(midi_pitch: int) -> list[Position]:
    """Every (string, fret) in standard tuning that produces `midi_pitch`."""
    return [
        (string, midi_pitch - open_pitch)
        for string, open_pitch in OPEN_STRING_PITCHES.items()
        if 0 <= midi_pitch - open_pitch <= MAX_FRET
    ]


def pick_string_and_fret(note: Note, prev_position: Position | None) -> Position:
    """Choose the best (string, fret) for `note` given the previous position."""

    midi_pitch = round(note.pitch_midi)
    candidates = candidate_positions(midi_pitch)

    if not candidates:
        raise ValueError(
            f"pitch {note.pitch_midi} (MIDI {midi_pitch}) is not reachable in "
            f"standard tuning within {MAX_FRET} frets"
        )

    if prev_position is None:
        # prefer the lowest fret 
        return min(candidates, key=lambda pos: (pos[1], -pos[0]))

    prev_string, prev_fret = prev_position

    def cost(pos: Position) -> float:
        string, fret = pos
        # Hand movement along the neck dominates; changing string is a minor
        # penalty; a small term breaks ties toward lower frets.
        return abs(fret - prev_fret) + 0.1 * abs(string - prev_string) + 0.01 * fret

    return min(candidates, key=cost)


def notes_to_tab(notes: list[Note]) -> Tab:
    """Turn an ordered list of notes into a `Tab`."""

    positions: list[TabPosition] = []
    prev_position: Position | None = None

    for note in notes:
        try:
            string, fret = pick_string_and_fret(note, prev_position)
        except ValueError as exc:
            logger.warning("skipping note at %.2fs: %s", note.start_time, exc)
            continue
        positions.append(TabPosition(string=string, fret=fret, time=note.start_time))
        prev_position = (string, fret)

    return Tab(positions=positions)
