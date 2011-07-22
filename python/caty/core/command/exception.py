
class ScriptError(Exception):
    pass

class PipelineErrorExit(Exception):
    def __init__(self, o):
        self.json_obj = o

class PipelineInterruption(Exception):
    def __init__(self, o):
        self.json_obj = o


