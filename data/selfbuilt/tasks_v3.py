"""Self-built Debug dataset v3: MULTI-FILE tasks.

Design principles (direction 1):
- Each task is a tiny project of 2-3 files; EXACTLY ONE file contains the bug.
- The symptom appears in test output but does not name the buggy file,
  so the model must LOCALIZE (read + reason across files) before fixing.
- Feedback is deliberately non-pointing: assertion diffs show wrong final
  values, not which module produced them.
- bug_file is ground truth for the localization metric (never shown to model).
- `note` is internal metadata, never fed to the model.

Invariants enforced by scripts/verify_tasks.py --set v3:
    files (buggy) must FAIL the tests; files_fixed must PASS.
"""
from __future__ import annotations

TASKS: list[dict] = []


def _add(task_id, bug_file, bug_type, description, files, test_code, files_fixed, note):
    TASKS.append(
        {
            "task_id": task_id,
            "bug_file": bug_file,
            "bug_type": bug_type,
            "description": description,
            "files": files,
            "test_code": test_code,
            "files_fixed": files_fixed,
            "note": note,
        }
    )


# ---------------------------------------------------------------------------
# v3_01  pricing: utils.normalize_weight 归一化上限边界写错 -> service 档位错误
# ---------------------------------------------------------------------------
_v3_01_files = {
    "utils.py": '''def normalize_weight(value, limit):
    """把重量 value 归一化到 [0, limit] 区间。"""
    if value < 0:
        return 0
    if value >= limit:     # bug: 等于 limit 时被错误截断为 limit-1
        return limit - 1
    return value
''',
    "service.py": '''from utils import normalize_weight


def shipping_fee(weight, unit_price=2):
    """运费 = 归一化后的重量 * 单价；重量上限为 10。"""
    w = normalize_weight(weight, 10)
    return w * unit_price
''',
}
_v3_01_test = '''from service import shipping_fee


def test_below_limit():
    assert shipping_fee(3) == 6


def test_at_limit():
    assert shipping_fee(10) == 20


def test_over_limit():
    assert shipping_fee(15) == 20


def test_negative():
    assert shipping_fee(-2) == 0
'''
_v3_01_fixed = dict(_v3_01_files)
_v3_01_fixed["utils.py"] = '''def normalize_weight(value, limit):
    """把重量 value 归一化到 [0, limit] 区间。"""
    if value < 0:
        return 0
    if value > limit:
        return limit
    return value
'''
_add(
    "v3_01", "utils.py", "boundary_condition",
    "一个运费计算小项目：service.py 依赖 utils.py 的重量归一化。"
    "测试报告运费结果不对，请定位并修复 bug。",
    _v3_01_files, _v3_01_test, _v3_01_fixed,
    "buggy: >=limit 返回 limit-1 → fee(10)=18≠20、fee(15)=18≠20；"
    "症状在 shipping_fee 返回值，assert 不指认文件",
)


# ---------------------------------------------------------------------------
# v3_02  textstats: tokenize 不折叠多空格 -> 词数统计错误
# ---------------------------------------------------------------------------
_v3_02_files = {
    "textproc.py": '''def tokenize(text):
    """按空白切分文本为单词列表。"""
    return text.split(" ")      # bug: 连续空格会产生空字符串 token
''',
    "stats.py": '''from textproc import tokenize


def word_count(text):
    """统计单词数。"""
    return len(tokenize(text))


def avg_word_length(text):
    """平均单词长度（保留 2 位小数）；无单词时返回 0。"""
    words = tokenize(text)
    if not words:
        return 0
    return round(sum(len(w) for w in words) / len(words), 2)
''',
}
_v3_02_test = '''from stats import avg_word_length, word_count


def test_simple():
    assert word_count("hello world") == 2


def test_multiple_spaces():
    assert word_count("a   b  c") == 3


def test_leading_trailing():
    assert word_count("  hi  ") == 1


def test_avg_len():
    assert avg_word_length("ab  cdef") == 3.0
'''
_v3_02_fixed = dict(_v3_02_files)
_v3_02_fixed["textproc.py"] = '''def tokenize(text):
    """按空白切分文本为单词列表。"""
    return text.split()
'''
_add(
    "v3_02", "textproc.py", "string_parsing",
    "一个文本统计小项目：stats.py 依赖 textproc.py 的分词器。"
    "部分测试的词数与平均词长不对，请定位并修复 bug。",
    _v3_02_files, _v3_02_test, _v3_02_fixed,
    "split(' ') vs split()；平均词长测试里空 token 长度 0 也拉低均值，双重症状",
)


