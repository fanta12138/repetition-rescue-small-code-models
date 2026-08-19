"""Self-built single-file debug benchmark (20 tasks).

Purpose: contamination-free fast-iteration benchmark for E0.
Each task: one buggy function/class + pytest tests that FAIL on the buggy
code and PASS on the fixed code.

Fields per task:
    task_id     : dbg001..dbg020
    bug_type    : taxonomy label (for failure analysis)
    description : shown to the model
    buggy_code  : shown to the model
    test_code   : run in sandbox; never shown to the model
    fixed_code  : GOLD reference, used ONLY by scripts/verify_tasks.py;
                  NEVER feed this to the model.

Bug types covered: off_by_one, missing_normalization, wrong_initialization,
loop_condition, wrong_order, wrong_direction, wrong_constant, shallow_vs_deep,
duplicate_handling, missing_case, wrong_base_case, boundary_condition,
dropped_tail, tie_breaking, wrong_dimension, state_update, wrong_divisor,
shallow_merge, off_by_one_decode, recency_update.
"""
from __future__ import annotations

import json

TASKS: list[dict] = []


def _add(task_id, bug_type, description, buggy_code, test_code, fixed_code):
    TASKS.append(
        {
            "task_id": task_id,
            "bug_type": bug_type,
            "description": description,
            "buggy_code": buggy_code,
            "test_code": test_code,
            "fixed_code": fixed_code,
        }
    )


# ---------------------------------------------------------------- dbg001
_add(
    "dbg001", "off_by_one",
    "sum_evens(n) 应返回闭区间 [0, n] 内所有偶数之和（包含 n 本身，n 为非负整数）。"
    "当前实现在 n 为偶数时漏掉了 n。请修复。",
    '''def sum_evens(n):
    """返回 [0, n] 闭区间内所有偶数之和。"""
    total = 0
    for i in range(0, n, 2):
        total += i
    return total
''',
    '''from solution import sum_evens


def test_sum_evens_includes_n():
    assert sum_evens(10) == 30  # 0+2+4+6+8+10


def test_sum_evens_small():
    assert sum_evens(6) == 12
    assert sum_evens(1) == 0
    assert sum_evens(0) == 0


def test_sum_evens_odd_n():
    assert sum_evens(7) == 12  # 0+2+4+6
''',
    '''def sum_evens(n):
    """返回 [0, n] 闭区间内所有偶数之和。"""
    total = 0
    for i in range(0, n + 1, 2):
        total += i
    return total
''',
)

# ---------------------------------------------------------------- dbg002
_add(
    "dbg002", "missing_normalization",
    "is_palindrome(s) 判断字符串是否为回文，要求忽略大小写，且只考虑字母和数字。"
    "当前实现没有忽略大小写。请修复。",
    '''def is_palindrome(s):
    """忽略大小写与标点，判断 s 是否为回文。"""
    cleaned = "".join(ch for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]
''',
    '''from solution import is_palindrome


def test_palindrome_mixed_case():
    assert is_palindrome("RaceCar") is True


def test_palindrome_sentence():
    assert is_palindrome("A man, a plan, a canal: Panama") is True


def test_not_palindrome():
    assert is_palindrome("hello") is False
''',
    '''def is_palindrome(s):
    """忽略大小写与标点，判断 s 是否为回文。"""
    cleaned = "".join(ch for ch in s if ch.isalnum()).lower()
    return cleaned == cleaned[::-1]
''',
)

# ---------------------------------------------------------------- dbg003
_add(
    "dbg003", "wrong_initialization",
    "fib(n) 返回斐波那契数，约定 fib(0)=0, fib(1)=1。当前实现的初始值有误，"
    "返回的是 fib(n+1)。请修复。",
    '''def fib(n):
    """返回第 n 个斐波那契数（fib(0)=0, fib(1)=1）。"""
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a
''',
    '''from solution import fib


def test_fib_base():
    assert fib(0) == 0
    assert fib(1) == 1


def test_fib_values():
    assert fib(2) == 1
    assert fib(10) == 55
''',
    '''def fib(n):
    """返回第 n 个斐波那契数（fib(0)=0, fib(1)=1）。"""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
''',
)

