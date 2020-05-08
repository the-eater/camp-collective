from hashlib import sha1
import string
from typing import Optional


def to_base36(num: int) -> str:
    chars = string.digits + string.ascii_lowercase

    if num == 0:
        return chars[0]

    sign = num < 0
    num = abs(num)

    digits = []

    while num:
        rest = num % 36
        num -= rest
        digits.append(chars[rest])
        num //= 36

    if sign:
        digits.append('-')

    digits.reverse()

    return ''.join(digits)


class PoW:
    assembled: str
    b: int
    c: int
    d: str
    e: Optional[str]

    def __init__(self, assembled: Optional[str] = None, b: int = 1, c: int = 10, d: str = "", e: Optional[str] = None):
        if assembled is not None:
            self.parse(assembled)
            return

        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.assembled = str(self)

    def __str__(self):
        assembled = f"{self.b}:{self.c}:{self.d}"
        if self.e is not None:
            return f"{assembled}:${self.e}"

        return assembled

    def parse(self, assembled: str):
        self.assembled = assembled
        split = assembled.split(':')
        self.b = int(split[0])
        self.c = int(split[1])
        self.d = split[2]

        if len(split) > 3:
            self.e = split[3]
        else:
            self.e = None


def scramble_pow(r12: str, r13: int, r14: int, r15: str) -> str:
    # TODO
    pass


class PoWHandler:
    pow: Optional[PoW]

    def set_pow(self, proof: str):
        self.pow = PoW(assembled=proof)

    def create_pow(self, extra: str):
        return PoW(b=self.pow.b, c=self.pow.c, d=self.pow.d, e=self.make_derivative(extra))

    def make_derivative(self, extra: str) -> str:
        if self.pow is None:
            return "n0pe"

        return scramble_pow(extra, self.pow.b, self.pow.c, self.pow.d)