# ---------------------------------------------------------------------------
# v3_03  events: queue 的比较方向反了 -> 处理器拿到乱序结果
# ---------------------------------------------------------------------------
_v3_03_files = {
    "eventqueue.py": '''class EventQueue:
    """按时间戳从小到大出队的事件队列。"""

    def __init__(self):
        self._items = []

    def push(self, ts, payload):
        self._items.append((ts, payload))
        self._items.sort(key=lambda p: p[0], reverse=True)   # bug: 降序

    def pop(self):
        return self._items.pop(0) if self._items else None
''',
    "handler.py": '''from eventqueue import EventQueue


def process(events):
    """events: [(ts, payload), ...]；返回按处理顺序排列的 payload 列表。"""
    q = EventQueue()
    for ts, payload in events:
        q.push(ts, payload)
    out = []
    while True:
        item = q.pop()
        if item is None:
            break
        out.append(item[1])
    return out
''',
}
_v3_03_test = '''from handler import process


def test_sorted_input():
    assert process([(1, "a"), (2, "b"), (3, "c")]) == ["a", "b", "c"]


def test_unsorted_input():
    assert process([(3, "c"), (1, "a"), (2, "b")]) == ["a", "b", "c"]


def test_single():
    assert process([(5, "x")]) == ["x"]


def test_empty():
    assert process([]) == []
'''
_v3_03_fixed = dict(_v3_03_files)
_v3_03_fixed["eventqueue.py"] = '''class EventQueue:
    """按时间戳从小到大出队的事件队列。"""

    def __init__(self):
        self._items = []

    def push(self, ts, payload):
        self._items.append((ts, payload))
        self._items.sort(key=lambda p: p[0])

    def pop(self):
        return self._items.pop(0) if self._items else None
'''
_add(
    "v3_03", "eventqueue.py", "algorithm_logic",
    "一个事件处理小项目：handler.py 通过 eventqueue.py 的事件队列按时间顺序处理事件。"
    "处理顺序出错，请定位并修复 bug。",
    _v3_03_files, _v3_03_test, _v3_03_fixed,
    "症状是 payload 顺序错；队列实现细节在另一文件。注意 queue.py 与标准库同名但测试从本地导入",
)


# ---------------------------------------------------------------------------
# v3_04  pagination: 第二页起切片 off-by-one
# ---------------------------------------------------------------------------
_v3_04_files = {
    "pager.py": '''def paginate(items, page, size):
    """返回第 page 页（从 1 开始）的元素列表；越界返回空列表。"""
    if page < 1 or size < 1:
        return []
    start = (page - 1) * size
    end = start + page          # bug: 应为 start + size
    return items[start:end]
''',
    "api.py": '''from pager import paginate


def get_page(items, page, size):
    """对外接口：返回 (该页数据, 是否还有下一页)。"""
    data = paginate(items, page, size)
    has_next = len(items) > page * size
    return data, has_next
''',
}
_v3_04_test = '''from api import get_page
from pager import paginate


def test_first_page():
    assert paginate([1, 2, 3, 4, 5], 1, 2) == [1, 2]


def test_second_page():
    assert paginate([1, 2, 3, 4, 5], 2, 2) == [3, 4]


def test_last_partial():
    assert paginate([1, 2, 3, 4, 5], 3, 2) == [5]


def test_has_next():
    data, has_next = get_page([1, 2, 3, 4], 1, 2)
    assert data == [1, 2] and has_next is True


def test_no_next():
    data, has_next = get_page([1, 2], 1, 2)
    assert data == [1, 2] and has_next is False
'''
_v3_04_fixed = dict(_v3_04_files)
_v3_04_fixed["pager.py"] = '''def paginate(items, page, size):
    """返回第 page 页（从 1 开始）的元素列表；越界返回空列表。"""
    if page < 1 or size < 1:
        return []
    start = (page - 1) * size
    end = start + size
    return items[start:end]
'''
_add(
    "v3_04", "pager.py", "off_by_one",
    "一个分页小项目：api.py 依赖 pager.py 的切片逻辑。"
    "某些页返回的数据不对，请定位并修复 bug。",
    _v3_04_files, _v3_04_test, _v3_04_fixed,
    "第一页 page==1 时 start+page 恰好等于 start+size（当 size==1 才同）…实际 size=2 时第一页 end=0+1=1 也会挂；"
    "故测试里第一页 [1]!=[1,2] 直接挂 —— 保持：症状明显但根因在 pager",
)


