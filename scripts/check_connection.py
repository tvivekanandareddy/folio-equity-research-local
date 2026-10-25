from dotenv import dotenv_values
from urllib.parse import urlsplit
import socket
v=dotenv_values('.env');u=urlsplit(v.get('DATABASE_URL') or '')
print({'pooler_host':bool(u.hostname and u.hostname.endswith('.pooler.supabase.com')),'database_name_valid':u.path=='/postgres','pooler_user_format':bool(u.username and u.username.startswith('postgres.')),'uri_contains_placeholder':'[' in (v.get('DATABASE_URL') or '')},flush=True)
try:
 addresses=socket.getaddrinfo(u.hostname,u.port or 5432,type=socket.SOCK_STREAM)
 print('DNS resolved.',flush=True)
 for port in [u.port or 5432,6543]:
  try:
   with socket.create_connection((u.hostname,port),timeout=6):print(f'TCP port {port} reachable.',flush=True)
  except Exception as e:print(f'TCP port {port}: {type(e).__name__}',flush=True)
except Exception as e: print(f'DNS check: {type(e).__name__}',flush=True)
