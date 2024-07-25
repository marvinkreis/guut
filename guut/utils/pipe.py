from typing import Any


class Sentinel:
    def __call__(self, value) -> "Pipe":
        return Pipe(value)

    def when(self, condition, value):
        if condition:
            return value
        else:
            return lambda x: x

    def format(self, format_string, *args, **kwargs):
        def retv(text):
            return format_string.format(*args, **kwargs, p=text)

        return retv


p = Sentinel()


class Pipe:
    def __init__(self, value: Any):
        self.value = value

    def apply(self, function, *args, **kwargs):
        self.value = function(self.value, *args, **kwargs)
        return self

    def get(self):
        return self.value

    def __or__(self, value) -> "Pipe":
        if value is p:
            return self.value
        if isinstance(value, tuple):
            return self.apply(*value)
        if isinstance(value, list):
            if not value[0]:
                return self
            else:
                return self.apply(*value[1:])
        else:
            return self.apply(value)
