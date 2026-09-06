import pytest

from models import Note
from tabs import candidate_positions, notes_to_tab, pick_string_and_fret


def note(midi: float, start: float = 0.0) -> Note:
    return Note(pitch_midi=midi, start_time=start, duration=0.5)


# === candidate_positions ================================================


def test_candidates_for_low_e():
    # MIDI 40 = low E2, only reachable as the open 6th string.
    assert candidate_positions(40) == [(6, 0)]


def test_candidates_for_e4_span_the_neck():
    positions = candidate_positions(64)  # E4
    assert (1, 0) in positions  # open high E
    assert (2, 5) in positions  # 5th fret B string
    assert all(0 <= fret <= 24 for _, fret in positions)


# === pick_string_and_fret ==============================================


def test_open_low_e_with_no_history():
    assert pick_string_and_fret(note(40), None) == (6, 0)


def test_no_history_prefers_lowest_fret():
    # A4 (MIDI 69) is playable at (1,5),(2,10),(3,14),(4,19),(5,24); pick (1,5).
    assert pick_string_and_fret(note(69), None) == (1, 5)


def test_stays_near_previous_position():
    # Previous note high up the 5th string; next pitch A3 (MIDI 57) is
    # reachable at (4,7),(5,12),(3,2)... expect the one closest to fret 12.
    prev = (5, 12)
    string, fret = pick_string_and_fret(note(57), prev)
    assert (string, fret) == (5, 12)


def test_unreachable_pitch_raises():
    with pytest.raises(ValueError, match="not reachable"):
        pick_string_and_fret(note(20), None)  # far below the guitar's range


# === notes_to_tab ======================================================


def test_empty_notes_gives_empty_tab():
    assert notes_to_tab([]).positions == []


def test_tab_preserves_order_and_times():
    notes = [note(40, 0.0), note(45, 1.0), note(50, 2.0)]
    tab = notes_to_tab(notes)
    assert [p.time for p in tab.positions] == [0.0, 1.0, 2.0]
    assert tab.positions[0] == tab.positions[0].__class__(string=6, fret=0, time=0.0)
