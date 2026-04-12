import threading
import socketserver
from http.server import SimpleHTTPRequestHandler
from functools import partial
from PyQt5.QtCore import QObject, pyqtSignal

class ServerThread(QObject):
    status_changed = pyqtSignal(bool, str)

    def __init__(self, port, www_path):
        super().__init__()
        self.port = port
        self.www_path = www_path
        self.server = None
        self.thread = None
        self.is_running = False

    def start_server(self):
        if self.is_running:
            return False
        handler = partial(SimpleHTTPRequestHandler, directory=self.www_path)
        try:
            self.server = socketserver.ThreadingTCPServer(("", self.port), handler)
            self.server.allow_reuse_address = True
            self.is_running = True
            self.status_changed.emit(True, f"Server started on port {self.port}")
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return True
        except OSError as e:
            if "Address already in use" in str(e):
                self.status_changed.emit(False, f"Port {self.port} already in use")
            else:
                self.status_changed.emit(False, f"OS Error: {e}")
            return False
        except Exception as e:
            self.status_changed.emit(False, f"Error: {e}")
            return False

    def stop_server(self):
        if self.server and self.is_running:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.is_running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1)
            self.status_changed.emit(False, "Server stopped")
            return True
        return False