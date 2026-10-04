from fakeworld import entity, snapshot
from fx import fingerprint


def test_speech_bubble_does_not_change_the_fingerprint():
    # `say` spawns a speech bubble over Claude; it must not invalidate the build gate
    area = [0, 0, 10, 10]
    furnace = entity("stone-furnace", (2, 2), size=2)
    bubble = entity("compi-speech-bubble", (4, 4), typ="speech-bubble", ghost=False)
    assert fingerprint(snapshot(area, [furnace]), area) == fingerprint(snapshot(area, [furnace, bubble]), area)


def test_new_entity_changes_the_fingerprint():
    area = [0, 0, 10, 10]
    furnace = entity("stone-furnace", (2, 2), size=2)
    chest = entity("wooden-chest", (6, 6))
    assert fingerprint(snapshot(area, [furnace]), area) != fingerprint(snapshot(area, [furnace, chest]), area)