# ---------------------------------------------------------------- dbg004
_add(
    "dbg004", "loop_condition",
    "binary_search(arr, target) 在升序列表 arr 中查找 target，返回下标；不存在返回 -1。"
    "当前循环条件有误，会漏掉某些合法位置。请修复。",
    '''def binary_search(arr, target):
    """升序数组二分查找，返回下标；不存在返回 -1。"""
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
    '''from solution import binary_search


def test_single_element():
    assert binary_search([5], 5) == 0
    assert binary_search([5], 3) == -1


def test_last_element():
    assert binary_search([1, 3, 5, 7], 7) == 3


def test_general():
    assert binary_search([1, 3, 5, 7], 3) == 1
    assert binary_search([1, 3, 5, 7], 4) == -1
''',
    '''def binary_search(arr, target):
    """升序数组二分查找，返回下标；不存在返回 -1。"""
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
)

# ---------------------------------------------------------------- dbg005
_add(
    "dbg005", "wrong_order",
    "dedupe_keep_order(items) 对列表去重，且必须保持元素第一次出现的顺序。"
    "当前实现破坏了原始顺序。请修复。",
    '''def dedupe_keep_order(items):
    """去重并保持元素首次出现的顺序。"""
    return sorted(set(items))
''',
    '''from solution import dedupe_keep_order


def test_keeps_first_occurrence_order():
    assert dedupe_keep_order([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_basic():
    assert dedupe_keep_order([]) == []
    assert dedupe_keep_order([1, 1, 1]) == [1]
''',
    '''def dedupe_keep_order(items):
    """去重并保持元素首次出现的顺序。"""
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
''',
)

# ---------------------------------------------------------------- dbg006
_add(
    "dbg006", "wrong_direction",
    "merge_dicts(base, override) 合并两个字典，要求 override 中的同名键覆盖 base。"
    "当前实现的覆盖方向反了。请修复。",
    '''def merge_dicts(base, override):
    """合并字典，override 的同名键应覆盖 base。"""
    result = dict(override)
    result.update(base)
    return result
''',
    '''from solution import merge_dicts


def test_override_wins():
    assert merge_dicts({"a": 1}, {"a": 2}) == {"a": 2}


def test_union():
    assert merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
''',
    '''def merge_dicts(base, override):
    """合并字典，override 的同名键应覆盖 base。"""
    result = dict(base)
    result.update(override)
    return result
''',
)

# ---------------------------------------------------------------- dbg007
_add(
    "dbg007", "wrong_constant",
    "celsius_to_fahrenheit(c) 将摄氏度转换为华氏度（公式 F = C * 9/5 + 32）。"
    "当前实现使用了错误的常数。请修复。",
    '''def celsius_to_fahrenheit(c):
    """摄氏度转华氏度。"""
    return c * 9 / 5 + 31
''',
    '''from solution import celsius_to_fahrenheit


def test_freezing():
    assert celsius_to_fahrenheit(0) == 32


def test_boiling():
    assert celsius_to_fahrenheit(100) == 212


def test_body():
    assert abs(celsius_to_fahrenheit(37) - 98.6) < 1e-9
''',
    '''def celsius_to_fahrenheit(c):
    """摄氏度转华氏度。"""
    return c * 9 / 5 + 32
''',
)

