"""Self-built Debug dataset v2 (harder): designed to break the ceiling effect.

Design principles (vs. v1, where direct mode hit 100%):
- Longer bodies and stateful logic (classes, iterators, streaming).
- Semantic / boundary bugs where the naive fix is wrong: off-by-one windows,
  floating-point ties, order stability, dead loops, mutable default state.
- Every task is machine-verified by scripts/verify_tasks.py:
  buggy_code MUST fail, fixed_code MUST pass.
- `note` is internal metadata (bug class, trap description). It is NEVER
  shown to the model; the model only sees description + buggy code + tests.
"""
from __future__ import annotations

TASKS: list[dict] = []


def _add(
    task_id: str,
    bug_type: str,
    description: str,
    buggy_code: str,
    test_code: str,
    fixed_code: str,
    note: str = "",
) -> None:
    TASKS.append(
        {
            "task_id": task_id,
            "bug_type": bug_type,
            "description": description,
            "buggy_code": buggy_code,
            "test_code": test_code,
            "fixed_code": fixed_code,
            "note": note,
        }
    )


# ---------------------------------------------------------------- v2_01
_add(
    "v2_01", "unsorted_assumption",
    "median(nums) 返回数值列表的中位数：奇数个取排序后的中间值，偶数个取"
    "中间两数的平均值。当前实现在某些输入上结果错误。请修复。",
    '''def median(nums):
    """返回列表中位数（不修改原列表）。"""
    a = list(nums)
    n = len(a)
    mid = n // 2
    if n % 2 == 1:
        return float(a[mid])
    return (a[mid - 1] + a[mid]) / 2
''',
    '''from solution import median


def test_odd():
    assert median([7, 1, 3]) == 3.0


def test_even():
    assert median([4, 1, 3, 2]) == 2.5


def test_unsorted_longer():
    assert median([9, 2, 5, 1, 8, 3]) == 4.0


def test_single():
    assert median([5]) == 5.0
''',
    '''def median(nums):
    """返回列表中位数（不修改原列表）。"""
    a = sorted(nums)
    n = len(a)
    mid = n // 2
    if n % 2 == 1:
        return float(a[mid])
    return (a[mid - 1] + a[mid]) / 2
''',
    note="忘记排序；直接模式下模型可能只补边界不改排序",
)


# ---------------------------------------------------------------- v2_02
_add(
    "v2_02", "boundary_condition",
    "merge_intervals(intervals) 合并所有重叠或相邻的闭区间，返回按起点升序、"
    "互不重叠的区间列表。一个区间完全包含另一个时也必须正确合并。请修复。",
    '''def merge_intervals(intervals):
    """合并重叠/相邻区间。"""
    if not intervals:
        return []
    ivs = sorted(intervals, key=lambda x: x[0])
    merged = [list(ivs[0])]
    for start, end in ivs[1:]:
        if start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''',
    '''from solution import merge_intervals


def test_basic_overlap():
    assert merge_intervals([[1, 3], [2, 6], [8, 10]]) == [[1, 6], [8, 10]]


def test_contained():
    assert merge_intervals([[1, 10], [2, 3]]) == [[1, 10]]


def test_adjacent():
    assert merge_intervals([[1, 2], [2, 3]]) == [[1, 3]]


def test_disjoint():
    assert merge_intervals([[1, 2], [4, 5]]) == [[1, 2], [4, 5]]
''',
    '''def merge_intervals(intervals):
    """合并重叠/相邻区间。"""
    if not intervals:
        return []
    ivs = sorted(intervals, key=lambda x: x[0])
    merged = [list(ivs[0])]
    for start, end in ivs[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''',
    note="严格小于漏掉 start == end 的相邻/相接情形",
)


