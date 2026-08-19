"""Self-built Debug dataset v4: STICKINESS-INDUCING tasks (E4).

Design principles (E4 expansion of the E3 lock-breaking signal):
- Each task contains a bug where the *tempting local tweak* keeps failing a
  visible edge-case test, inviting the model to iterate within the same
  solution family (repetition lock-in). The gold fix is structurally
  different (stack / hash map / recursion / state machine / ...).
- Same single-file schema as v1/v2: buggy_code must FAIL, fixed_code PASS.
- `note` is internal metadata, never fed to the model.

Screening step (preregistration prerequisite): only tasks that actually
induce lock-in under repair_structured (repetition_events >= 2) enter the
frozen E4 locked subset.
"""
from __future__ import annotations

TASKS: list[dict] = []


def _add(task_id, bug_type, description, buggy_code, test_code, fixed_code, note=""):
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


# ---------------------------------------------------------------- v4_01
_add(
    "v4_01", "algorithm_logic",
    "remove_adjacent_pairs(s) 反复删除字符串中相邻的两个相同字符，"
    "删除后可能产生新的相邻重复对，需继续删除，直到无法再删。返回最终结果。"
    "例如 'abba' -> 删 'bb' 得 'aa' -> 删 'aa' 得 ''。请修复。",
    '''def remove_adjacent_pairs(s):
    """反复删除相邻重复对。"""
    for pair in {c + c for c in s}:
        s = s.replace(pair, "")
    return s
''',
    '''from solution import remove_adjacent_pairs


def test_basic():
    assert remove_adjacent_pairs("abbaca") == "ca"


def test_no_pairs():
    assert remove_adjacent_pairs("abc") == "abc"


def test_cascade_full():
    assert remove_adjacent_pairs("abba") == ""


def test_cascade_order():
    # 删除顺序敏感：单轮 replace 无论什么顺序都会残留。
    assert remove_adjacent_pairs("abccba") == ""


def test_empty():
    assert remove_adjacent_pairs("") == ""
''',
    '''def remove_adjacent_pairs(s):
    """反复删除相邻重复对。"""
    stack = []
    for ch in s:
        if stack and stack[-1] == ch:
            stack.pop()
        else:
            stack.append(ch)
    return "".join(stack)
''',
    "replace 循环族修补陷阱（v2_11 同题不同 buggy 变体，正解同为栈），"
    "检验效应跨题/跨 buggy 变体泛化。",
)

# ---------------------------------------------------------------- v4_02
_add(
    "v4_02", "algorithm_logic",
    "remove_zero_sum_pairs(s) 处理仅含数字 0-9 的字符串：反复删除相邻且和为 10 "
    "的两个字符，删除后可能产生新的这类相邻对，需继续删除，直到无法再删。"
    "返回最终结果。例如 '37' -> 删 '37' 得 ''。请修复。",
    '''def remove_zero_sum_pairs(s):
    """反复删除相邻且和为10的数字对。"""
    for a in "0123456789":
        for b in "0123456789":
            if int(a) + int(b) == 10:
                s = s.replace(a + b, "")
    return s
''',
    '''from solution import remove_zero_sum_pairs


def test_basic():
    assert remove_zero_sum_pairs("3712") == "12"


def test_no_pair():
    assert remove_zero_sum_pairs("123") == "123"


def test_cascade():
    assert remove_zero_sum_pairs("1928") == ""


def test_cascade_order():
    # 删除顺序敏感：replace 逐对处理时，后产生的新对若属于已处理的
    # 字符对就会残留（如先删 '19' 后新产生的 '28'）。
    assert remove_zero_sum_pairs("2918") == ""
''',
    '''def remove_zero_sum_pairs(s):
    """反复删除相邻且和为10的数字对。"""
    stack = []
    for ch in s:
        if stack and int(stack[-1]) + int(ch) == 10:
            stack.pop()
        else:
            stack.append(ch)
    return "".join(stack)
''',
    "级联删除的另一规则变体：replace 族 buggy（筛选证据：单轮 replace 对"
    "部分用例碰巧自愈，模型倾向在替换顺序/轮次上打转）。",
)