# ---------------------------------------------------------------------------
# v3_05  cache: 键序列化不稳定（dict 无序拼接）
# ---------------------------------------------------------------------------
_v3_05_files = {
    "keygen.py": '''def make_key(params):
    """把参数字典序列化为缓存键。同一组参数必须总是得到同一个键。"""
    parts = [f"{k}={v}" for k, v in params.items()]   # bug: 未排序，顺序随插入变化
    return "&".join(parts)
''',
    "cache.py": '''from keygen import make_key


class SimpleCache:
    def __init__(self):
        self._store = {}

    def get(self, params, default=None):
        return self._store.get(make_key(params), default)

    def set(self, params, value):
        self._store[make_key(params)] = value
''',
}
_v3_05_test = '''from cache import SimpleCache


def test_roundtrip():
    c = SimpleCache()
    c.set({"a": 1, "b": 2}, "v")
    assert c.get({"a": 1, "b": 2}) == "v"


def test_order_insensitive():
    c = SimpleCache()
    c.set({"a": 1, "b": 2}, "v")
    assert c.get({"b": 2, "a": 1}) == "v"


def test_three_keys():
    c = SimpleCache()
    c.set({"x": 1, "y": 2, "z": 3}, 42)
    assert c.get({"z": 3, "x": 1, "y": 2}) == 42


def test_miss():
    c = SimpleCache()
    assert c.get({"nope": 0}) is None
'''
_v3_05_fixed = dict(_v3_05_files)
_v3_05_fixed["keygen.py"] = '''def make_key(params):
    """把参数字典序列化为缓存键。同一组参数必须总是得到同一个键。"""
    parts = [f"{k}={v}" for k, v in sorted(params.items())]
    return "&".join(parts)
'''
_add(
    "v3_05", "keygen.py", "stability",
    "一个缓存小项目：cache.py 依赖 keygen.py 生成缓存键。"
    "同样的参数换个插入顺序就查不到缓存，请定位并修复 bug。",
    _v3_05_files, _v3_05_test, _v3_05_fixed,
    "Python dict 保持插入序，不同顺序构造的 dict 产生不同键；症状是缓存未命中",
)


# ---------------------------------------------------------------------------
# v3_06  retry: 次数判断 > 与 >= 混淆 -> 多执行一次
# ---------------------------------------------------------------------------
_v3_06_files = {
    "retry.py": '''def with_retry(fn, attempts):
    """最多调用 fn attempts 次，直到成功；返回 (结果, 实际调用次数)。
    fn 抛异常视为失败。全部失败时返回 (None, 调用次数)。"""
    count = 0
    while count > attempts:      # bug: 初始 0 > attempts 恒假，循环根本不进入？
        count += 1
        try:
            return fn(), count
        except Exception:
            continue
    return None, count
''',
    "client.py": '''from retry import with_retry


def fetch(url_provider, attempts=3):
    """url_provider 是一个返回 url 的可调用对象；返回 (url 或 None, 调用次数)。"""
    return with_retry(url_provider, attempts)
''',
}
_v3_06_test = '''from client import fetch


def make_counter(fail_times):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise RuntimeError("boom")
        return "ok"

    return fn, calls


def test_success_first_try():
    fn, calls = make_counter(0)
    result, used = fetch(fn, attempts=3)
    assert result == "ok" and used == 1


def test_success_after_retries():
    fn, calls = make_counter(2)
    result, used = fetch(fn, attempts=3)
    assert result == "ok" and used == 3


def test_all_fail():
    fn, calls = make_counter(99)
    result, used = fetch(fn, attempts=2)
    assert result is None and used == 2
'''
_v3_06_fixed = dict(_v3_06_files)
_v3_06_fixed["retry.py"] = '''def with_retry(fn, attempts):
    """最多调用 fn attempts 次，直到成功；返回 (结果, 实际调用次数)。
    fn 抛异常视为失败。全部失败时返回 (None, 调用次数)。"""
    count = 0
    while count < attempts:
        count += 1
        try:
            return fn(), count
        except Exception:
            continue
    return None, count
'''
_add(
    "v3_06", "retry.py", "algorithm_logic",
    "一个重试小项目：client.py 依赖 retry.py 的重试器。"
    "测试全部失败（返回 None、调用次数为 0），请定位并修复 bug。",
    _v3_06_files, _v3_06_test, _v3_06_fixed,
    "while count > attempts 恒假 -> 一次都不执行；症状统一为 (None,0)，不指向文件",
)


