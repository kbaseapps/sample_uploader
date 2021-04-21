class SampleContentError(Exception):
    def __init__(self, message, sample_name=None, node=None, key=None, row=None, column=None):            
        super().__init__(message)
        self.sample_name = sample_name
        self.node = node
        self.key = key
        self.row = row
        self.column = column