# ---------------------------------------------------------------- v4_03
_add(
    "v4_03", "algorithm_logic",
    "is_balanced(s) 判断括号字符串是否合法：'()'、'[]'、'{}' 三种括号，"
    "必须正确配对且嵌套顺序正确。例如 '([])' 合法，'([)]' 不合法。请修复。",
    '''def is_balanced(s):
    """判断括号字符串是否合法。"""
    opens = s.count("(") + s.count("[") + s.count("{")
    closes = s.count(")") + s.count("]") + s.count("}")
    return opens == closes
''',
    '''from solution import is_balanced


def test_simple_ok():
    assert is_balanced("(())") is True


def test_mixed_ok():
    assert is_balanced("([]){}") is True


def test_wrong_order():
    assert is_balanced("([)]") is False


def test_closing_first():
    assert is_balanced(")(") is False


def test_empty():
    assert is_balanced("") is True
''',
    '''def is_balanced(s):
    """判断括号字符串是否合法。"""
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
''',
    "计数族修补（加条件/比大小）无法覆盖顺序用例，正解为栈。",
)

# ---------------------------------------------------------------- v4_04
_add(
    "v4_04", "algorithm_logic",
    "remove_adjacent_dup_pairs(items) 反复删除列表中相邻的两个相同元素，"
    "删除后可能产生新的相邻重复对，需继续删除，直到无法再删。返回最终列表。"
    "例如 [1,2,2,3] -> 删两个 2 得 [1,3]。请修复。",
    '''def remove_adjacent_dup_pairs(items):
    """反复删除列表中相邻的重复对。"""
    result = []
    for i in range(len(items)):
        if i > 0 and items[i] == items[i - 1]:
            continue
        result.append(items[i])
    return result
''',
    '''from solution import remove_adjacent_dup_pairs


def test_basic():
    assert remove_adjacent_dup_pairs([1, 2, 2, 3]) == [1, 3]


def test_no_pairs():
    assert remove_adjacent_dup_pairs([1, 2, 3]) == [1, 2, 3]


def test_cascade_full():
    assert remove_adjacent_dup_pairs([1, 2, 2, 1]) == []


def test_cascade_mid():
    assert remove_adjacent_dup_pairs([1, 1, 2, 2, 3]) == [3]
''',
    '''def remove_adjacent_dup_pairs(items):
    """反复删除列表中相邻的重复对。"""
    stack = []
    for x in items:
        if stack and stack[-1] == x:
            stack.pop()
        else:
            stack.append(x)
    return stack
''',
    "跳读循环族陷阱（v2_11 的列表版，元素类型不同），"
    "检验锁定效应跨数据类型的泛化。",
)

# ---------------------------------------------------------------- v4_05
_add(
    "v4_05", "boundary_condition",
    "merge_intervals(intervals) 合并所有重叠或首尾相接的区间，输入区间不一定有序。"
    "例如 [(1,3),(2,6),(8,10)] -> [(1,6),(8,10)]；(1,4) 与 (4,5) 应合并为 (1,5)。"
    "返回合并后的新区间列表（按起点升序）。请修复。",
    '''def merge_intervals(intervals):
    """合并重叠或相接的区间。"""
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(iv) for iv in merged]
''',
    '''from solution import merge_intervals


def test_basic():
    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_unsorted():
    assert merge_intervals([(8, 10), (1, 3), (2, 6)]) == [(1, 6), (8, 10)]


def test_unsorted_bridge():
    # 桥接区间排在后面：不排序会把 (1,4) 与 (6,7) 错误合并。
    assert merge_intervals([(6, 7), (1, 4), (2, 9)]) == [(1, 9)]


def test_touching():
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]


def test_single():
    assert merge_intervals([(1, 2)]) == [(1, 2)]
''',
    '''def merge_intervals(intervals):
    """合并重叠或相接的区间。"""
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(iv) for iv in merged]
''',
    "缺排序 bug：模型常修补比较条件而非补上 sorted()。",
)

# ---------------------------------------------------------------- v4_06
_add(
    "v4_06", "algorithm_logic",
    "flatten(nested) 把任意深度嵌套的列表展平为一维列表，保持元素顺序。"
    "例如 [1, [2, [3, 4]], 5] -> [1, 2, 3, 4, 5]。请修复。",
    '''def flatten(nested):
    """展平任意深度嵌套的列表。"""
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out
''',
    '''from solution import flatten


def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]


def test_one_level():
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def test_deep():
    assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]


def test_deeper():
    assert flatten([[1], [[2]], [[[3]]]]) == [1, 2, 3]
''',
    '''def flatten(nested):
    """展平任意深度嵌套的列表。"""
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out
''',
    "单层 extend 族修补（加第二层判断）打转，正解为递归。",
)