# ---------------------------------------------------------------- v2_03
_add(
    "v2_03", "infinite_loop",
    "last_le(sorted_vals, x) 在非降序列表中返回最后一个 <= x 的元素，"
    "若不存在则返回 None。当前实现在某些输入上会卡死（超时）。请修复。",
    '''def last_le(sorted_vals, x):
    """二分查找最后一个 <= x 的元素。"""
    lo, hi = 0, len(sorted_vals) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] <= x:
            ans = sorted_vals[mid]
            lo = mid
        else:
            hi = mid - 1
    return ans
''',
    '''import signal

from solution import last_le


def _with_timeout(fn, *args):
    def handler(signum, frame):
        raise TimeoutError("疑似死循环")

    old = signal.signal(signal.SIGALRM, handler)
    signal.alarm(3)
    try:
        return fn(*args)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def test_normal():
    assert _with_timeout(last_le, [1, 3, 5, 7], 4) == 3


def test_all_le():
    assert _with_timeout(last_le, [1, 2, 3], 10) == 3


def test_none_le():
    assert _with_timeout(last_le, [5, 6], 1) is None


def test_duplicates():
    assert _with_timeout(last_le, [1, 2, 2, 2, 9], 2) == 2


def test_empty():
    assert _with_timeout(last_le, [], 3) is None
''',
    '''def last_le(sorted_vals, x):
    """二分查找最后一个 <= x 的元素。"""
    lo, hi = 0, len(sorted_vals) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi + 1) // 2
        if sorted_vals[mid] <= x:
            ans = sorted_vals[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return ans
''',
    note="lo=mid 导致 hi=lo+1 时死循环；需要 lo=mid+1 配合上取整 mid",
)


# ---------------------------------------------------------------- v2_04
_add(
    "v2_04", "state_machine",
    "LRUCache 实现最近最少使用缓存：get 命中时返回该值并将其标记为最近使用"
    "（未命中返回 -1）；put 写入时若超容量则淘汰『最久未使用』的键。"
    "当前实现在 get 之后淘汰了错误的键。请修复。",
    '''from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.cap = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key not in self.data:
            return -1
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.data.move_to_end(key)
        self.data[key] = value
        if len(self.data) > self.cap:
            self.data.popitem(last=False)
''',
    '''from solution import LRUCache


def test_basic():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == 1
    c.put(3, 3)          # 此时最久未使用的是键 2
    assert c.get(2) == -1
    assert c.get(3) == 3


def test_update_existing():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(1, 10)         # 更新已有键不应淘汰任何键
    assert c.get(1) == 10
    assert c.get(2) == 2


def test_get_refreshes():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(2) == 2
    c.put(3, 3)          # get(2) 之后最久未使用的是键 1
    assert c.get(1) == -1
    assert c.get(2) == 2
''',
    '''from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.cap = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key not in self.data:
            return -1
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.data.move_to_end(key)
        self.data[key] = value
        if len(self.data) > self.cap:
            self.data.popitem(last=False)
''',
    note="get 未 move_to_end，LRU 顺序不更新",
)


# ---------------------------------------------------------------- v2_05
_add(
    "v2_05", "stability",
    "partition_stable(nums, pivot) 将列表分为两部分返回 (less, greater)："
    "less 包含所有 < pivot 的元素，greater 包含其余元素；两部分都必须保持"
    "原列表中的相对顺序。请修复。",
    '''def partition_stable(nums, pivot):
    """稳定划分：返回 (less, greater)，均保持相对顺序。"""
    less, greater = [], []
    for x in nums:
        if x < pivot:
            less.append(x)
        else:
            greater.append(x)
    return less[::-1], greater
''',
    '''from solution import partition_stable


def test_basic():
    assert partition_stable([3, 1, 4, 1, 5], 3) == ([1, 1], [3, 4, 5])


def test_order_preserved():
    assert partition_stable([7, 2, 9, 3, 8], 5) == ([2, 3], [7, 9, 8])


def test_all_less():
    assert partition_stable([1, 2], 10) == ([1, 2], [])


def test_empty():
    assert partition_stable([], 0) == ([], [])
''',
    '''def partition_stable(nums, pivot):
    """稳定划分：返回 (less, greater)，均保持相对顺序。"""
    less, greater = [], []
    for x in nums:
        if x < pivot:
            less.append(x)
        else:
            greater.append(x)
    return less, greater
''',
    note="对 less 做了多余反转破坏稳定性",
)


