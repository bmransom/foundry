from calc import running_max


def test_running_max_tracks_the_max():
    assert running_max([1, 3, 2, 5, 4]) == [1, 3, 3, 5, 5]


def test_running_max_preserves_length():
    values = [4, 1, 7, 7, 2]
    assert len(running_max(values)) == len(values)
