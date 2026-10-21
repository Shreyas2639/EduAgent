from pathlib import Path
from streamlit.testing.v1 import AppTest

from memory import long_term_db as db


def test_ui_approval_correction_and_new_thread(tutor):
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    app.text_input[0].set_value("learner")
    next(button for button in app.button if button.label == "Start session").click().run()
    assert not app.exception
    first_thread = app.session_state["thread_id"]
    # Retain two real records, including an explicit beginner level.
    app.selectbox[0].select("bullet_points")
    next(button for button in app.button if button.label == "Review memory changes").click().run()
    assert app.session_state["pending_approval"]
    assert db.get_memory_records("learner") == []
    next(button for button in app.button if button.label == "Approve memory update").click().run()
    assert len(db.get_memory_records("learner")) == 2
    assert not app.exception
    next(button for button in app.button if button.label == "New thread — keep approved memory").click().run()
    assert app.session_state["thread_id"] != first_thread
    assert app.session_state["messages"] == []
    assert len(db.get_memory_records("learner")) == 2
    app.selectbox[0].select("worked_examples")
    next(button for button in app.button if button.label == "Review memory changes").click().run()
    next(button for button in app.button if button.label == "Reject memory update").click().run()
    assert not app.exception
    assert db.get_learner_profile("learner")["preferred_style"] == "bullet_points"