# ---------------------------------------------------------------- dbg008
_add(
    "dbg008", "shallow_vs_deep",
    "flatten(nested) 应递归地展平任意深度的嵌套列表。当前实现只展平了一层。请修复。",
    '''def flatten(nested):
    """递归展平嵌套列表。"""
    out = []
    for x in nested:
        if isinstance(x, list):
            out.extend(x)
        else:
            out.append(x)
    return out
''',
    '''from solution import flatten


def test_deep():
    assert flatten([1, [2, [3, [4]]]]) == [1, 2, 3, 4]


def test_flat_input():
    assert flatten([1, 2, 3]) == [1, 2, 3]
    assert flatten([]) == []
''',
    '''def flatten(nested):
    """递归展平嵌套列表。"""
    out = []
    for x in nested:
        if isinstance(x, list):
            out.extend(flatten(x))
        else:
            out.append(x)
    return out
''',
)

# ---------------------------------------------------------------- dbg009
_add(
    "dbg009", "duplicate_handling",
    "second_largest(nums) 返回列表中第二大的『不同』数值（nums 至少含两个不同的数）。"
    "当前实现在存在重复最大值时出错。请修复。",
    '''def second_largest(nums):
    """返回第二大的不同数值。"""
    s = sorted(nums)
    return s[-2]
''',
    '''from solution import second_largest


def test_duplicates():
    assert second_largest([5, 5, 3]) == 3


def test_simple():
    assert second_largest([1, 2]) == 1
    assert second_largest([9, 1, 9, 4]) == 4
''',
    '''def second_largest(nums):
    """返回第二大的不同数值。"""
    unique = sorted(set(nums))
    return unique[-2]
''',
)

# ---------------------------------------------------------------- dbg010
_add(
    "dbg010", "missing_case",
    "count_vowels(s) 统计字符串中元音字母（a, e, i, o, u）的个数，大小写均需统计。"
    "当前实现遗漏了大写字母。请修复。",
    '''def count_vowels(s):
    """统计元音字母个数（大小写均计入）。"""
    return sum(1 for ch in s if ch in "aeiou")
''',
    '''from solution import count_vowels


def test_uppercase_vowels():
    assert count_vowels("Education") == 5  # E u a i o


def test_basic():
    assert count_vowels("rhythm") == 0
    assert count_vowels("") == 0
''',
    '''def count_vowels(s):
    """统计元音字母个数（大小写均计入）。"""
    return sum(1 for ch in s.lower() if ch in "aeiou")
''',
)

# ---------------------------------------------------------------- dbg011
_add(
    "dbg011", "wrong_base_case",
    "gcd(a, b) 用辗转相除法返回两个正整数的最大公约数。当前递归的边界返回值有误。请修复。",
    '''def gcd(a, b):
    """辗转相除法求最大公约数。"""
    if b == 0:
        return b
    return gcd(b, a % b)
''',
    '''from solution import gcd


def test_gcd():
    assert gcd(12, 18) == 6


def test_coprime():
    assert gcd(7, 13) == 1


def test_divides():
    assert gcd(10, 5) == 5
''',
    '''def gcd(a, b):
    """辗转相除法求最大公约数。"""
    if b == 0:
        return a
    return gcd(b, a % b)
''',
)

# ---------------------------------------------------------------- dbg012
_add(
    "dbg012", "boundary_condition",
    "is_prime(n) 判断整数 n 是否为素数。当前实现对 n < 2 的边界处理错误。请修复。",
    '''def is_prime(n):
    """判断 n 是否为素数。"""
    if n < 2:
        return True
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True
''',
    '''from solution import is_prime


def test_not_prime_small():
    assert is_prime(1) is False
    assert is_prime(0) is False
    assert is_prime(-7) is False


def test_primes():
    assert is_prime(2) is True
    assert is_prime(97) is True


def test_composites():
    assert is_prime(15) is False
''',
    '''def is_prime(n):
    """判断 n 是否为素数。"""
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True
''',
)

