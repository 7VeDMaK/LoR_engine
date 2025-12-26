from dataclasses import dataclass

@dataclass
class Resistances:
    slash: float = 1.0
    pierce: float = 1.0
    blunt: float = 1.0

    def to_dict(self):
        return {"slash": self.slash, "pierce": self.pierce, "blunt": self.blunt}

    @classmethod
    def from_dict(cls, data: dict):
        if not data: return cls()
        return cls(
            slash=data.get("slash", 1.0),
            pierce=data.get("pierce", 1.0),
            blunt=data.get("blunt", 1.0)
        )