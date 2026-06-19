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


# --- regression: hunk body lines that look like file headers ---------------

HEADER_LIKE_BODY = """\
diff --git a/sig.txt b/sig.txt
--- a/sig.txt
+++ b/sig.txt
@@ -1,3 +1,3 @@
 hello
---
+++ world
"""


def test_body_lines_not_misparsed_as_headers():
    # Deleting "-- " (email signature) yields a body line "--- "; adding
    # "++ world" yields "+++ world". Neither should overwrite the file paths.
    files = parse_diff(HEADER_LIKE_BODY)
    assert len(files) == 1
    assert files[0].path == "sig.txt"
    assert files[0].old_path == "sig.txt"
    # "++ world" is added at new line 2 (the "---" deletion doesn't advance it).
    assert files[0].added_line_numbers() == {2}


# --- regression: "\\ No newline at end of file" marker ---------------------

NO_NEWLINE = """\
diff --git a/a.txt b/a.txt
--- a/a.txt
+++ b/a.txt
@@ -1,2 +1,3 @@
 first
-second
\\ No newline at end of file
+second
+third
"""


def test_no_newline_marker_does_not_shift_line_numbers():
    files = parse_diff(NO_NEWLINE)
    added = files[0].added_line_numbers()
    # "second" (new line 2) and "third" (new line 3) are added; the marker
    # must not bump the counter, which would wrongly yield {3, 4}.
    assert added == {2, 3}