# ---------------------------------------------------------------------------
# v3_07  csvmini: 引号内逗号未保护 -> 列数错
# ---------------------------------------------------------------------------
_v3_07_files = {
    "csvmini.py": '''def parse_line(line):
    """解析一行 CSV，支持双引号包裹含逗号的字段。返回字段列表。"""
    return line.split(",")      # bug: 完全忽略引号
''',
    "table.py": '''from csvmini import parse_line


def parse_table(text):
    """解析多行 CSV 文本为二维列表（忽略空行）。"""
    rows = []
    for line in text.splitlines():
        if line.strip():
            rows.append(parse_line(line))
    return rows


def column(table, index):
    """取第 index 列（行长度不足时跳过）。"""
    return [row[index] for row in table if len(row) > index]
''',
}
_v3_07_test = '''from table import column, parse_table


def test_simple():
    assert parse_table("a,b,c") == [["a", "b", "c"]]


def test_quoted_comma():
    assert parse_table('1,"x,y",3') == [["1", "x,y", "3"]]


def test_multirow_column():
    t = parse_table("name,city\\nAda,\\"Paris, FR\\"\\nBob,Rome")
    assert column(t, 1) == ["city", "Paris, FR", "Rome"]


def test_blank_lines():
    assert parse_table("a,b\\n\\nc,d") == [["a", "b"], ["c", "d"]]
'''
_v3_07_fixed = dict(_v3_07_files)
_v3_07_fixed["csvmini.py"] = '''def parse_line(line):
    """解析一行 CSV，支持双引号包裹含逗号的字段。返回字段列表。"""
    fields, cur, in_quotes = [], [], False
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
'''
_add(
    "v3_07", "csvmini.py", "string_parsing",
    "一个迷你 CSV 解析项目：table.py 依赖 csvmini.py 的行解析。"
    "含引号字段的行解析错误，请定位并修复 bug。",
    _v3_07_files, _v3_07_test, _v3_07_fixed,
    "经典状态机解析；症状是列数/列内容错，根因在底层解析器",
)


# ---------------------------------------------------------------------------
# v3_08  validator: 边界包含方向反 -> 合法金额被拒
# ---------------------------------------------------------------------------
_v3_08_files = {
    "validator.py": '''def validate_amount(amount, min_val=0, max_val=1000):
    """金额必须在 [min_val, max_val] 内；返回是否合法。"""
    return amount > min_val and amount <= max_val   # bug: 下界应为 >=
''',
    "order.py": '''from validator import validate_amount


def place_order(amount, balance):
    """下单：金额合法且余额足够则返回 ('ok', 剩余余额)，
    金额非法返回 ('invalid', balance)，余额不足返回 ('declined', balance)。"""
    if not validate_amount(amount):
        return "invalid", balance
    if amount > balance:
        return "declined", balance
    return "ok", balance - amount
''',
}
_v3_08_test = '''from order import place_order
from validator import validate_amount


def test_zero_amount_valid():
    assert validate_amount(0) is True


def test_mid_valid():
    assert validate_amount(500) is True


def test_max_valid():
    assert validate_amount(1000) is True


def test_negative_invalid():
    assert validate_amount(-1) is False


def test_order_zero():
    status, rest = place_order(0, 100)
    assert status == "ok" and rest == 100


def test_order_insufficient():
    status, rest = place_order(500, 100)
    assert status == "declined" and rest == 100
'''
_v3_08_fixed = dict(_v3_08_files)
_v3_08_fixed["validator.py"] = '''def validate_amount(amount, min_val=0, max_val=1000):
    """金额必须在 [min_val, max_val] 内；返回是否合法。"""
    return amount >= min_val and amount <= max_val
'''
_add(
    "v3_08", "validator.py", "boundary_condition",
    "一个订单小项目：order.py 依赖 validator.py 校验金额。"
    "金额为 0 的合法订单被拒绝，请定位并修复 bug。",
    _v3_08_files, _v3_08_test, _v3_08_fixed,
    "下界 > 与 >= 的差异只在 amount==0 时暴露；症状在 order 层 ('invalid')",
)


