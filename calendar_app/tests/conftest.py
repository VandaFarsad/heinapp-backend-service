from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_caldav() -> Generator[MagicMock, None, None]:
    """Mock CalDAVService globally to prevent real CalDAV connections in all calendar tests."""
    mock_service = MagicMock()
    mock_service.__enter__ = MagicMock(return_value=mock_service)
    mock_service.__exit__ = MagicMock(return_value=False)
    mock_service.get_events.return_value = []

    with patch("calendar_app.views.CalDAVService") as mock_cls:
        mock_cls.return_value = mock_service
        yield mock_service