# ---------------------------------------------------------------- v2_06
_add(
    "v2_06", "boundary_condition",
    "RateLimiter 判断请求是否被允许：最近 window 秒（含端点）内最多允许 "
    "max_calls 次调用；允许则记录本次时间戳并返回 True，否则返回 False。"
    "时间戳以非降序传入。当前实现在窗口边界处判断错误。请修复。",
    '''class RateLimiter:
    def __init__(self, max_calls, window):
        self.max_calls = max_calls
        self.window = window
        self.calls = []

    def allow(self, t):
        self.calls = [c for c in self.calls if t - c < self.window]
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(t)
        return True
''',
    '''from solution import RateLimiter


def test_within_limit():
    r = RateLimiter(2, 10)
    assert r.allow(1) is True
    assert r.allow(5) is True


def test_exact_boundary():
    r = RateLimiter(2, 10)
    r.allow(1)
    r.allow(5)
    # t=11 时，t=1 的调用恰好在 10 秒窗口的端点上，仍计入 -> 拒绝
    assert r.allow(11) is False
    # t=12 时，t=1 已滑出窗口（12-1=11>10）-> 允许
    assert r.allow(12) is True


def test_after_window():
    r = RateLimiter(1, 5)
    assert r.allow(0) is True
    assert r.allow(4) is False
    assert r.allow(6) is True
''',
    '''class RateLimiter:
    def __init__(self, max_calls, window):
        self.max_calls = max_calls
        self.window = window
        self.calls = []

    def allow(self, t):
        self.calls = [c for c in self.calls if t - c <= self.window]
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(t)
        return True
''',
    note="窗口端点含等号：t-c < window 写成 <= 才符合『含端点』规范",
)


# ---------------------------------------------------------------- v2_07
_add(
    "v2_07", "string_parsing",
    "natural_sort_key(s) 生成自然排序键，使 'file2' 排在 'file10' 之前："
    "字符串按连续的数字段/非数字段切分，数字段按数值比较。请修复。",
    '''import re


def natural_sort_key(s):
    """自然排序键。"""
    parts = re.split(r"(\\d+)", s)
    key = []
    for p in parts:
        if p.isdigit():
            key.append(p)
        else:
            key.append(p)
    return key
''',
    '''from solution import natural_sort_key


def test_file_names():
    names = ["file10", "file2", "file1"]
    assert sorted(names, key=natural_sort_key) == ["file1", "file2", "file10"]


def test_mixed():
    names = ["img12.png", "img2.png", "img3.png"]
    assert sorted(names, key=natural_sort_key) == ["img2.png", "img3.png", "img12.png"]


def test_multi_digit_blocks():
    names = ["a10b2", "a2b10", "a10b10"]
    assert sorted(names, key=natural_sort_key) == ["a2b10", "a10b2", "a10b10"]
''',
    '''import re


def natural_sort_key(s):
    """自然排序键。"""
    parts = re.split(r"(\\d+)", s)
    key = []
    for p in parts:
        if p.isdigit():
            key.append(int(p))
        else:
            key.append(p)
    return key
''',
    note="数字段未转 int，按字符串比较导致 file10 < file2",
)


