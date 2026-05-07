class FakeCursor:
    def __init__(self, fetch_result=None):
        self.fetch_result = fetch_result
        self.executed_query = None
        self.executed_values = None
        self.closed = False

    def execute(self, query, values=None):
        self.executed_query = query
        self.executed_values = values

    def fetchone(self):
        return self.fetch_result

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, fetch_result=None):
        self.cursor_instance = FakeCursor(fetch_result=fetch_result)
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True
