from bookbot import parse_db_datetime
from database import convert_datetime

print('parse1:', parse_db_datetime('2025-12-01 15:20:30'))
print('parse2:', parse_db_datetime('2025-12-01'))
print('conv1:', convert_datetime(b'2025-12-01 15:20:30'))
print('conv2:', convert_datetime('2025-12-01T15:20:30'))
