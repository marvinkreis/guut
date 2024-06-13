from guut.llm import Message, Role


TEST_CONTENT = 'Sphinx of black quartz, judge my vow'


class TestMessageConstructors:
    def test_system(self):
        msg = Message.system(TEST_CONTENT)
        assert msg.role is Role.SYSTEM
        assert msg.content == TEST_CONTENT
        assert msg.response is None

    def test_user(self):
        msg = Message.user(TEST_CONTENT)
        assert msg.role is Role.USER
        assert msg.content == TEST_CONTENT
        assert msg.response is None

    def test_assistant(self):
        msg = Message.assistant(TEST_CONTENT)
        assert msg.role is Role.ASSISTANT
        assert msg.content == TEST_CONTENT
        assert msg.response is None

    def test_from_response(self):
        # TODO
        pass
