class questionnairerror(Exception):
    pass


class InvalidGraphState(questionnairerror):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
