import pytest
import queue

from async2v.fields import Latest, Event, Buffer, History, LatestBy, AveragingOutput


@pytest.mark.parametrize('input_data, more_input_data, expected_value, expected_updated', [
    ([1, 2], [3, 4], 4, True),
    ([1, 2], [], 2, False),
    ([], [], None, False),
])
def test_latest_field(input_data, more_input_data, expected_value, expected_updated):
    field = Latest('key')
    for v in input_data:
        field.set(Event('key', v))
    field.switch()
    for v in more_input_data:
        field.set(Event('key', v))
    field.switch()

    assert field.updated == expected_updated
    assert field.value == expected_value


@pytest.mark.parametrize('input_data, more_input_data, expected_values, expected_updated', [
    ([1, 2], [3, 4], [3, 4], True),
    ([1, 2], [], [], False),
    ([], [], [], False),
])
def test_buffer_field(input_data, more_input_data, expected_values, expected_updated):
    field = Buffer('key')
    for v in input_data:
        field.set(Event('key', v))
    field.switch()
    for v in more_input_data:
        field.set(Event('key', v))
    field.switch()

    assert field.updated == expected_updated
    assert field.values == expected_values


@pytest.mark.parametrize('input_data, more_input_data, expected_values, expected_updated', [
    ([1, 2], [3, 4], [2, 3, 4], True),
    ([1, 2], [], [1, 2], False),
    ([], [], [], False),
])
def test_history_field(input_data, more_input_data, expected_values, expected_updated):
    field = History('key', 3)
    for v in input_data:
        field.set(Event('key', v))
    field.switch()
    for v in more_input_data:
        field.set(Event('key', v))
    field.switch()

    assert field.updated == expected_updated
    assert field.values == expected_values


@pytest.mark.parametrize('input_data, more_input_data, expected_values, expected_updated', [
    (['a', 'ab'], ['c', 'def'], {1: 'c', 2: 'ab', 3: 'def'}, True),
    (['a', 'b'], [], {1: 'b'}, False),
    ([], [], {}, False),
])
def test_latest_key_field(input_data, more_input_data, expected_values, expected_updated):
    field = LatestBy('key', lambda it: len(it))
    for v in input_data:
        field.set(Event('key', v))
    field.switch()
    for v in more_input_data:
        field.set(Event('key', v))
    field.switch()

    assert field.updated == expected_updated
    assert field.value_dict == expected_values


def test_averaging_output_field():
    field = AveragingOutput('key', count=4)
    q = queue.Queue()
    field.set_queue(q)

    field.push(0)
    field.push(1)
    field.push(2)
    field.push(3)
    field.push(4)
    field.push(5)
    field.push(6)
    field.push(7)

    assert q.qsize() == 2
    assert q.get().value == 1.5
    assert q.get().value == 5.5
