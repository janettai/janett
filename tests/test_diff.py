from janett.core.diff import changed_paths, parse_diff

MULTI = """\
diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,5 @@
 import os
+import sys

 def main():
-    print("hi")
+    print("hello")
+    return 0
diff --git a/README.md b/README.md
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/README.md
@@ -0,0 +1,2 @@
+# Title
+body
"""


def test_parses_multiple_files():
    files = parse_diff(MULTI)
    assert [f.path for f in files] == ["src/app.py", "README.md"]


def test_new_file_flag():
    files = parse_diff(MULTI)
    readme = files[1]
    assert readme.is_new is True
    assert readme.old_path is None


def test_added_line_numbers():
    files = parse_diff(MULTI)
    app = files[0]
    # `import sys` added at new line 2; print("hello") and return 0 added later.
    added = app.added_line_numbers()
    assert 2 in added  # import sys
    assert 1 not in added  # context line `import os`


def test_changed_paths_skips_nothing_reviewable():
    files = parse_diff(MULTI)
    assert set(changed_paths(files)) == {"src/app.py", "README.md"}


def test_empty_diff():
    assert parse_diff("") == []
