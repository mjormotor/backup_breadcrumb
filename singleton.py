"""
/* --------------------------------
   Singleton component

 - to keep single process to manage 1 of the repository
-------------------------------- */
"""
import sys

from Socket_Singleton import MultipleSingletonsError, Socket_Singleton


class Singleton(Socket_Singleton):
	def __init__(self, address: str = "127.0.0.1", port: int = 1337, timeout: int = 0, client: bool = True, strict: bool = True, max_clients: int = 0):
		super().__init__(address, port, timeout, client, strict, max_clients)
		
		self.address = address
	
	def _create_client(self):
		# idea by https://qiita.com/takavfx/items/3ce8a10d8d7b7759e58a
		with self._sock as sock:
			sock.connect((self.address, self.port))
			sock.send(" ".join(sys.argv).encode())