# ---------------------------------------------------------------- v2_08
_add(
    "v2_08", "off_by_one",
    "max_subarray_sum_k(nums, k) 返回长度为 k 的连续子数组的最大元素和。"
    "假设 len(nums) >= k >= 1。当前实现在多数输入上结果错误。请修复。",
    '''def max_subarray_sum_k(nums, k):
    """定长 k 滑动窗口最大和。"""
    cur = sum(nums[:k])
    best = cur
    for i in range(k, len(nums)):
        cur += nums[i] - nums[i - 1]
        best = max(best, cur)
    return best
''',
    '''from solution import max_subarray_sum_k


def test_basic():
    assert max_subarray_sum_k([10, 1, 1, 1, 10], 2) == 11


def test_negative():
    assert max_subarray_sum_k([-1, -2, -3, -4], 2) == -3


def test_k_equals_len():
    assert max_subarray_sum_k([5, 6, 7], 3) == 18


def test_k_one():
    assert max_subarray_sum_k([3, 9, 1], 1) == 9
''',
    '''def max_subarray_sum_k(nums, k):
    """定长 k 滑动窗口最大和。"""
    cur = sum(nums[:k])
    best = cur
    for i in range(k, len(nums)):
        cur += nums[i] - nums[i - k]
        best = max(best, cur)
    return best
''',
    note="滑出窗口的元素应是 nums[i-k]，写成 nums[i-1]",
)


# ---------------------------------------------------------------- v2_09
_add(
    "v2_09", "state_machine",
    "parse_csv_line(line) 解析单行 CSV：逗号分隔字段；双引号包裹的字段内"
    "逗号是字面内容；字段内的两个连续双引号 \"\" 表示一个字面双引号。"
    "返回字段列表。当前实现解析结果错误。请修复。",
    '''def parse_csv_line(line):
    """解析单行 CSV。"""
    fields = []
    cur = []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                cur.append('"')
                i += 1
            # 普通引号：进入/退出引用状态
        elif ch == ',' and not in_quotes:
            fields.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    fields.append("".join(cur))
    return fields
''',
    '''from solution import parse_csv_line


def test_plain():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_quoted_comma():
    assert parse_csv_line('"a,b",c') == ["a,b", "c"]


def test_escaped_quote():
    assert parse_csv_line('"say ""hi""",ok') == ['say "hi"', "ok"]


def test_quoted_then_comma_inside():
    assert parse_csv_line('"x","y,z"') == ["x", "y,z"]
''',
    '''def parse_csv_line(line):
    """解析单行 CSV。"""
    fields = []
    cur = []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                cur.append('"')
                i += 1
            else:
                in_quotes = not in_quotes
        elif ch == ',' and not in_quotes:
            fields.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    fields.append("".join(cur))
    return fields
''',
    note="引号分支漏掉 in_quotes 翻转，状态机永远认为不在引用中",
)


# ---------------------------------------------------------------- v2_10
_add(
    "v2_10", "sentinel_value",
    "coin_change(coins, amount) 返回凑出 amount 所需的最少硬币数"
    "（每种硬币无限使用），无法凑出时返回 -1。请修复。",
    '''def coin_change(coins, amount):
    """最少硬币数，无法凑出返回 -1。"""
    dp = [amount] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for c in coins:
            if c <= i and dp[i - c] + 1 < dp[i]:
                dp[i] = dp[i - c] + 1
    return -1 if dp[amount] == amount else dp[amount]
''',
    '''from solution import coin_change


def test_normal():
    assert coin_change([1, 2, 5], 11) == 3


def test_impossible():
    assert coin_change([3], 10) == -1


def test_answer_equals_amount():
    # 真解恰好等于 amount（5 枚 1 元硬币），不得误判为无解
    assert coin_change([1], 5) == 5


def test_zero():
    assert coin_change([1], 0) == 0


def test_exact():
    assert coin_change([2, 5], 10) == 2
''',
    '''def coin_change(coins, amount):
    """最少硬币数，无法凑出返回 -1。"""
    INF = amount + 1
    dp = [INF] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for c in coins:
            if c <= i and dp[i - c] + 1 < dp[i]:
                dp[i] = dp[i - c] + 1
    return -1 if dp[amount] == INF else dp[amount]
''',
    note="哨兵取 amount 时无法区分『真解恰为 amount』与『无解』",
)


