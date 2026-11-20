from the_watcher.watcher_ai import TheWatcherEngine


def test_speech_to_movement_intent():
    engine = TheWatcherEngine()
    result = engine.parse_speech_intent("I step 3 squares north towards the chest", "Valeros")
    assert result.action_type == "move"
    assert result.parameters["steps"] == 3
    assert result.parameters["direction"] == "north"
    assert result.parameters["dy"] == -3
    assert "Valeros" in result.watcher_reply


def test_speech_to_attack_intent():
    engine = TheWatcherEngine()
    result = engine.parse_speech_intent("I slash at the goblin with my sword!", "Valeros")
    assert result.action_type == "attack"
    assert "Valeros" in result.watcher_reply
