import copy
import json
import os
import glob
from core.models import Card


class Library:
    _cards = {}  # Тут хранятся ВСЕ карты (из всех файлов) для игры

    @classmethod
    def register(cls, card: Card):
        """Просто добавляет карту в оперативную память"""
        key = card.id if card.id and card.id != "unknown" else card.name
        cls._cards[key] = card

    @classmethod
    def get_card(cls, key: str) -> Card:
        if key in cls._cards:
            return copy.deepcopy(cls._cards[key])
        for card in cls._cards.values():
            if card.name == key:
                return copy.deepcopy(card)
        return Card("Unknown", 0, [])

    @classmethod
    def get_all_cards(cls):
        return list(cls._cards.values())

    # === ЗАГРУЗКА (ЧИТАЕТ ВСЮ ПАПКУ) ===
    @classmethod
    def load_all(cls, path="data/cards"):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            return

        if os.path.isdir(path):
            files = glob.glob(os.path.join(path, "*.json"))
            print(f"--- Загрузка карт из папки {path} ---")
            for filepath in files:
                cls._load_single_file(filepath)
        else:
            cls._load_single_file(path)

    @classmethod
    def _load_single_file(cls, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cards_list = data.get("cards", []) if isinstance(data, dict) else data

            count = 0
            for card_data in cards_list:
                card = Card.from_dict(card_data)
                cls.register(card)
                count += 1
            print(f"✔ {os.path.basename(filepath)}: {count} шт.")
        except Exception as e:
            print(f" Ошибка {filepath}: {e}")

    # === СОХРАНЕНИЕ (ПИШЕТ ТОЛЬКО ОДНУ КАРТУ) ===
    @classmethod
    def save_card(cls, card: Card, filename="custom_cards.json"):
        """
        Сохраняет конкретную карту в конкретный файл.
        Не перезаписывает всю библиотеку!
        """
        folder = "data/cards"
        filepath = os.path.join(folder, filename)
        os.makedirs(folder, exist_ok=True)

        # 1. Читаем текущий файл (если он есть)
        current_data = {"cards": []}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    # Поддержка старого формата (список) и нового (dict)
                    if isinstance(content, list):
                        current_data["cards"] = content
                    else:
                        current_data = content
            except Exception as e:
                print(f"Ошибка чтения файла сохранения: {e}")

        # 2. Ищем, есть ли карта с таким ID внутри этого файла
        card_dict = card.to_dict()
        found = False

        for i, existing in enumerate(current_data["cards"]):
            if existing.get("id") == card.id:
                # Если нашли - обновляем
                current_data["cards"][i] = card_dict
                found = True
                break

        if not found:
            # Если не нашли - добавляем в конец
            current_data["cards"].append(card_dict)

        # 3. Записываем обратно только в этот файл
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

        print(f" Карта '{card.name}' сохранена в {filename}")

        # 4. Не забываем обновить карту в памяти, чтобы сразу играть ей
        cls.register(card)


# Инициализация
Library.load_all("data/cards")