# ---------------------------------------------------------------- v2_11
_add(
    "v2_11", "algorithm_logic",
    "remove_adjacent_duplicates(s) 反复删除字符串中相邻的两个相同字符，"
    "删除后可能产生新的相邻重复，需继续删除，直到无法再删。返回最终结果。"
    "例如 'abbaca' -> 删 'bb' 得 'aaca' -> 删 'aa' 得 'ca'。请修复。",
    '''def remove_adjacent_duplicates(s):
    """反复删除相邻重复对。"""
    result = []
    for i in range(len(s)):
        if i > 0 and s[i] == s[i - 1]:
            continue
        result.append(s[i])
    return "".join(result)
''',
    '''from solution import remove_adjacent_duplicates


def test_example():
    assert remove_adjacent_duplicates("abbaca") == "ca"


def test_cascade():
    assert remove_adjacent_duplicates("abba") == ""


def test_no_dup():
    assert remove_adjacent_duplicates("abc") == "abc"


def test_long_cascade():
    assert remove_adjacent_duplicates("aabccba") == "a"
''',
    '''def remove_adjacent_duplicates(s):
    """反复删除相邻重复对。"""
    stack = []
    for ch in s:
        if stack and stack[-1] == ch:
            stack.pop()
        else:
            stack.append(ch)
    return "".join(stack)
''',
    note="只跳过原串相邻重复而非栈顶比较，级联删除全部失效",
)


# ---------------------------------------------------------------- v2_12
_add(
    "v2_12", "string_parsing",
    "compare_versions(v1, v2) 比较点分版本号：逐段按数值比较，"
    "v1 大返回 1，v2 大返回 -1，相等返回 0。段数不同时缺失段视为 0，"
    "如 '1.0' == '1'。请修复。",
    '''def compare_versions(v1, v2):
    """比较版本号，返回 1 / -1 / 0。"""
    p1 = v1.split(".")
    p2 = v2.split(".")
    for a, b in zip(p1, p2):
        if int(a) > int(b):
            return 1
        if int(a) < int(b):
            return -1
    return 0
''',
    '''from solution import compare_versions


def test_equal_values():
    assert compare_versions("1.01", "1.1") == 0


def test_longer_is_bigger():
    assert compare_versions("1.0.1", "1") == 1


def test_shorter_missing_zero():
    assert compare_versions("1", "1.0.0") == 0


def test_numeric_not_lex():
    assert compare_versions("1.10", "1.2") == 1


def test_simple_less():
    assert compare_versions("0.9", "1.0") == -1
''',
    '''def compare_versions(v1, v2):
    """比较版本号，返回 1 / -1 / 0。"""
    p1 = [int(x) for x in v1.split(".")]
    p2 = [int(x) for x in v2.split(".")]
    n = max(len(p1), len(p2))
    p1 += [0] * (n - len(p1))
    p2 += [0] * (n - len(p2))
    for a, b in zip(p1, p2):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0
''',
    note="zip 截断后直接 return 0，段数不同的版本比较错误",
)


