import json
import requests


def get_enemies():
    url = "https://api.open5e.com/monsters/?document__slug=wotc-srd"
    enemies = []
    damage_types = []
    response = requests.get(url)
    enemy_section = response.json()
    while enemy_section["next"]:
        for enemy in enemy_section["results"]:
            enemies.append(enemy["name"])
            if enemy["damage_vulnerabilities"] not in damage_types:
                damage_types.append(enemy["damage_vulnerabilities"])
            if enemy["damage_resistances"] not in damage_types:
                damage_types.append(enemy["damage_resistances"])
            if enemy["damage_immunities"] not in damage_types:
                damage_types.append(enemy["damage_immunities"])

        response = requests.get(enemy_section["next"])
        enemy_section = response.json()

    for enemy in enemy_section["results"]:
        enemies.append(enemy["name"])
        if enemy["damage_vulnerabilities"] not in damage_types:
            damage_types.append(enemy["damage_vulnerabilities"])
        if enemy["damage_resistances"] not in damage_types:
            damage_types.append(enemy["damage_resistances"])
        if enemy["damage_immunities"] not in damage_types:
            damage_types.append(enemy["damage_immunities"])

    info = [enemies, damage_types]

    return info

def main():
    info = get_enemies()
    with open("enemy_names.txt", "w") as output:
        json.dump(info[0], output, indent = 4)
    with open("damage_types.txt", "w") as output:
        json.dump(info[1], output, indent = 4)


main()