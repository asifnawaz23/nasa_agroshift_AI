"""Exception types so /api/analyze/ can return a clear 503 message."""


class DataSourceError(Exception):
    """Base error for any external data source problem."""

    def __init__(self, source, message):
        self.source = source
        super().__init__(f"{source}: {message}")


class DataSourceTimeout(DataSourceError):
    """The service did not answer in time."""


class DataSourceBadResponse(DataSourceError):
    """The service answered, but with an error code or unusable data."""