# ---------------------------------------------------------------- v2_13
_add(
    "v2_13", "greedy_order",
    "min_meeting_rooms(intervals) 返回同时进行的最多会议数，即所需最少会议室"
    "数量。intervals 为 [start, end) 半开区间列表，顺序任意。请修复。",
    '''def min_meeting_rooms(intervals):
    """最少会议室数（扫描线）。"""
    if not intervals:
        return 0
    ivs = sorted(intervals, key=lambda x: x[1])
    rooms = 0
    cur = 0
    events = []
    for s, e in ivs:
        events.append((s, 1))
        events.append((e, -1))
    # 同一时刻先算开始再算结束
    events.sort(key=lambda ev: (ev[0], -ev[1]))
    for _, delta in events:
        cur += delta
        rooms = max(rooms, cur)
    return rooms
''',
    '''from solution import min_meeting_rooms


def test_overlap():
    assert min_meeting_rooms([[0, 30], [5, 10], [15, 20]]) == 2


def test_chain():
    assert min_meeting_rooms([[1, 5], [5, 9], [9, 12]]) == 1


def test_all_overlap():
    assert min_meeting_rooms([[1, 10], [2, 3], [2, 6]]) == 3


def test_empty():
    assert min_meeting_rooms([]) == 0
''',
    '''def min_meeting_rooms(intervals):
    """最少会议室数（扫描线）。"""
    if not intervals:
        return 0
    events = []
    for s, e in intervals:
        events.append((s, 1))
        events.append((e, -1))
    # 同一时刻先处理结束（-1 在 +1 前），保证半开区间衔接不算重叠
    events.sort(key=lambda x: (x[0], x[1]))
    rooms = 0
    cur = 0
    for _, delta in events:
        cur += delta
        rooms = max(rooms, cur)
    return rooms
''',
    note="同刻事件排序方向错（先开始后结束），半开衔接区间被误判重叠",
)


# ---------------------------------------------------------------- v2_14
_add(
    "v2_14", "algorithm_logic",
    "next_permutation(seq) 原地将列表变为字典序中的下一个排列并返回该列表；"
    "若已是最大排列，则变为最小排列（升序）。请修复。",
    '''def next_permutation(seq):
    """原地下一个字典序排列。"""
    n = len(seq)
    i = n - 2
    while i >= 0 and seq[i] >= seq[i + 1]:
        i -= 1
    if i >= 0:
        j = n - 1
        while seq[j] <= seq[i]:
            j -= 1
        seq[i], seq[j] = seq[j], seq[i]
    seq[i:] = reversed(seq[i:])
    return seq
''',
    '''from solution import next_permutation


def test_basic():
    assert next_permutation([1, 2, 3]) == [1, 3, 2]


def test_mid():
    assert next_permutation([1, 3, 2]) == [2, 1, 3]


def test_descending_wraps():
    assert next_permutation([3, 2, 1]) == [1, 2, 3]


def test_duplicates():
    assert next_permutation([1, 5, 1]) == [5, 1, 1]


def test_single():
    assert next_permutation([7]) == [7]
''',
    '''def next_permutation(seq):
    """原地下一个字典序排列。"""
    n = len(seq)
    i = n - 2
    while i >= 0 and seq[i] >= seq[i + 1]:
        i -= 1
    if i >= 0:
        j = n - 1
        while seq[j] <= seq[i]:
            j -= 1
        seq[i], seq[j] = seq[j], seq[i]
    seq[i + 1:] = seq[i + 1:][::-1]
    return seq
''',
    note="反转后缀的起点应是 i+1，写成 i 会把刚交换上去的元素又翻回去",
)


# ---------------------------------------------------------------- v2_15
_add(
    "v2_15", "boundary_condition",
    "job_schedule(jobs) 中 jobs 是 (start, end, profit) 元组列表，选择互不"
    "重叠的工作（前一个 end 严格小于后一个 start 才可衔接）使总利润最大，"
    "返回最大利润。请修复。",
    '''def job_schedule(jobs):
    """带权区间调度（DP + 二分）。"""
    if not jobs:
        return 0
    js = sorted(jobs, key=lambda x: x[1])
    n = len(js)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        start, end, profit = js[i - 1]
        lo, hi, compat = 0, i - 1, 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if js[mid][1] <= start:
                compat = mid + 1
                lo = mid + 1
            else:
                hi = mid - 1
        dp[i] = max(dp[i - 1], dp[compat] + profit)
    return dp[n]
''',
    '''from solution import job_schedule


def test_conflict_at_boundary():
    # (1,3) 与 (3,4) end==start，不允许衔接，只能选利润大的一个
    assert job_schedule([(1, 3, 5), (3, 4, 100)]) == 100


def test_chain_ok():
    assert job_schedule([(1, 2, 5), (3, 4, 10)]) == 15


def test_pick_best_combo():
    assert job_schedule([(1, 4, 30), (2, 5, 50), (5, 7, 20)]) == 50


def test_empty():
    assert job_schedule([]) == 0
''',
    '''def job_schedule(jobs):
    """带权区间调度（DP + 二分）。"""
    if not jobs:
        return 0
    js = sorted(jobs, key=lambda x: x[1])
    n = len(js)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        start, end, profit = js[i - 1]
        lo, hi, compat = 0, i - 1, 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if js[mid][1] < start:
                compat = mid + 1
                lo = mid + 1
            else:
                hi = mid - 1
        dp[i] = max(dp[i - 1], dp[compat] + profit)
    return dp[n]
''',
    note="衔接条件应为严格小于（end < start），<= 允许了非法衔接",
)


