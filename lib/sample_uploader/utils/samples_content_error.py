class SampleContentError(Exception):
    """                                                                        .
    Error type for managing errors which arrise at a certain position in 
    an uploaded datafile. Both sample_name/key and row/column positions are 
    included as both may be useful the the user trying to identify the source 
    of the error. However, the aboce are optional as not all the above 
    information is availible in all places the exception is thrown. 
    """
    def __init__(self, message:str, sample_name:str=None, node=None, key=None, row=None, column=None):
        """
        :param message: the error message, str
        :param sample_name: the sample name (user defined ID) related to the error, str or None
        :param node: the node name related to the error, str or None
        :param key: the key (column name) related to the error, str or None
        :param row: the zero-based index of the datafile row related to the error, int or None
        :param column: the zero-based index of the datafile column related to the error, int or None
        """
        super().__init__(message)
        self.message = message
        self.sample_name = sample_name
        self.node = node
        self.key = key
        self.row = row
        self.column = column

    def toJSONable(self):
        return {
            'message': self.message,
            'sample_name': self.sample_name,
            'node': self.node,
            'key': self.key,
            'row': self.row,
            'column': self.column,
        }