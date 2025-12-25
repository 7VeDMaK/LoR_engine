from logic.modifiers import RollContext

# Реестр всех доступных в игре пассивок
PASSIVE_REGISTRY = {}

def register_passive(name):
    def decorator(func):
        PASSIVE_REGISTRY[name] = func
        return func
    return decorator

# --- Реализация конкретных пассивок ---

@register_passive("Lone Fixer")
def p_lone_fixer(ctx: RollContext):
    # Упрощение: всегда дает +3
    ctx.modify_power(3, "Lone Fixer")

@register_passive("Paralysis")
def p_paralysis(ctx: RollContext):
    # Уменьшает результат на 2
    ctx.modify_power(-2, "Paralysis")

@register_passive("Strength")
def p_strength(ctx: RollContext):
    ctx.modify_power(1, "Strength")