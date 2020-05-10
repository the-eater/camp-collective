from hashlib import sha1
import string
from typing import Optional, Any, List


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
            return f"{assembled}:{self.e}"

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
    if r14 == 0:
        return "noop"
    r: List[Any] = [0 for k in range(20)]
    r[0] = sha1()
    r[1] = 0
    r[2] = 0
    r[4] = ""
    r[5] = 0
    r[6] = 0
    r[7] = 0
    r[8] = 0
    r[9] = 0
    r[12] = r12
    r[13] = r13
    r[14] = r14
    r[15] = r15
    r[13] = 0

    def L_0x000e(r):
        if r[13] != 0:
            return 'L_0x008b'
        r[3] = to_base36(r[2])
        r[4] = f"{r[12]}{r[15]}{r[3]}"
        r[0].update(r[4].encode('utf-8'))
        r[4] = r[0].digest()
        r[0] = sha1()
        r[5] = 0
        r[6] = 0
        return 'L_0x0038'

    def L_0x0038(r):
        r[7] = len(r[4])
        if r[5] >= r[7]:
            return 'L_0x007d'
        r[7] = r[4][r[5]]
        r[8] = 8
        r[9] = 1
        if r[7] >= 0:
            return 'L_0x0044'
        return 'L_0x0042'

    def L_0x0042(r):
        r[9] = 0
        return 'L_0x0076'

    def L_0x0044(r):
        r[7] = r[4][r[5]]
        if r[7] >= r[9]:
            return 'L_0x004b'
        r[9] = 8
        return 'L_0x0076'

    def L_0x004b(r):
        r[7] = r[4][r[5]]
        if r[7] >= 2:
            return 'L_0x0052'
        r[9] = 7
        return 'L_0x0076'

    def L_0x0052(r):
        r[7] = r[4][r[5]]
        if r[7] >= r[8]:
            return 'L_0x0058'
        r[9] = 6
        return 'L_0x0076'

    def L_0x0058(r):
        r[7] = r[4][r[5]]
        if r[7] >= 16:
            return 'L_0x0060'
        r[9] = 5
        return 'L_0x0076'

    def L_0x0060(r):
        r[7] = r[4][r[5]]
        if r[7] >= 32:
            return 'L_0x0068'

        r[9] = 4
        return 'L_0x0076'

    def L_0x0068(r):
        r[7] = r[4][r[5]]
        if r[7] >= 64:
            return 'L_0x0070'

        r[9] = 3
        return 'L_0x0076'

    def L_0x0070(r):
        r[7] = r[4][r[5]]
        if r[7] >= 128:
            return 'L_0x0042'

        return 'L_0x0076'

    def L_0x0076(r):
        r[6] = r[6] + r[9]
        if r[9] == r[8]:
            return 'L_0x007a'

        return 'L_0x007d'

    def L_0x007a(r):
        r[5] = r[5] + 1
        return 'L_0x0038'

    def L_0x007d(r):
        if r[6] < r[14]:
            return 'L_0x0080'
        r[13] = r[3]
        return 'L_0x0080'

    def L_0x0080(r):
        r[2] = r[2] + 1
        return 'L_0x000e'

    def L_0x0083(r):
        print("bandcamp: Unable to compute answer <exception probably goes here or whatever>")

    calls = {
        'L_0x000e': L_0x000e,
        'L_0x0038': L_0x0038,
        'L_0x0042': L_0x0042,
        'L_0x0044': L_0x0044,
        'L_0x004b': L_0x004b,
        'L_0x0052': L_0x0052,
        'L_0x0058': L_0x0058,
        'L_0x0060': L_0x0060,
        'L_0x0068': L_0x0068,
        'L_0x0070': L_0x0070,
        'L_0x0076': L_0x0076,
        'L_0x007a': L_0x007a,
        'L_0x007d': L_0x007d,
        'L_0x0080': L_0x0080,
        'L_0x0083': L_0x0083,
    }

    try:
        current = "L_0x000e"
        while current != "L_0x008b":
            current = calls[current](r)
    except Exception as e:
        print(e)
        # return 'L_0x0083'

    r13 = r[13]
    return r13


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
