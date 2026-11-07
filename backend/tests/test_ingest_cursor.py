"""Jetstream cursor moves only through events that were actually kept."""
from backend.app.ingest.jetstream import (
    IngestState,
    ack_durable_cursor,
    begin_firehose_connection,
    note_firehose_position,
)


def test_full_queue_does_not_skip_the_dropped_event():
    state = IngestState()
    note_firehose_position(state, 100, matched=False, fully_queued=False, queue_empty=True)
    assert state.high_water_us == 100
    assert state.last_cursor == 100

    note_firehose_position(state, 200, matched=True, fully_queued=True, queue_empty=False)
    assert state.high_water_us == 200
    assert state.last_cursor == 100
    ack_durable_cursor(state, queue_empty=True, committed_us=200)
    assert state.last_cursor == 200

    state.dropped_events += 1
    note_firehose_position(state, 300, matched=True, fully_queued=False, queue_empty=False)
    assert state.cursor_blocked is True
    assert state.high_water_us == 200

    note_firehose_position(state, 400, matched=False, fully_queued=False, queue_empty=True)
    assert state.high_water_us == 200
    assert state.last_cursor == 200

    ack_durable_cursor(state, queue_empty=True, committed_us=400)
    assert state.last_cursor == 200

    begin_firehose_connection(state)
    assert state.cursor_blocked is False
    assert state.high_water_us == 200
