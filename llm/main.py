import sys
from pathlib import Path

# Добавляем директорию src в путь поиска модулей
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm.main import main

if __name__ == "__main__":
    main()