# ---------------------------------------------------------------- v2_16
_add(
    "v2_16", "floating_point",
    "round_half_even(x) 实现银行家舍入到整数：小数部分恰为 0.5 时取最近的"
    "偶数（2.5 -> 2，3.5 -> 4），其余情况四舍五入。请修复。",
    '''def round_half_even(x):
    """银行家舍入到整数。"""
    import math

    return math.floor(x + 0.5)
''',
    '''from solution import round_half_even


def test_tie_to_even_down():
    assert round_half_even(2.5) == 2


def test_tie_to_even_up():
    assert round_half_even(3.5) == 4


def test_tie_negative():
    assert round_half_even(-2.5) == -2


def test_normal_round():
    assert round_half_even(2.6) == 3
    assert round_half_even(2.4) == 2


def test_normal_negative():
    assert round_half_even(-2.6) == -3
''',
    '''def round_half_even(x):
    """银行家舍入到整数。"""
    import decimal

    return int(
        decimal.Decimal(str(x)).quantize(
            decimal.Decimal("1"), rounding=decimal.ROUND_HALF_EVEN
        )
    )
''',
    note="floor(x+0.5) 是 half-up 而非 half-even；需显式处理 0.5 平局",
)


# ---------------------------------------------------------------- v2_17
_add(
    "v2_17", "algorithm_logic",
    "merge_sort(nums) 用归并排序返回升序新列表（不修改输入）。"
    "当前实现排序结果错误。请修复。",
    '''def merge_sort(nums):
    """归并排序，返回新的升序列表。"""
    if len(nums) <= 1:
        return list(nums)
    mid = len(nums) // 2
    left = merge_sort(nums[:mid])
    right = merge_sort(nums[mid:])
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] > right[j]:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out
''',
    '''from solution import merge_sort


def test_basic():
    assert merge_sort([5, 3, 1, 4, 2]) == [1, 2, 3, 4, 5]


def test_duplicates():
    assert merge_sort([2, 1, 2, 1]) == [1, 1, 2, 2]


def test_negative():
    assert merge_sort([-1, -5, 3]) == [-5, -1, 3]


def test_input_untouched():
    src = [3, 1, 2]
    merge_sort(src)
    assert src == [3, 1, 2]
''',
    '''def merge_sort(nums):
    """归并排序，返回新的升序列表。"""
    if len(nums) <= 1:
        return list(nums)
    mid = len(nums) // 2
    left = merge_sort(nums[:mid])
    right = merge_sort(nums[mid:])
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out
''',
    note="归并比较方向反了（取大不取小），产出非升序结果",
)


