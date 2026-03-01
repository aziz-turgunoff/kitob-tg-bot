import os, sys
with open('debug_output.txt', 'w') as f:
    f.write(f"CWD: {os.getcwd()}\n")
    f.write(f"Files: {os.listdir('.')}\n")
    try:
        import config
        f.write("Config imported!\n")
    except Exception as e:
        import traceback
        f.write(f"Import failed: {str(e)}\n")
        f.write(traceback.format_exc())
