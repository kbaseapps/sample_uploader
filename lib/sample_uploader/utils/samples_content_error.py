import warnings

class SampleContentWarning(Warning):
    """
    Exception (Warning) type for managing errors which arrise at a certain position in 
    an uploaded datafile. Both sample_name/key and row/column positions are 
    included as both may be useful the the user trying to identify the source 
    of the error. However, the above are optional as not all the above 
    information is availible in all places the exception is thrown. This can be thrown, 
    or can be passed to `warnings.warn` within a `SampleContentWarningContext` context
    block.
    """
    def __init__(self, message:str, sample_name:str=None, node=None, key=None, row=None, column=None, severity='error'):
        """
        :param message: the error message, str
        :param sample_name: the sample name (user defined ID) related to the error, str or None
        :param node: the node name related to the error, str or None
        :param key: the key (column name) related to the error, str or None
        :param row: the zero-based index of the datafile row related to the error, int or None
        :param column: the zero-based index of the datafile column related to the error, int or None
        :param severity: severity of the exception ('error','warning'), string (default: 'error')
        """
        super().__init__(message)
        self.message = message
        self.sample_name = sample_name
        self.node = node
        self.key = key
        self.row = row
        self.column = column
        self.severity = severity
        if(self.severity not in ('error','warning')):
            raise ValueError(f'Invalid severity for SampleContentWarning: {self.severity}')

    def toJSONable(self):
        return {
            'message': self.message,
            'sample_name': self.sample_name,
            'node': self.node,
            'key': self.key,
            'row': self.row,
            'column': self.column,
            'severity': self.severity
        }

class SampleContentWarningContext:
    """
    Context manager to capture `SampleContentWarning`s which are raised as
    warnings using `warnings.warn`. Use a `with as` block to capture warnings.
    Warnings can then be accessed as an iterator or with the `getErrors` method.
    """
    def __init__(self, severities):
        self.severities = severities
        self.catcher = warnings.catch_warnings(record=True)
        self.captured = []
        self.sample_warnings = []

    def getErrors(self, severity=None):
        while len(self.captured):
            warning = self.captured.pop()
            if  isinstance(warning.message, SampleContentWarning):
                err = warning.message
                if err.severity in self.severities:
                    self.sample_warnings.append(warning.message)
            else:
                warnings.warn_explicit(
                    warning.message,
                    warning.category,
                    warning.filename,
                    warning.lineno)
        errs = self.sample_warnings
        if severity is not None:
            errs = filter(lambda e: e.severity == severity, errs)
        return errs

    def __getitem__(self, index):
        return self.getErrors()[index]

    def __enter__(self):
        self.captured = self.catcher.__enter__()
        warnings.simplefilter("always", category=SampleContentWarning)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.catcher.__exit__(exc_type, exc_value, traceback)
        self.getErrors()
