# rin-leet

LeetCode in [rin](https://github.com/IbrahimHindawi/rin). You write a rin proc
with LeetCode's C signature; `leet.py` compiles it to one C file and submits it
through leetgo, so LeetCode's own judge runs it, hidden cases and time limits
included.

## Requirements

- Python 3
- rin, found through `RIN_HOME`, `PATH`, or `C:\devel\rin-windows-x64`
- [leetgo](https://github.com/j178/leetgo) on `PATH`
- Firefox, logged in to leetcode.com: leetgo reads the login from it
  (`judge/leetgo.yaml`). Chrome, Edge and Brave encrypt their cookies so that
  nothing outside the browser can read them.

## The loop

```
python leet.py next        # start the next Blind 75 problem you haven't solved
python leet.py test 1      # run LeetCode's example cases on your solution
python leet.py submit 1    # test, then submit if the examples pass
```

`start` (which `next` and `random` call) makes `problems/0001-two-sum/` with
the statement in `README.md` and `solution.rin`, which holds LeetCode's C
signature as a comment:

```
// int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
```

Write that function in rin, same name and signature, importing the std files
you use:

```rin
import "../../lib/lc.rin"
import "std/hashmap.rin"

twoSum: proc(nums: [*]i32, numsSize: i32, target: i32, returnSize: *i32) -> [*]i32 = {
    arena: *memops_arena = lc_begin();
    xs: []i32 = nums[0..numsSize];
    seen: hashmap<i32, i32> = {};
    out: [*]i32 = cast(memops_arena_push(arena, 2 * sizeof(i32), alignof(i32)), [*]i32);
    returnSize[0] = 0;
    for (i: u64 = 0; i < xs.length; i += 1) {
        at: *i32 = hashmap<i32, i32>get(seen&, target - xs[i]);
        if (at != null) {
            out[0] = at[0];
            out[1] = cast(i, i32);
            returnSize[0] = 2;
            return out;
        }
        hashmap<i32, i32>put(arena, seen&, xs[i], cast(i, i32));
    }
    return out;
}
```

`int` is `i32`, `long long` is `i64`, `double` is `f64`, `char` is `c8`, and a
pointer `T*` is `[*]T`. Slice a pointer with its size to get a checked `[]T`.

`lc_begin()` empties the arena for the new test case and returns it: call it
once, at the top of the function LeetCode calls. A helper that needs the arena
takes it from `lc_arena()`, which leaves it alone. LeetCode never frees what
you return, so returning arena memory is fine.

`test` and `submit` compile `solution.rin` with `rin compile --single-file`,
put the result between the `@lc code` markers in `judge/c/<id>.<slug>.c`, and
run `leetgo test` / `leetgo submit`. An accepted submit is recorded in
`progress.json`; `stats` and `list --todo` read it.

Other commands: `random -d medium`, `list --path blind75`, `show 42`, `stats`.
A problem can be named by number, slug or folder. Numbers, titles and
difficulties come from leetgo's question cache (`leetgo cache update` refreshes
it).

## std, one file each

Import what a solution uses; nothing is pulled in wholesale.

| import | |
|---|---|
| `std/vec.rin` | `vec<T>`, a growable array: `append`, `pop`, `last`, `items` (as a slice) |
| `std/hashmap.rin`, `std/hashset.rin` | `hashmap<K, V>`, `hashset<K>`: any key with `hash`/`equal`, such as ints, `[]c8`, or your own struct |
| `std/heap.rin` | `heap<T>`, a priority queue with a comparator: `less_i32` is a min-heap, `greater_i32` a max-heap |
| `std/deque.rin` | `deque<T>`, a ring buffer, for BFS and sliding windows |
| `std/sort.rin` | `sort`, `lower_bound`, `upper_bound`, `reverse` over any slice, with a comparator |
| `std/dsu.rin` | union-find |
| `std/order.rin` | the comparators (`less_i32`, `greater_i64`, ...) and `swap` |

A comparator is a plain proc, as with C's `qsort`:

```rin
by_start: proc(a: []i32, b: []i32) -> b32 = { return a[0] < b[0]; }
sort<[]i32>(intervals, by_start);
```

## Things to know

- **Premium problems** can't be picked or submitted without Premium; `next` and
  `random` skip them, and `list` marks them with `$`.
- **Lists and trees** haven't been tried yet. LeetCode's C defines
  `struct ListNode` and `struct TreeNode` itself, so the rin side has to refer
  to those rather than declare its own.
- **Statements stay local.** `problems/*/README.md` and `judge/c/` are fetched
  from LeetCode and are not committed.
