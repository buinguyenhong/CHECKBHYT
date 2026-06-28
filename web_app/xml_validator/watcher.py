import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class XMLFolderHandler(FileSystemEventHandler):
    def __init__(self, callback, debounce_seconds=2.0):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.timer = None
        self.lock = threading.Lock()

    def on_any_event(self, event):
        # Chỉ quét khi có thay đổi trên file .xml
        if event.is_directory:
            return
        if not event.src_path.lower().endswith(".xml"):
            return
            
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(self.debounce_seconds, self.callback)
            self.timer.start()

class XMLWatcher:
    def __init__(self, watch_dir, callback, debounce_seconds=2.0):
        self.watch_dir = watch_dir
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.observer = None
        self.is_running = False
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            if self.is_running:
                return
            os.makedirs(self.watch_dir, exist_ok=True)
            event_handler = XMLFolderHandler(self.callback, self.debounce_seconds)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.watch_dir, recursive=False)
            self.observer.start()
            self.is_running = True
            print(f"[*] Started XML Watcher on folder: {self.watch_dir}")

    def stop(self):
        with self.lock:
            if not self.is_running:
                return
            if self.observer:
                self.observer.stop()
                self.observer.join()
            self.is_running = False
            print(f"[*] Stopped XML Watcher.")
            
    def get_status(self):
        with self.lock:
            return self.is_running
