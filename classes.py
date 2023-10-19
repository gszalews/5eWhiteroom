from dataclasses import dataclass, field
from helpers import dice_average, get_weapons, get_spells
SPACE = "    "
@dataclass
class Damage():
    ave: int
    dice: str
    type: str

    def __str__(self) -> str:
        return f"(ave: {self.ave} dice: {self.dice} type: {self.type})"

@dataclass
class Save():
    dc: int
    ability: str

    def __str__(self) -> str:
        return f"(dc: {self.dc} ability: {self.ability})"

@dataclass
class Action():
    name: str
    desc: str
    type: str
    dmg: list
    save: list
    hit: int = 0

    def __str__(self) -> str:
        return f"{SPACE * 2 + self.name}:\n{SPACE * 3 + self.desc}\n{SPACE * 3}Hit: {self.hit} Dmg: {self.dmg} Save: {self.save}"

@dataclass
class Multiattack:
    attacks: dict

@dataclass
class Spell:
    ave: int
    dice: str
    save: bool
    throw: Save
    attack: bool
    hit: int

@dataclass
class Ability:
    value: int = 0
    bonus: int = field(init = False)
    save: int = field(init = False)

    def __post_init__(self):
        self.bonus = self.value // 2 - 5
        self.save = self.bonus

@dataclass
class Weapon:
    name: str
    magic_bonus: int = 0
    does_extra_dmg: bool = False
    extra_dmg: Damage = None
    extra_dmg_monster_type: str = None
    crit: float = 0.5
    properties: list = None
    dmg: Damage = None

    def __post_init__(self):
        weapons = get_weapons()
        for wp in weapons["results"]:
            if wp["name"] == self.name:
                d = dice_average(wp["damage_dice"])
                self.dmg = Damage(d, wp["damage_dice"], wp["damage_type"])

@dataclass
class Character:
    name: str
    hp: int
    ac: int
    scores: dict
    spells: list

@dataclass
class Hero(Character):
    c_class: str
    level: int
    attacks: int
    weapon1: Weapon
    weapon2: Weapon
    fighting_style: str
    is_spellcaster: bool
    caster_type: str
    prof_bonus: int = field(init=False)
    
    def __post_init__(self):
        prof_bonus = 0
        if self.level < 5:
            prof_bonus = 2
        elif self.level < 9:
            prof_bonus = 3
        elif self.level < 13:
            prof_bonus = 4
        elif self.level < 17:
            prof_bonus = 5
        elif self.level > 16:
            prof_bonus = 6
        self.prof_bonus = prof_bonus

    

    

