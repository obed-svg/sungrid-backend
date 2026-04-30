import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestPollReclosersCommand:
    def test_poll_once_no_projects(self, capsys):
        call_command("poll_reclosers", "--once")
        captured = capsys.readouterr()
        assert "0 enabled project(s)" in captured.out