# ---------------------------------------------------------------- dbg013
_add(
    "dbg013", "dropped_tail",
    "chunk_list(lst, k) 把列表按每 k 个一组切分；最后不足 k 个的尾部也必须保留。"
    "当前实现丢掉了尾部。请修复。",
    '''def chunk_list(lst, k):
    """按每 k 个一组切分列表，保留尾部不足一组的元素。"""
    return [lst[i:i + k] for i in range(0, len(lst) - k + 1, k)]
''',
    '''from solution import chunk_list


def test_tail_kept():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_exact():
    assert chunk_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_smaller_than_k():
    assert chunk_list([1], 3) == [[1]]
''',
    '''def chunk_list(lst, k):
    """按每 k 个一组切分列表，保留尾部不足一组的元素。"""
    return [lst[i:i + k] for i in range(0, len(lst), k)]
''',
)

# ---------------------------------------------------------------- dbg014
_add(
    "dbg014", "tie_breaking",
    "most_frequent(items) 返回出现次数最多的元素；当多个元素并列时，返回『最先出现』的那个。"
    "当前实现在并列时返回了错误的元素。请修复。",
    '''def most_frequent(items):
    """返回出现最多的元素；并列时返回最先出现的。"""
    counts = {}
    for x in items:
        counts[x] = counts.get(x, 0) + 1
    return max(sorted(counts), key=counts.get)
''',
    '''from solution import most_frequent


def test_tie_first_wins():
    # 2 与 1 均出现 2 次，但 2 先出现，应返回 2
    assert most_frequent([2, 2, 1, 1, 3]) == 2


def test_clear_winner():
    assert most_frequent(["a", "b", "a"]) == "a"
''',
    '''def most_frequent(items):
    """返回出现最多的元素；并列时返回最先出现的。"""
    counts = {}
    order = []
    for x in items:
        if x not in counts:
            order.append(x)
            counts[x] = 0
        counts[x] += 1
    return max(order, key=counts.get)
''',
)

# ---------------------------------------------------------------- dbg015
_add(
    "dbg015", "wrong_dimension",
    "transpose(matrix) 返回矩阵的转置（matrix 是 m 行 n 列，结果应为 n 行 m 列）。"
    "当前实现假设了矩阵是方阵。请修复。",
    '''def transpose(matrix):
    """返回矩阵转置。"""
    return [[matrix[i][j] for i in range(len(matrix))] for j in range(len(matrix))]
''',
    '''from solution import transpose


def test_rectangular():
    assert transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]]


def test_square():
    assert transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]]
''',
    '''def transpose(matrix):
    """返回矩阵转置。"""
    rows, cols = len(matrix), len(matrix[0])
    return [[matrix[i][j] for i in range(rows)] for j in range(cols)]
''',
)

# ---------------------------------------------------------------- dbg016
_add(
    "dbg016", "state_update",
    "valid_parens(s) 判断字符串中的括号 ()[]{} 是否配对闭合（其他字符忽略）。"
    "当前实现的栈操作有误。请修复。",
    '''def valid_parens(s):
    """判断括号是否合法配对。"""
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.append(stack.pop())
    return not stack
''',
    '''from solution import valid_parens


def test_simple_ok():
    assert valid_parens("()") is True
    assert valid_parens("([{}])") is True


def test_bad():
    assert valid_parens("([)]") is False
    assert valid_parens("(") is False


def test_ignore_others():
    assert valid_parens("a(b[c]{d})e") is True
''',
    '''def valid_parens(s):
    """判断括号是否合法配对。"""
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return not stack
''',
)

