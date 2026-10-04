from dataclasses import dataclass

@dataclass
class Meal:
    id: int
    name: str
    ingredients: set[str]
    recipe: str

    def __repr__(self):
        return f"{self.name} (#{self.id})"

    def __eq__(self, value: Meal) -> bool:
        return self.id == value.id
