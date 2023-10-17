from dataclasses import dataclass, field


@dataclass
class Action:
    name: str
    desc: str
    type: str
    hit: int = 0
    damage: list = field(factory_default = lambda : [])
    save: list = field(factory_default = lambda : [])

    def __str__(self) -> str:
        return f"{SPACE * 2 + self.name}:\n{SPACE * 3 + self.desc}\n{SPACE * 3}Hit: {self.hit} Dmg: {self.damage} Save: {self.save}\n"

    def roll(self, ac):
        if (random.randint(1, 20) + self.hit) >= ac:
            return True
        return False


@dataclass
class Character:
    name: str
    hp: int
    multiattack: bool
    mattacks: dict = field(factory_default = lambda : {})
    actions: dict = field(factory_default = lambda : {})
    stats: dict = field(factory_default = lambda : {})
    spells: list = field(factory_default = lambda : [])

@dataclass
class Damage:
    ave: int
    dice: str
    type: str

@dataclass
class Enemy(Character):
    legendary_actions: dict = field(factory_default = lambda : {})

@dataclass
class Hero(Character):
    weapon1 = str
    weapon2 = str
    
@dataclass
class Multiattack:

@dataclass
class Save:
    dc: int
    ability: str

@dataclass
class Spell:
    ave: int
    dice: str
    save: bool
    throw: Save
    attack: bool
    hit: int

@dataclass
class Stat:
    name: str
    value: int
    bonus: int
    save: int