# ---------------------------------------------------------------- dbg017
_add(
    "dbg017", "wrong_divisor",
    "moving_average(values, window) 返回滑动平均序列：第 i 个输出是"
    "values[max(0, i-window+1) : i+1] 这段的算术平均（开头不足 window 个时按实际个数求平均）。"
    "当前实现在开头部分的除数用错了。请修复。",
    '''def moving_average(values, window):
    """滑动平均；开头不足 window 个时按实际元素个数求平均。"""
    out = []
    for i in range(len(values)):
        seg = values[max(0, i - window + 1): i + 1]
        out.append(sum(seg) / window)
    return out
''',
    '''from solution import moving_average


def test_head():
    assert moving_average([2, 4, 6], 2) == [2.0, 3.0, 5.0]


def test_window_larger():
    assert moving_average([1, 2, 3], 5) == [1.0, 1.5, 2.0]
''',
    '''def moving_average(values, window):
    """滑动平均；开头不足 window 个时按实际元素个数求平均。"""
    out = []
    for i in range(len(values)):
        seg = values[max(0, i - window + 1): i + 1]
        out.append(sum(seg) / len(seg))
    return out
''',
)

# ---------------------------------------------------------------- dbg018
_add(
    "dbg018", "shallow_merge",
    "deep_merge(a, b) 递归合并两个字典：嵌套字典要逐键合并，b 中的非字典值覆盖 a 的同名键。"
    "当前实现只做了浅合并。请修复。",
    '''def deep_merge(a, b):
    """递归合并字典，b 优先。"""
    result = dict(a)
    result.update(b)
    return result
''',
    '''from solution import deep_merge


def test_nested():
    a = {"x": {"p": 1, "q": 2}}
    b = {"x": {"q": 3}}
    assert deep_merge(a, b) == {"x": {"p": 1, "q": 3}}


def test_flat():
    assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
''',
    '''def deep_merge(a, b):
    """递归合并字典，b 优先。"""
    result = dict(a)
    for k, v in b.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result
''',
)

# ---------------------------------------------------------------- dbg019
_add(
    "dbg019", "off_by_one_decode",
    "run_length_decode(pairs) 将 (字符, 次数) 对列表解码为字符串，例如 "
    "[('a', 3), ('b', 2)] -> 'aaabb'。当前实现每段少输出一个字符。请修复。",
    '''def run_length_decode(pairs):
    """行程解码。"""
    out = []
    for ch, n in pairs:
        out.append(ch * (n - 1))
    return "".join(out)
''',
    '''from solution import run_length_decode


def test_basic():
    assert run_length_decode([("a", 3), ("b", 2)]) == "aaabb"


def test_single():
    assert run_length_decode([("x", 1)]) == "x"
    assert run_length_decode([]) == ""
''',
    '''def run_length_decode(pairs):
    """行程解码。"""
    out = []
    for ch, n in pairs:
        out.append(ch * n)
    return "".join(out)
''',
)

# ---------------------------------------------------------------- dbg020
_add(
    "dbg020", "recency_update",
    "LRUCache 实现最近最少使用缓存：put 超过容量时淘汰最久未使用的键；"
    "get 访问某个键后，该键应被视为最近使用。当前实现的 get 没有更新使用顺序。请修复。",
    '''class LRUCache:
    """最近最少使用缓存。"""

    def __init__(self, capacity):
        self.cap = capacity
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def put(self, key, value):
        self.data[key] = value
        if len(self.data) > self.cap:
            oldest = next(iter(self.data))
            del self.data[oldest]
''',
    '''from solution import LRUCache


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")          # a 变为最近使用
    c.put("c", 3)       # 应淘汰 b
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_basic_put_get():
    c = LRUCache(1)
    c.put("k", 10)
    assert c.get("k") == 10
''',
    '''class LRUCache:
    """最近最少使用缓存。"""

    def __init__(self, capacity):
        self.cap = capacity
        self.data = {}

    def get(self, key, default=None):
        if key not in self.data:
            return default
        self.data[key] = self.data.pop(key)
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.data.pop(key)
        self.data[key] = value
        if len(self.data) > self.cap:
            oldest = next(iter(self.data))
            del self.data[oldest]
''',
)


def dump_jsonl(path: str) -> None:
    import pathlib
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for t in TASKS:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    dump_jsonl("data/selfbuilt/tasks.jsonl")
    print(f"dumped {len(TASKS)} tasks -> data/selfbuilt/tasks.jsonl")
