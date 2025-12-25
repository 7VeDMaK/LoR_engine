# logic/card_scripts.py

def convert_evade_to_haste(context, params):
    """Пример: Инерция. Конвертирует уклонения в спешку."""
    # Здесь будет логика доступа к user.combat_dashboard
    print(f"DEBUG: Сработал скрипт 'convert_evade_to_haste'")

def apply_status(context, params):
    """Универсальный скрипт наложения статуса"""
    status = params.get("status")
    stack = params.get("stack", 1)
    target = params.get("target", "enemy") # self или enemy
    print(f"DEBUG: Накладываем {status} x{stack} на {target}")

def break_die_slot(context, params):
    """Пример: Пурж-Токсин. Ломает слот кубика."""
    slot = params.get("slot", 0)
    print(f"DEBUG: Ломаем слот {slot} у врага")

def heal_percent_medicine(context, params):
    """Пример: Морфиновый дротик"""
    print(f"DEBUG: Лечим цель на % от Медицины")

# === РЕЕСТР СКРИПТОВ ===
# Строка из JSON -> Функция Python
SCRIPTS_REGISTRY = {
    "convert_evade_to_haste": convert_evade_to_haste,
    "apply_status": apply_status,
    "break_die_slot": break_die_slot,
    "heal_percent_medicine": heal_percent_medicine
}