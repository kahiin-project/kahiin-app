import signal
import logging
import sys

def setup_signal_handlers():
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}. Performing cleanup...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)