# ---------------------------------------------------------------------------
# v3_09  merge: 合并两个有序列表时用了 pop(0) 反向取？不——比较方向反
# ---------------------------------------------------------------------------
_v3_09_files = {
    "mergeutil.py": '''def merge_sorted(a, b):
    """合并两个升序列表为一个升序列表（不修改原列表）。
    元素按第一个分量比较；相等时应先取 a 中元素（稳定合并）。"""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i][0] < b[j][0]:      # bug: 只看第一个分量，相等时总是先取 b
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out
''',
    "ranker.py": '''from mergeutil import merge_sorted


def rank(players_a, players_b):
    """两个战队按分数升序合并；同分时 A 队成员必须排在 B 队前面。
    输入为 (分数, 队名, 名字) 列表，按分数比较。"""
    keyed_a = [(score, "A", name) for score, name in players_a]
    keyed_b = [(score, "B", name) for score, name in players_b]
    merged = merge_sorted(keyed_a, keyed_b)
    return [name for _, _, name in merged]
''',
}
_v3_09_test = '''from ranker import rank


def test_disjoint():
    assert rank([(1, "a"), (5, "c")], [(2, "b")]) == ["a", "b", "c"]


def test_tie_prefers_a():
    assert rank([(3, "a")], [(3, "b")]) == ["a", "b"]


def test_all_ties():
    assert rank([(1, "x"), (1, "y")], [(1, "z")]) == ["x", "y", "z"]


def test_empty():
    assert rank([], [(4, "q")]) == ["q"]
'''
_v3_09_fixed = dict(_v3_09_files)
_v3_09_fixed["mergeutil.py"] = '''def merge_sorted(a, b):
    """合并两个升序列表为一个升序列表（不修改原列表）。
    元素按第一个分量比较；相等时应先取 a 中元素（稳定合并）。"""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i][0] <= b[j][0]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out
'''
_add(
    "v3_09", "mergeutil.py", "stability",
    "一个排行榜小项目：ranker.py 依赖 mergeutil.py 合并两个有序列表。"
    "同分时的相对顺序不符合约定，请定位并修复 bug。",
    _v3_09_files, _v3_09_test, _v3_09_fixed,
    "buggy 只比第一个分量且相等时先取 b：test_tie_prefers_a 得 ['b','a']；"
    "test_all_ties 得 ['z','x','y']；无同分用例不受影响 → 部分失败模式",
)


# ---------------------------------------------------------------------------
# v3_10  stats: 方差除 n 与 n-1 + window 长度串扰
# ---------------------------------------------------------------------------
_v3_10_files = {
    "window.py": '''def moving_average(nums, k):
    """返回滑动平均列表：每个位置取其后 k 个元素（含自身）的平均值；
    尾部不足 k 个时按实际长度平均。nums 为空返回空列表。"""
    out = []
    for i in range(len(nums)):
        chunk = nums[i : i + k - 1]     # bug: 窗口少取一个元素
        out.append(sum(chunk) / len(chunk))
    return out
''',
    "report.py": '''from window import moving_average


def smooth_report(nums, k):
    """返回 (滑动平均列表, 最后一个窗口的平均值)。"""
    ma = moving_average(nums, k)
    return ma, ma[-1] if ma else None
''',
}
_v3_10_test = '''from report import smooth_report
from window import moving_average


def test_k1_identity():
    assert moving_average([1, 2, 3], 1) == [1, 2, 3]


def test_k2():
    assert moving_average([1, 3, 5], 2) == [2.0, 4.0, 5.0]


def test_k_full():
    assert moving_average([2, 4], 2) == [3.0, 4.0]


def test_empty():
    assert moving_average([], 3) == []


def test_report():
    ma, last = smooth_report([1, 3, 5], 2)
    assert last == 5.0
'''
_v3_10_fixed = dict(_v3_10_files)
_v3_10_fixed["window.py"] = '''def moving_average(nums, k):
    """返回滑动平均列表：每个位置取其后 k 个元素（含自身）的平均值；
    尾部不足 k 个时按实际长度平均。nums 为空返回空列表。"""
    out = []
    for i in range(len(nums)):
        chunk = nums[i : i + k]
        out.append(sum(chunk) / len(chunk))
    return out
'''
_add(
    "v3_10", "window.py", "off_by_one",
    "一个数据平滑小项目：report.py 依赖 window.py 的滑动平均。"
    "滑动平均值普遍偏差，请定位并修复 bug。",
    _v3_10_files, _v3_10_test, _v3_10_fixed,
    "k=1 时 i:i+0 为空 -> ZeroDivisionError，症状是崩溃而非数值错，反馈信号不同",
)