# ---------------------------------------------------------------- v4_07
_add(
    "v4_07", "algorithm_logic",
    "eval_rpn(tokens) 计算逆波兰表达式：tokens 为数字与运算符 '+','-','*','//' "
    "的列表，除法是整数除法。例如 ['4','13','5','/','+'] -> 4 + 13//5 = 6。请修复。",
    '''def eval_rpn(tokens):
    """计算逆波兰表达式。"""
    stack = []
    for t in tokens:
        if t in "+-*/":
            a, b = stack.pop(), stack.pop()
            if t == "+":
                stack.append(b + a)
            elif t == "-":
                stack.append(a - b)
            elif t == "*":
                stack.append(b * a)
            else:
                stack.append(a // b)
        else:
            stack.append(int(t))
    return stack[-1]
''',
    '''from solution import eval_rpn


def test_add():
    assert eval_rpn(["2", "3", "+"]) == 5


def test_sub():
    assert eval_rpn(["10", "3", "-"]) == 7


def test_div():
    assert eval_rpn(["4", "13", "5", "/", "+"]) == 6


def test_complex():
    assert eval_rpn(["2", "1", "+", "3", "*"]) == 9
''',
    '''def eval_rpn(tokens):
    """计算逆波兰表达式。"""
    stack = []
    for t in tokens:
        if t in "+-*/":
            a, b = stack.pop(), stack.pop()
            if t == "+":
                stack.append(b + a)
            elif t == "-":
                stack.append(b - a)
            elif t == "*":
                stack.append(b * a)
            else:
                stack.append(b // a)
        else:
            stack.append(int(t))
    return stack[-1]
''',
    "操作数顺序 bug：模型常在 a-b / b-a 间来回翻转（E3 式打转）。",
)

# ---------------------------------------------------------------- v4_08
_add(
    "v4_08", "algorithm_logic",
    "two_sum(nums, target) 返回 nums 中和为 target 的两个数的下标 [i, j]（i<j）。"
    "不能重复使用同一元素；若存在多对可行解，返回右端下标 j 最小的那对。请修复。",
    '''def two_sum(nums, target):
    """返回和为 target 的两个下标。"""
    pairs = sorted((v, i) for i, v in enumerate(nums))
    lo, hi = 0, len(pairs) - 1
    while lo < hi:
        s = pairs[lo][0] + pairs[hi][0]
        if s == target:
            i, j = pairs[lo][1], pairs[hi][1]
            return [min(i, j), max(i, j)]
        if s < target:
            lo += 1
        else:
            hi -= 1
    return []
''',
    '''from solution import two_sum


def test_basic():
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]


def test_middle():
    assert two_sum([3, 2, 4], 6) == [1, 2]


def test_unsorted_indices():
    assert two_sum([1, 5, 3, 7], 10) == [2, 3]


def test_multiple_pairs():
    # 存在多对可行解（8+2 与 3+7），排序双指针收敛到错误的一对。
    assert two_sum([8, 1, 3, 7, 2], 10) == [2, 3]


def test_duplicates():
    assert two_sum([3, 3], 6) == [0, 1]
''',
    '''def two_sum(nums, target):
    """返回和为 target 的两个下标。"""
    seen = {}
    for i, v in enumerate(nums):
        if target - v in seen:
            return [seen[target - v], i]
        seen[v] = i
    return []
''',
    "排序双指针丢失原始下标/顺序：局部修补排序细节无解，正解为哈希。",
)

# ---------------------------------------------------------------- v4_09
_add(
    "v4_09", "stability",
    "stable_dedup(items) 去除列表中的重复元素，保留每个元素第一次出现的位置，"
    "其余重复全部删除（不要求重复元素相邻）。例如 [1,2,1,3,2] -> [1,2,3]。请修复。",
    '''def stable_dedup(items):
    """去重并保留首次出现顺序。"""
    out = []
    for i, x in enumerate(items):
        if i > 0 and x == items[i - 1]:
            continue
        out.append(x)
    return out
''',
    '''from solution import stable_dedup


def test_adjacent():
    assert stable_dedup([1, 1, 2, 2, 3]) == [1, 2, 3]


def test_scattered():
    assert stable_dedup([1, 2, 1, 3, 2]) == [1, 2, 3]


def test_all_same():
    assert stable_dedup([5, 5, 5]) == [5]


def test_strings():
    assert stable_dedup(["a", "b", "a"]) == ["a", "b"]
''',
    '''def stable_dedup(items):
    """去重并保留首次出现顺序。"""
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
''',
    "相邻比较族修补陷阱，正解为集合记录。",
)

