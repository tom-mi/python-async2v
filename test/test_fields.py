import pytest

from async2v.fields import Latest, Event, Buffer, History


@pytest.mark.parametrize('input_data, more_input_data, expected_value, expected_updated', [
    ([1, 2], [3, 4], 4, True),
    ([1, 2], [], 2, False),
    ([], [], None, False),
])
def test_latest_field(input_data, more_input_data, expected_value, expected_updated):
    field = Latest('key')
    for v in input_data:
        field._set(Event('key', v))
    field._switch()
    for v in more_input_data:
        field._set(Event('key', v))
    field._switch()

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
        field._set(Event('key', v))
    field._switch()
    for v in more_input_data:
        field._set(Event('key', v))
    field._switch()

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
        field._set(Event('key', v))
    field._switch()
    for v in more_input_data:
        field._set(Event('key', v))
    field._switch()

    assert field.updated == expected_updated
    assert field.values == expected_values
