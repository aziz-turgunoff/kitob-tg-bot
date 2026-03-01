import py_compile
try:
    py_compile.compile('bookbot.py', doraise=True)
    print("Compilation successful!")
except py_compile.PyCompileError as e:
    print(f"Compilation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
