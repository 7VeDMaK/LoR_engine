# core/unit_library.py
import os
import json
from core.unit import Unit


class UnitLibrary:
    _roster = {}
    DATA_PATH = "data/units"

    @classmethod
    def load_all(cls):
        """Загружает всех персонажей из JSON файлов в папке."""
        cls._roster = {}
        if not os.path.exists(cls.DATA_PATH):
            os.makedirs(cls.DATA_PATH, exist_ok=True)
            print(f"Created directory: {cls.DATA_PATH}")
            return {}

        files = [f for f in os.listdir(cls.DATA_PATH) if f.endswith('.json')]
        print(f"Loading units from {cls.DATA_PATH}...")

        for filename in files:
            path = os.path.join(cls.DATA_PATH, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    unit = Unit.from_dict(data)
                    cls._roster[unit.name] = unit
                    print(f"✔ Loaded: {unit.name}")
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")

        return cls._roster

    @classmethod
    def save_unit(cls, unit: Unit):
        """Сохраняет одного персонажа в файл."""
        if not os.path.exists(cls.DATA_PATH):
            os.makedirs(cls.DATA_PATH, exist_ok=True)

        # Формируем имя файла из имени персонажа (безопасно)
        safe_name = "".join(c for c in unit.name if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_")
        filename = f"{safe_name}.json"
        path = os.path.join(cls.DATA_PATH, filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(unit.to_dict(), f, indent=4, ensure_ascii=False)
            print(f"💾 Saved unit: {unit.name} -> {path}")
            # Обновляем кэш
            cls._roster[unit.name] = unit
            return True
        except Exception as e:
            print(f"Error saving unit: {e}")
            return False

    @classmethod
    def get_roster(cls):
        return cls._roster