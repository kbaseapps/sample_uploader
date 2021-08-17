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
    def __init__(self, message:str, sample_name:str=None, node=None, key=None, subkey=None, row=None, column=None, severity='error'):
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
        self.subkey = subkey
        self.row = row
        self.column = column
        self.severity = severity
        self.column_name = None if subkey is not None else key
        if(self.severity not in ('error','warning')):
            raise ValueError(f'Invalid severity for SampleContentWarning: {self.severity}')

    def toJSONable(self):
        return {
            'message': self.message,
            'sample_name': self.sample_name,
            'node': self.node,
            'key': self.key,
            'subkey': self.subkey,
            'row': self.row,
            'column': self.column,
            'column_name': self.column_name,
            'severity': self.severity
        }

class SampleContentWarningContext:
    """
    Context manager to capture `SampleContentWarning`s which are raised as
    warnings using `warnings.warn`. Use a `with as` block to capture warnings.
    Warnings can then be accessed using the `get` method.
    """
    def __init__(self):
        self._severities = ("error","warning")
        self._warning_catcher = warnings.catch_warnings(record=True)
        self._caught = []
        self._targeted = []
        self._other_warnings = []

    def get(self, severity=None):
        self._processCaptured()
        if severity is not None:
            return list(filter(lambda e: e.severity == severity, self._targeted))
        else:
            return list(self._targeted)

    def _processCaptured(self):
        while self._caught:
            w = self._caught.pop()
            if  isinstance(w.message, SampleContentWarning) \
                    and w.message.severity in self._severities:
                self._targeted.append(w.message)
            else:
                self._other_warnings.append(w)

    def __enter__(self):
        self._caught = self._warning_catcher.__enter__()
        warnings.simplefilter("always", category=SampleContentWarning)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._warning_catcher.__exit__(exc_type, exc_value, traceback)
        self._processCaptured()
        while self._other_warnings:
            w = self._other_warnings.pop()
            warnings.warn_explicit(
                    w.message,
                    w.category,
                    w.filename,
                    w.lineno)

    def __getitem__(self, index):
        return self._targeted[index]
