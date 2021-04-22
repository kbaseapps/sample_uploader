class SampleContentError(Exception):
    def __init__(self, message, sample_name=None, node=None, key=None, row=None, column=None):            
        super().__init__(message)
        self.message = message
        self.sample_name = sample_name
        self.node = node
        self.key = key
        self.row = row
        self.column = column

    def locatedMessage(self):
        sample = self.sample_name if self.sample_name is not None else ""
        key = self.key if self.key is not None else ""
        row = self.row if self.row is not None else ""
        column = self.column if self.column is not None else ""
        return f"({sample},{key})[{row},{column}]: {self.message}"