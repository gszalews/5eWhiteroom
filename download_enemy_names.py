import json
import requests


def get_enemies():
    '''
    Get enemies from open5e API

    :param slug: Document slug for use in API call
    :type slug: str
    :return: A list of enemies in JSON format
    :rtype: list

    '''
    url = f"https://api.open5e.com/monsters/"
    total_results = []
    response = requests.get(url)
    data = response.json()
    total_results = total_results + data["results"]

    # Loop to handle multi-page return from API call
    while data["next"] is not None:
        response = requests.get(data["next"])
        data = response.json()
        total_results = total_results + data["results"]
    return total_results

def main():
    info = get_enemies()
    monsters = []
    for enemy in info:
        e = {"name": enemy["name"], "slug": enemy["document__slug"]}
        monsters.append(e)
    with open("static/files/all_enemy_names.txt", "w") as output:
        json.dump(monsters, output, indent = 4)


if __name__ == "__main__":
    main()