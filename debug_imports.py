try:
    print("Checking config...")
    import config
    print("Checking database...")
    import database
    print("Checking bookbot...")
    from bookbot import parse_db_datetime
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
