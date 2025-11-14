import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding='UTF-8'),
    ]
)

logger = logging.getLogger(__name__)
