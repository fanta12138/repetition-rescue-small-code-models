"""Self-built Debug dataset v5: shallow-lock task expansion (E5).

Design principles (from E4 evidence):
- Skip-loop cascade family (v2_11 style) and order/index-confusion family
  (v4_08 style) are the two proven SHALLOW lock families: the model gets
  stuck tweaking within the buggy family, but the correct fix (stack /
  hash map) is in-distribution and reachable after a switch-approach nudge.
- Deep-lock families (replace-order, regex lookbehind) are deliberately
  excluded: E4 showed nudges cannot break them.
- Screening (seed 0, repair_structured) selects the actually-locking tasks;
  the locked subset is frozen BEFORE intervention arms run (preregistered).
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


# ================================================================ A 族：跳读级联
# ---------------------------------------------------------------- v5_01
_add(
    "v5_01", "algorithm_logic",
    "remove_zero_sum_pairs(items) 处理仅含 0-9 数字的列表：反复删除相邻且和为 10 "
    "的两个元素，删除后可能产生新的这类相邻对，需继续删除，直到无法再删。"
    "返回最终列表。例如 [3,7] -> 删 3,7 得 []。请修复。",
    '''def remove_zero_sum_pairs(items):
    """反复删除相邻且和为10的数字对。"""
    result = []
    for i in range(len(items)):
        if i > 0 and items[i] + items[i - 1] == 10:
            continue
        result.append(items[i])
    return result
''',
    '''from solution import remove_zero_sum_pairs


def test_basic():
    assert remove_zero_sum_pairs([3, 7, 1, 2]) == [1, 2]


def test_no_pair():
    assert remove_zero_sum_pairs([1, 2, 3]) == [1, 2, 3]


def test_cascade():
    assert remove_zero_sum_pairs([1, 9, 2, 8]) == []


def test_cascade_two():
    assert remove_zero_sum_pairs([4, 6, 5, 5]) == []
''',
    '''def remove_zero_sum_pairs(items):
    """反复删除相邻且和为10的数字对。"""
    stack = []
    for x in items:
        if stack and stack[-1] + x == 10:
            stack.pop()
        else:
            stack.append(x)
    return stack
''',
    "跳读级联族（v2_11 同族，列表+数字对规则）。",
)

# ---------------------------------------------------------------- v5_02
_add(
    "v5_02", "algorithm_logic",
    "remove_pair_sum_k(items, k) 反复删除列表中相邻且和等于 k 的两个元素，"
    "删除后可能产生新的这类相邻对，需继续删除，直到无法再删。返回最终列表。"
    "例如 remove_pair_sum_k([1, 4, 2, 3], 5) -> 删 1,4 得 [2,3] -> 删 2,3 得 []。"
    "请修复。",
    '''def remove_pair_sum_k(items, k):
    """反复删除相邻且和为k的元素对。"""
    result = []
    for i in range(len(items)):
        if i > 0 and items[i] + items[i - 1] == k:
            continue
        result.append(items[i])
    return result
''',
    '''from solution import remove_pair_sum_k


def test_basic():
    assert remove_pair_sum_k([1, 4, 3], 5) == [3]


def test_no_pair():
    assert remove_pair_sum_k([1, 2, 3], 7) == [1, 2, 3]


def test_cascade():
    assert remove_pair_sum_k([1, 4, 2, 3], 5) == []


def test_cascade_two():
    assert remove_pair_sum_k([2, 3, 3, 2, 1, 4], 5) == []
''',
    '''def remove_pair_sum_k(items, k):
    """反复删除相邻且和为k的元素对。"""
    stack = []
    for x in items:
        if stack and stack[-1] + x == k:
            stack.pop()
        else:
            stack.append(x)
    return stack
''',
    "跳读级联族（带参数的和规则）。",
)

# ---------------------------------------------------------------- v5_03
_add(
    "v5_03", "algorithm_logic",
    "remove_diff1_pairs(s) 反复删除字符串中相邻且 ASCII 码相差恰好为 1 的两个字符"
    "（不分先后，如 'ab'、'ba'），删除后可能产生新的这类相邻对，需继续删除，"
    "直到无法再删。返回最终结果。例如 'ab' -> ''。请修复。",
    '''def remove_diff1_pairs(s):
    """反复删除相邻且ASCII码相差1的字符对。"""
    result = []
    for i in range(len(s)):
        if i > 0 and abs(ord(s[i]) - ord(s[i - 1])) == 1:
            continue
        result.append(s[i])
    return "".join(result)
''',
    '''from solution import remove_diff1_pairs


def test_basic():
    assert remove_diff1_pairs("abx") == "x"


def test_no_pair():
    assert remove_diff1_pairs("ace") == "ace"


def test_cascade():
    assert remove_diff1_pairs("abba") == ""


def test_cascade_two():
    assert remove_diff1_pairs("abcddcba") == ""
''',
    '''def remove_diff1_pairs(s):
    """反复删除相邻且ASCII码相差1的字符对。"""
    stack = []
    for ch in s:
        if stack and abs(ord(ch) - ord(stack[-1])) == 1:
            stack.pop()
        else:
            stack.append(ch)
    return "".join(stack)
''',
    "跳读级联族（ASCII 差 1 规则，大小写混合敏感）。",
)

# ---------------------------------------------------------------- v5_04
_add(
    "v5_04", "algorithm_logic",
    "remove_adjacent_pairs(tokens) 反复删除列表中相邻的两个相同元素，"
    "删除后可能产生新的相邻重复对，需继续删除，直到无法再删。返回最终列表。"
    "元素为小写字符串。例如 ['a','b','b','a'] -> []。请修复。",
    '''def remove_adjacent_pairs(tokens):
    """反复删除列表中相邻的重复对。"""
    result = []
    for i in range(len(tokens)):
        if i > 0 and tokens[i] == tokens[i - 1]:
            continue
        result.append(tokens[i])
    return result
''',
    '''from solution import remove_adjacent_pairs


def test_basic():
    assert remove_adjacent_pairs(["x", "y", "y"]) == ["x"]


def test_no_pairs():
    assert remove_adjacent_pairs(["a", "b", "c"]) == ["a", "b", "c"]


def test_cascade_full():
    assert remove_adjacent_pairs(["a", "b", "b", "a"]) == []


def test_cascade_mid():
    assert remove_adjacent_pairs(["p", "p", "q", "q", "r"]) == ["r"]
''',
    '''def remove_adjacent_pairs(tokens):
    """反复删除列表中相邻的重复对。"""
    stack = []
    for t in tokens:
        if stack and stack[-1] == t:
            stack.pop()
        else:
            stack.append(t)
    return stack
''',
    "跳读级联族（字符串列表相等规则，v4_04 的整数版筛选中单 seed 锁定，"
    "此版换元素类型与用例结构再验）。",
)

# ---------------------------------------------------------------- v5_05
_add(
    "v5_05", "algorithm_logic",
    "remove_nested_pairs(s) 反复删除字符串中相邻的配对括号（'()'、'[]'，"
    "必须左括号紧跟右括号），删除后可能产生新的相邻配对，需继续删除，"
    "直到无法再删。返回最终结果。例如 '(())' -> 删内层 '()' 得 '()' -> ''。"
    "请修复。",
    '''def remove_nested_pairs(s):
    """反复删除相邻的配对括号。"""
    result = []
    for i in range(len(s)):
        if i > 0 and s[i - 1:i + 1] in ("()", "[]"):
            continue
        result.append(s[i])
    return "".join(result)
''',
    '''from solution import remove_nested_pairs


def test_basic():
    assert remove_nested_pairs("a()b") == "ab"


def test_no_pair():
    assert remove_nested_pairs(")(") == ")("


def test_cascade():
    assert remove_nested_pairs("(())") == ""


def test_cascade_two():
    assert remove_nested_pairs("([])") == ""
''',
    '''def remove_nested_pairs(s):
    """反复删除相邻的配对括号。"""
    pairs = {"(": ")", "[": "]"}
    stack = []
    for ch in s:
        if stack and stack[-1] in pairs and pairs[stack[-1]] == ch:
            stack.pop()
        else:
            stack.append(ch)
    return "".join(stack)
''',
    "跳读级联族（括号配对规则；v4_12 三括号版被一次解掉，此版减为两种"
    "括号并改用嵌套主导用例）。",
)

# ---------------------------------------------------------------- v5_06
_add(
    "v5_06", "algorithm_logic",
    "remove_digit_twins(digits) 处理仅含 0-9 数字的字符串：反复删除相邻的两个"
    "相同数字，删除后可能产生新的相邻重复，需继续删除，直到无法再删。"
    "返回最终结果。例如 '1221' -> 删 '22' 得 '11' -> 删 '11' 得 ''。请修复。",
    '''def remove_digit_twins(digits):
    """反复删除相邻的重复数字对。"""
    result = []
    for i in range(len(digits)):
        if i > 0 and digits[i] == digits[i - 1]:
            continue
        result.append(digits[i])
    return "".join(result)
''',
    '''from solution import remove_digit_twins


def test_basic():
    assert remove_digit_twins("1123") == "23"


def test_no_pairs():
    assert remove_digit_twins("123") == "123"


def test_cascade_full():
    assert remove_digit_twins("1221") == ""


def test_cascade_three():
    assert remove_digit_twins("112233") == ""
''',
    '''def remove_digit_twins(digits):
    """反复删除相邻的重复数字对。"""
    stack = []
    for d in digits:
        if stack and stack[-1] == d:
            stack.pop()
        else:
            stack.append(d)
    return "".join(stack)
''',
    "跳读级联族（数字串相等规则，v2_11 的同构异表面变体，检验效应是否"
    "依赖具体表面形式）。",
)

# ================================================================ B 族：顺序/下标混淆
# ---------------------------------------------------------------- v5_07
_add(
    "v5_07", "algorithm_logic",
    "three_sum_closest(nums, target) 在 nums 中找出和恰好等于 target 的三个数，"
    "返回它们的下标 [i, j, k]（i<j<k）。保证有解；若存在多组解，返回右端下标 k "
    "最小的那组。请修复。",
    '''def three_sum_closest(nums, target):
    """返回和为target的三个下标。"""
    triples = sorted((v, i) for i, v in enumerate(nums))
    n = len(triples)
    for a in range(n - 2):
        lo, hi = a + 1, n - 1
        while lo < hi:
            s = triples[a][0] + triples[lo][0] + triples[hi][0]
            if s == target:
                idx = sorted([triples[a][1], triples[lo][1], triples[hi][1]])
                return idx
            if s < target:
                lo += 1
            else:
                hi -= 1
    return []
''',
    '''from solution import three_sum_closest


def test_basic():
    assert three_sum_closest([2, 7, 11, 15], 20) == [0, 1, 2]


def test_unsorted():
    assert three_sum_closest([3, 1, 4, 2], 9) == [0, 2, 3]


def test_multiple_triples():
    # 两组解：2+3+6（k=3）与 1+4+6（k=4）；应返回 k 最小的 [0, 1, 3]。
    assert three_sum_closest([2, 3, 1, 6, 4], 11) == [0, 1, 3]


def test_duplicates():
    assert three_sum_closest([1, 1, 2], 4) == [0, 1, 2]
''',
    '''def three_sum_closest(nums, target):
    """返回和为target的三个下标。"""
    seen = {}
    for i, v in enumerate(nums):
        seen.setdefault(v, i)
    for k in range(len(nums)):
        for j in range(k):
            need = target - nums[j] - nums[k]
            if need in seen and seen[need] < j:
                return [seen[need], j, k]
    return []
''',
    "顺序混淆族（v4_08 的三数版）：排序双指针收敛到 k 更大的解。",
)

# ---------------------------------------------------------------- v5_08
_add(
    "v5_08", "algorithm_logic",
    "max_profit(prices) 给定股票每日价格列表，只允许买卖各一次且必须先买后卖，"
    "返回最大利润；若无法获利则返回 0。请修复。",
    '''def max_profit(prices):
    """返回一次买卖的最大利润。"""
    best = 0
    for i in range(len(prices)):
        for j in range(len(prices)):
            best = max(best, prices[i] - prices[j])
    return best
''',
    '''from solution import max_profit


def test_basic():
    assert max_profit([7, 1, 5, 3, 6, 4]) == 5


def test_descending():
    assert max_profit([7, 6, 4, 3, 1]) == 0


def test_two_days():
    assert max_profit([2, 4]) == 2


def test_sell_before_buy():
    # 最高价在最低价之前，不能先卖后买。
    assert max_profit([5, 1, 3]) == 2
''',
    '''def max_profit(prices):
    """返回一次买卖的最大利润。"""
    best = 0
    low = prices[0]
    for p in prices[1:]:
        best = max(best, p - low)
        low = min(low, p)
    return best
''',
    "顺序混淆族：双层循环忽略 i<j 约束，模型倾向交换 i/j 而非引入前缀最小值，"
    "在同一族内打转。",
)

# ---------------------------------------------------------------- v5_09
_add(
    "v5_09", "algorithm_logic",
    "closest_pair_sum(nums, target) 返回 nums 中和与 target 最接近的两个数的下标 "
    "[i, j]（i<j）；若有多个同样接近的对，返回右端下标 j 最小的那对。请修复。",
    '''def closest_pair_sum(nums, target):
    """返回和最接近target的两个下标。"""
    pairs = sorted((v, i) for i, v in enumerate(nums))
    lo, hi = 0, len(pairs) - 1
    best = None
    while lo < hi:
        s = pairs[lo][0] + pairs[hi][0]
        if best is None or abs(s - target) < abs(best[0] - target):
            best = (s, pairs[lo][1], pairs[hi][1])
        if s < target:
            lo += 1
        elif s > target:
            hi -= 1
        else:
            break
    i, j = best[1], best[2]
    return [min(i, j), max(i, j)]
''',
    '''from solution import closest_pair_sum


def test_exact():
    assert closest_pair_sum([2, 7, 11], 9) == [0, 1]


def test_closest():
    assert closest_pair_sum([1, 4, 8], 10) == [0, 2]


def test_tie_smallest_j():
    # 4+6=10（j=2）与 2+8=10（j=3）同样精确，返回 j 小的 [1, 2]。
    assert closest_pair_sum([4, 6, 2, 8], 10) == [0, 1]


def test_negative():
    assert closest_pair_sum([-3, 5, 2], 3) == [0, 1]
''',
    '''def closest_pair_sum(nums, target):
    """返回和最接近target的两个下标。"""
    best = None
    for j in range(len(nums)):
        for i in range(j):
            s = nums[i] + nums[j]
            d = abs(s - target)
            if best is None or d < best[0]:
                best = (d, i, j)
    return [best[1], best[2]]
''',
    "顺序混淆族：排序双指针在并列时不满足最小 j 约束。",
)

# ---------------------------------------------------------------- v5_10
_add(
    "v5_10", "boundary_condition",
    "search_range(nums, target) 在非降序整数列表中找 target 第一次和最后一次"
    "出现的位置，返回 [first, last]；不存在则返回 [-1, -1]。请修复。",
    '''def search_range(nums, target):
    """返回target的首尾位置。"""
    lo, hi = 0, len(nums) - 1
    first = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] >= target:
            hi = mid - 1
        else:
            lo = mid + 1
    if lo < len(nums) and nums[lo] == target:
        first = lo
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] <= target:
            lo = mid + 1
        else:
            hi = mid - 1
    if first == -1:
        return [-1, -1]
    return [first, lo]
''',
    '''from solution import search_range


def test_basic():
    assert search_range([5, 7, 7, 8, 8, 10], 8) == [3, 4]


def test_absent():
    assert search_range([5, 7, 7, 8, 8, 10], 6) == [-1, -1]


def test_single():
    assert search_range([1], 1) == [0, 0]


def test_all_same():
    assert search_range([3, 3, 3], 3) == [0, 2]
''',
    '''def search_range(nums, target):
    """返回target的首尾位置。"""
    lo, hi = 0, len(nums) - 1
    first = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] >= target:
            hi = mid - 1
        else:
            lo = mid + 1
    if lo < len(nums) and nums[lo] == target:
        first = lo
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] <= target:
            lo = mid + 1
        else:
            hi = mid - 1
    if first == -1:
        return [-1, -1]
    return [first, lo - 1]
''',
    "边界混淆族：last 位置 off-by-one（返回 lo 而非 lo-1），模型常在两个二分"
    "的边界条件间来回微调。",
)

# ---------------------------------------------------------------- v5_11
_add(
    "v5_11", "algorithm_logic",
    "max_subarray(nums) 返回和最大的连续子数组的和，以及该子数组的起止下标 "
    "[i, j]（闭区间）。若有多个和相同的最大子数组，返回最短的那个；若仍并列，"
    "返回起点 i 最小的。nums 非空。请修复。",
    '''def max_subarray(nums):
    """返回最大子数组的和与起止下标。"""
    best = None
    for i in range(len(nums)):
        for j in range(i, len(nums)):
            s = sum(nums[i:j + 1])
            if best is None or s > best[0]:
                best = (s, i, j)
    return [best[0], best[1], best[2]]
''',
    '''from solution import max_subarray


def test_basic():
    assert max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == [6, 3, 6]


def test_all_negative():
    assert max_subarray([-3, -1, -2]) == [-1, 1, 1]


def test_shortest_tie():
    # 和=3 的子数组有 [1,2,-3,3]（起点0，长度4）与 [3]（起点3，长度1），
    # 按规则取最短的 [3]。
    assert max_subarray([1, 2, -3, 3]) == [3, 3, 3]


def test_single():
    assert max_subarray([5]) == [5, 0, 0]
''',
    '''def max_subarray(nums):
    """返回最大子数组的和与起止下标。"""
    best = None
    for i in range(len(nums)):
        for j in range(i, len(nums)):
            s = sum(nums[i:j + 1])
            key = (-s, j - i, i)
            if best is None or key < best[0]:
                best = (key, s, i, j)
    return [best[1], best[2], best[3]]
''',
    "并列规则混淆族：buggy 用'先到先赢'代替'最短优先'，模型倾向在比较条件上"
    "打转而非重写并列键。",
)

# ---------------------------------------------------------------- v5_12
_add(
    "v5_12", "algorithm_logic",
    "pivot_index(nums) 返回列表的平衡点下标 i：左侧元素之和等于右侧元素之和"
    "（不含 nums[i] 本身）；不存在则返回 -1。若有多个平衡点，返回最小的下标。"
    "空的一侧和为 0。请修复。",
    '''def pivot_index(nums):
    """返回平衡点下标。"""
    for i in range(len(nums)):
        left = sum(nums[:i])
        right = sum(nums[i:])
        if left == right:
            return i
    return -1
''',
    '''from solution import pivot_index


def test_basic():
    assert pivot_index([1, 7, 3, 6, 5, 6]) == 3


def test_first():
    assert pivot_index([2, 1, -1]) == 0


def test_absent():
    assert pivot_index([1, 2, 3]) == -1


def test_right_excludes_self():
    # 右侧不应包含 nums[i] 自身。
    assert pivot_index([0, 0, 0]) == 0
''',
    '''def pivot_index(nums):
    """返回平衡点下标。"""
    total = sum(nums)
    left = 0
    for i, v in enumerate(nums):
        if left == total - left - v:
            return i
        left += v
    return -1
''',
    "切片边界混淆族：右侧切片包含自身（nums[i:] 而非 nums[i+1:]），模型常在"
    "两个切片的 +1/-1 上打转。",
)

# ---------------------------------------------------------------- v5_13
_add(
    "v5_13", "algorithm_logic",
    "min_rotated(nums) 返回旋转排序列表（无重复元素）中的最小值。"
    "例如 [4,5,6,7,0,1,2] 是 [0,1,2,4,5,6,7] 旋转而来，最小值为 0；"
    "未旋转的列表直接返回首元素。请修复。",
    '''def min_rotated(nums):
    """返回旋转排序列表的最小值。"""
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid
        else:
            hi = mid
    return nums[lo]
''',
    '''from solution import min_rotated


def test_rotated():
    assert min_rotated([4, 5, 6, 7, 0, 1, 2]) == 0


def test_unrotated():
    assert min_rotated([1, 2, 3, 4]) == 1


def test_two():
    assert min_rotated([2, 1]) == 1


def test_pivot_end():
    assert min_rotated([3, 4, 5, 1, 2]) == 1
''',
    '''def min_rotated(nums):
    """返回旋转排序列表的最小值。"""
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1
        else:
            hi = mid
    return nums[lo]
''',
    "边界混淆族：lo=mid 差一导致死循环/错位，模型在 mid±1 间打转。",
)

# ---------------------------------------------------------------- v5_14
_add(
    "v5_14", "algorithm_logic",
    "longest_mountain(nums) 返回列表中最长'山峰'子数组的长度：山峰定义为长度"
    "至少 3 的子数组，存在顶点下标 k（不在两端）使左侧严格递增、右侧严格递减。"
    "不存在山峰则返回 0。请修复。",
    '''def longest_mountain(nums):
    """返回最长山峰子数组的长度。"""
    best = 0
    for i in range(1, len(nums) - 1):
        if nums[i - 1] < nums[i] > nums[i + 1]:
            left = i
            while left > 0 and nums[left - 1] < nums[left]:
                left -= 1
            right = i
            while right < len(nums) - 1 and nums[right] > nums[right + 1]:
                right += 1
            best = max(best, right - left)
    return best
''',
    '''from solution import longest_mountain


def test_basic():
    assert longest_mountain([2, 1, 4, 7, 3, 2, 5]) == 5


def test_no_mountain():
    assert longest_mountain([2, 2, 2]) == 0


def test_two_mountains():
    assert longest_mountain([1, 3, 1, 4, 5, 2, 1]) == 5


def test_short():
    assert longest_mountain([1, 2]) == 0
''',
    '''def longest_mountain(nums):
    """返回最长山峰子数组的长度。"""
    best = 0
    for i in range(1, len(nums) - 1):
        if nums[i - 1] < nums[i] > nums[i + 1]:
            left = i
            while left > 0 and nums[left - 1] < nums[left]:
                left -= 1
            right = i
            while right < len(nums) - 1 and nums[right] > nums[right + 1]:
                right += 1
            best = max(best, right - left + 1)
    return best
''',
    "边界混淆族：长度 off-by-one（right-left 应为 right-left+1）。",
)