# ---------------------------------------------------------------- v2_18
_add(
    "v2_18", "boundary_condition",
    "paginate(items, page, page_size) 返回第 page 页（从 1 开始）的元素列表，"
    "每页 page_size 个；页码从 1 起算，超出范围的页返回空列表。"
    "请修复。",
    '''def paginate(items, page, page_size):
    """返回第 page 页（从 1 开始）的分页结果。"""
    start = page * page_size
    return items[start : start + page_size]
''',
    '''from solution import paginate


def test_first_page():
    assert paginate([1, 2, 3, 4, 5], 1, 2) == [1, 2]


def test_second_page():
    assert paginate([1, 2, 3, 4, 5], 2, 2) == [3, 4]


def test_partial_last_page():
    assert paginate([1, 2, 3, 4, 5], 3, 2) == [5]


def test_out_of_range():
    assert paginate([1, 2, 3], 5, 2) == []


def test_empty():
    assert paginate([], 1, 10) == []
''',
    '''def paginate(items, page, page_size):
    """返回第 page 页（从 1 开始）的分页结果。"""
    start = (page - 1) * page_size
    return items[start : start + page_size]
''',
    note="页码从 1 起但偏移按 page*page_size 算，第一页整体错位",
)


# ---------------------------------------------------------------- v2_19
_add(
    "v2_19", "string_parsing",
    "parse_csv_multiline(text) 解析 CSV 文本，返回所有字段的扁平列表（按行"
    "优先顺序）：未被引号包裹的换行符是记录分隔符（字段结束并开始新记录）；"
    "双引号包裹的字段内部，逗号与换行符都是字面内容。当前实现在字段含"
    "换行时解析错误。请修复。",
    '''def parse_csv_multiline(text):
    """解析 CSV 文本；引号内换行属于字段内容，引号外换行分隔记录。"""
    fields = []
    cur = []
    in_quotes = False
    for ch in text:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            fields.append("".join(cur))
            cur = []
        elif ch == "\\n":
            # 换行无论是否在引号内都分隔记录
            fields.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    fields.append("".join(cur))
    return fields
''',
    '''from solution import parse_csv_multiline


def test_simple():
    assert parse_csv_multiline("a,b\\nc,d") == ["a", "b", "c", "d"]


def test_newline_in_quotes():
    assert parse_csv_multiline('a,"x\\ny",b') == ["a", "x\\ny", "b"]


def test_quoted_comma():
    assert parse_csv_multiline('"p,q",r') == ["p,q", "r"]


def test_multiple_lines():
    assert parse_csv_multiline('1,2\\n"3\\n4",5') == ["1", "2", "3\\n4", "5"]
''',
    '''def parse_csv_multiline(text):
    """解析 CSV 文本；引号内换行属于字段内容，引号外换行分隔记录。"""
    fields = []
    cur = []
    in_quotes = False
    for ch in text:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            fields.append("".join(cur))
            cur = []
        elif ch == "\\n" and not in_quotes:
            fields.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    fields.append("".join(cur))
    return fields
''',
    note="引号内换行被误当作记录分隔符；需检查 in_quotes 状态",
)


# ---------------------------------------------------------------- v2_20
_add(
    "v2_20", "algorithm_logic",
    "search_rotated(nums, target) 在无重复元素的旋转升序数组中查找 target，"
    "返回下标；不存在返回 -1。要求 O(log n)。请修复。",
    '''def search_rotated(nums, target):
    """旋转数组二分查找。"""
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid
    return -1
''',
    '''from solution import search_rotated


def test_in_sorted_part():
    assert search_rotated([4, 5, 6, 7, 0, 1, 2], 0) == 4


def test_in_rotated_part():
    assert search_rotated([4, 5, 6, 7, 0, 1, 2], 5) == 1


def test_not_found():
    assert search_rotated([4, 5, 6, 7, 0, 1, 2], 3) == -1


def test_two_elements():
    assert search_rotated([3, 1], 1) == 1
    assert search_rotated([3, 1], 3) == 0


def test_single():
    assert search_rotated([1], 1) == 0
    assert search_rotated([1], 0) == -1
''',
    '''def search_rotated(nums, target):
    """旋转数组二分查找。"""
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
''',
    note="lo=mid / hi=mid 单步不收缩，两个元素等场景死循环或漏判",
)