# ---------------------------------------------------------------- v4_10
_add(
    "v4_10", "algorithm_logic",
    "LRUCache(capacity) 实现最近最少使用缓存：get(key) 命中返回值并刷新使用记录，"
    "未命中返回 -1；put(key, value) 写入并在超容量时淘汰最久未使用的键。请修复。",
    '''class LRUCache:
    """最近最少使用缓存。"""

    def __init__(self, capacity):
        self.capacity = capacity
        self.data = {}
        self.order = []

    def get(self, key):
        return self.data.get(key, -1)

    def put(self, key, value):
        if key in self.data:
            self.order.remove(key)
        elif len(self.data) >= self.capacity:
            old = self.order.pop(0)
            del self.data[old]
        self.data[key] = value
        self.order.append(key)
''',
    '''from solution import LRUCache


def test_basic():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == 1


def test_eviction():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.get(1)
    c.put(3, 3)
    assert c.get(2) == -1
    assert c.get(1) == 1
    assert c.get(3) == 3


def test_update_existing():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(1, 10)
    assert c.get(1) == 10
''',
    '''class LRUCache:
    """最近最少使用缓存。"""

    def __init__(self, capacity):
        self.capacity = capacity
        self.data = {}
        self.order = []

    def get(self, key):
        if key not in self.data:
            return -1
        self.order.remove(key)
        self.order.append(key)
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.order.remove(key)
        elif len(self.data) >= self.capacity:
            old = self.order.pop(0)
            del self.data[old]
        self.data[key] = value
        self.order.append(key)
''',
    "get 不刷新使用记录：模型常在淘汰条件上打转而非修 get。",
)

# ---------------------------------------------------------------- v4_11
_add(
    "v4_11", "string_parsing",
    "parse_line(line) 解析一行 CSV：字段以逗号分隔，但双引号包裹的字段内部"
    "可以包含逗号（本题数据不含转义引号）。返回字段列表。"
    "例如 'a,\"b,c\",d' -> ['a', 'b,c', 'd']。请修复。",
    '''def parse_line(line):
    """解析一行 CSV，支持引号内逗号。"""
    return line.split(",")
''',
    '''from solution import parse_line


def test_plain():
    assert parse_line("a,b,c") == ["a", "b", "c"]


def test_quoted():
    assert parse_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_quoted_two():
    assert parse_line('"x,y","1,2"') == ["x,y", "1,2"]


def test_single():
    assert parse_line("only") == ["only"]
''',
    '''def parse_line(line):
    """解析一行 CSV，支持引号内逗号。"""
    fields = []
    cur = []
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            fields.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    fields.append("".join(cur))
    return fields
''',
    "v3_07 的单文件变体：正则族深锁定候选，检验 nudge 对深锁定的边界。",
)

# ---------------------------------------------------------------- v4_12
_add(
    "v4_12", "algorithm_logic",
    "remove_bracket_pairs(s) 反复删除字符串中相邻的配对括号（'()'、'[]'、'{}'，"
    "必须是左括号紧跟右括号），删除后可能产生新的相邻配对，需继续删除，"
    "直到无法再删。返回最终结果。例如 '([])' -> 删 '[]' 得 '()' -> 删 '()' 得 ''。"
    "请修复。",
    '''def remove_bracket_pairs(s):
    """反复删除相邻的配对括号。"""
    pairs = ("()", "[]", "{}")
    result = []
    for i in range(len(s)):
        if i > 0 and s[i - 1:i + 1] in pairs:
            continue
        result.append(s[i])
    return "".join(result)
''',
    '''from solution import remove_bracket_pairs


def test_basic():
    assert remove_bracket_pairs("a()b") == "ab"


def test_no_pair():
    assert remove_bracket_pairs(")(") == ")("


def test_cascade():
    assert remove_bracket_pairs("([])") == ""


def test_cascade_two():
    assert remove_bracket_pairs("([]){}") == ""
''',
    '''def remove_bracket_pairs(s):
    """反复删除相邻的配对括号。"""
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = []
    for ch in s:
        if stack and stack[-1] in pairs and pairs[stack[-1]] == ch:
            stack.pop()
        else:
            stack.append(ch)
    return "".join(stack)
''',
    "跳读循环族陷阱（与 v2_11 同族不同题，配对规则更复杂），"
    "检验锁定效应在同族 buggy 上的可重复性。",
)
