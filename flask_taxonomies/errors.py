
class TaxonomyDeleteError(Exception):
    """Taxonomy deletion error."""
    def __init__(self, message, records, *args, **kwargs):
        self.message = message
        self._records = records

    @property
    def records(self):
        return [r.record_uuid for r in self._records]

    def __repr__(self):
        return self.message

