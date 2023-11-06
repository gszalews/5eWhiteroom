import os
import json
from flask import Flask, flash, redirect, render_template, request, session, send_file
from flask_session import Session
from helpers import get_weapons, get_spells, get_enemy, get_prof, get_mod, update_party, update_enemies, ave_pc_dmg, ave_enemy_dmg, process_pc_spells, pull_monster, process_statblock, get_xp
import re
from tempfile import mkdtemp
from werkzeug.utils import secure_filename


# Configure application
app = Flask(__name__)
ALLOWED_EXTENSIONS = {"party", "enemies", "encounter"}
PATH = ""
#PATH = "/home/gszalews/mysite/"
# # Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
def index():
    party = session.get("party")
    if party == None:
        session["party"] = []
        party = session.get("party")
    enemies = session.get("enemies")
    if enemies == None:
        session["enemies"] = []
        enemies = session.get("enemies")
    encounter = session.get("encounter")
    if encounter == None:
        session["encounter"] = {"party": {"count": 0}, "enemies": {"count": 0}}
        encounter = session.get("encounter")
    return render_template("index.html")


@app.route("/party", methods=["GET", "POST"])
def party():
    weapons = get_weapons()
    spells = get_spells()
    party = session.get("party")
    if party == None:
        session["party"] = []
        party = session.get("party")
    encounter = session.get("encounter")
    if encounter == None:
        session["encounter"] = {"party": {"count": 0}, "enemies": {"count": 0}}
        encounter = session.get("encounter")


    if request.method == "POST":
        # add character to party
        name = request.form.get("name")
        for pc in party:
            if pc["name"] == name:
                name = name + "*"
        character = {
        "name": name,
        "class": request.form.get("class"),
        "level": int(request.form.get("level")),
        "prof_bonus": get_prof(request.form.get("level")),
        "hp": int(request.form.get("hp")),
        "ac": int(request.form.get("ac")),
        "scores": {"str": request.form.get("str"), "dex":request.form.get("dex"), "con": request.form.get("con"), "int":
                  request.form.get("int"), "wis": request.form.get("wis"), "cha": request.form.get("cha")}
        }
        for abl in character["scores"].keys():
            if not character["scores"][abl]:
                character["scores"][abl] = 0
            else:
                character["scores"][abl] = int(character["scores"][abl])
        character["modifiers"] = {"str": get_mod(character["scores"]["str"]), "dex": get_mod(character["scores"]["dex"]), "con": get_mod(character["scores"]["con"]),
                      "int": get_mod(character["scores"]["int"]), "wis": get_mod(character["scores"]["wis"]), "cha": get_mod(character["scores"]["cha"])}
        if request.form.get("attacks"):
            character["attacks"] = int(request.form.get("attacks"))
        else:
            character["attacks"] = 1
        
        if request.form.get("fighting_style"):
            character["fighting_style"] = request.form.get("fighting_style")
        else:
            character["fighting_style"] = "none"
        
        # main weapon info
        if request.form.get("weapon1"):
            weapon = request.form.get("weapon1")
            for wp in weapons["results"]:
                if wp["name"] == weapon:
                    character["weapon1"] = wp
        else:
            character["weapon1"] = {}
            character["weapon1"]["name"] = "none"

        if request.form.get("magic1"):
            character["weapon1"]["magic_bonus"] = int(request.form.get("magic1"))
        else:
            character["weapon1"]["magic_bonus"] = 0

        if request.form.get("xdmg_dice1"):
            character["weapon1"]["extra_damage_dice"] = request.form.get("xdmg_dice1")
            character["weapon1"]["extra_damage_type"] = request.form.get("xdmg_type1")
            character["weapon1"]["extra_damage_monster_type"] = request.form.get("xdmg_mon1")
        else:
            character["weapon1"]["extra_damage_dice"] = "none"

        if request.form.get("imp_crit1"):
            character["weapon1"]["crit"] = .1
        else:
            character["weapon1"]["crit"] = .05

        # 2nd weapon info
        if request.form.get("weapon2"):
            weapon2 = request.form.get("weapon2")
            for wp in weapons["results"]:
                if wp["name"] == weapon2:
                    character["weapon2"] = wp
            if request.form.get("magic2"):
                character["weapon2"]["magic_bonus"] = int(request.form.get("magic2"))
            else:
                character["weapon2"]["magic_bonus"] = 0
            if request.form.get("xdmg_dice2"):
                character["weapon2"]["extra_damage_dice"] = request.form.get("xdmg_dice2")
                character["weapon2"]["extra_damage_type"] = request.form.get("xdmg_type2")
                character["weapon2"]["extra_damage_monster_type"] = request.form.get("xdmg_mon2")
            else:
                character["weapon2"]["extra_damage_dice"] = "none"
            if request.form.get("imp_crit2"):
                character["weapon2"]["crit"] = .1
            else:
                character["weapon2"]["crit"] = .05
        else:
            character["weapon2"] = {}
            character["weapon2"]["name"] = "none"
            character["weapon2"]["magic_bonus"] = 0
            character["weapon2"]["extra_damage_dice"] = "none"
            character["weapon2"]["crit"] = .05      

        # spellcasting info
        caster = request.form["caster_type"]
        if caster != "none":
            character["spellcaster"] = True
            character["caster_type"] = caster
            char_spells = []
            for i in range(1, 6):
                if request.form.get("spell" + str(i)):
                    char_spells.append(request.form.get("spell" + str(i)))
            character["spells"] = []
            for name in char_spells:
                for spell in spells:
                    if spell["name"] == name:
                        character["spells"].append(spell)
            process_pc_spells(character)
        else:
            character["spellcaster"] = False
            character["caster_type"] = "none"
        session["party"].append(character)
        party = session["party"]
        update_party(party, encounter)
        if encounter["enemies"]["count"] > 0:
            ave_pc_dmg(character, encounter)
            enemies = session.get("enemies")
            for enemy in enemies:
                ave_enemy_dmg(enemy, encounter)
        else:
            character["dpr"] = {"base": 0, "med": 0, "high": 0}
    dpr_total = 0
    if encounter["enemies"]["count"] > 0:
        for pc in party:
            if "dpr" in pc.keys():
                dpr_total = round(dpr_total + pc["dpr"]["med"], 2)

    return render_template("party.html", weapons=weapons, spells=spells, party=party, encounter=encounter, dpr_total=dpr_total)


@app.route("/enemies", methods=["GET", "POST"])
def enemies():
    with open(PATH + "static/files/all_enemy_names.txt", "r") as input:
        enemy_names = json.load(input)
    #Get enemies session data
    enemies = session.get("enemies")
    if enemies == None:
        session["enemies"] = []
        enemies = session.get("enemies")
    #Get any encounter session data
    encounter = session.get("encounter")
    if encounter == None:
        session["encounter"] = {"party": {"count": 0}, "enemies": {"count": 0}}
        encounter = session.get("encounter")


    #On submit add enemy to enemy session list
    if request.method == "POST":
        name = request.form.get("monster-select")
        result = re.search(r"^.* \((\w+|wotc-srd)\)", name)
        if result:
            slug = result[1]
            name = name.replace(f" ({slug})", "")
        else:
            return redirect("/enemies")
        count = request.form.get("count")
        found = False
        samename = False
        for monster in enemies:
            if monster["name"] == name and slug == monster["document__slug"]:
                monster["count"] = monster["count"] + int(count)
                found = True
            elif monster["name"] == name and slug != monster["document__slug"]:
                samename = True
                monsterslug = monster["document__slug"]
                monster["name"] = monster["name"] + f" ({monsterslug})"
        if not found:
            enemy = get_enemy(name, slug)
            if samename:
                enemy["name"] = enemy["name"] + f" ({slug})"
            enemy["count"] = int(count)
            session["enemies"].append(enemy)
        #Update encounter variables
        update_enemies(enemies, encounter)
        if encounter["party"]["count"] > 0:
            if not found:
                ave_enemy_dmg(enemy, encounter)
            party = session.get("party")
            for character in party:
                ave_pc_dmg(character, encounter)
    dpr_total = 0
    if encounter["party"]["count"] > 0:
        for enemy in enemies:
            if "dpr" in enemy.keys():
                dpr_total = round(dpr_total + (enemy["dpr"] * enemy["count"]), 2)
    return render_template("enemies.html", enemy_names=enemy_names, enemies=enemies, encounter=encounter, dpr_total=dpr_total)


@app.route("/statblock", methods=["GET", "POST"])
def statblock():
    # with open(PATH + "static/files/all_enemy_names.txt", "r") as input:
    #     enemy_names = json.load(input)
    # #Get enemies session data
    # enemies = session.get("enemies")
    # if enemies == None:
    #     session["enemies"] = []
    #     enemies = session.get("enemies")
    # #Get any encounter session data
    # encounter = session.get("encounter")
    # if encounter == None:
    #     session["encounter"] = {"party": {"count": 0}, "enemies": {"count": 0}}
    #     encounter = session.get("encounter")

    if request.method == "POST":
        name = request.form.get("monster-select")
        result = re.search(r"^.* \((\w+|wotc-srd)\)", name)
        if result:
            slug = result[1]
            name = name.replace(f" ({slug})", "")
        else:
            return redirect("/enemies")
        enemy = pull_monster(name, slug)
        enemy = process_statblock(enemy)
    # dpr_total = 0
    # if encounter["party"]["count"] > 0:
    #     for enemy in enemies:
    #         if "dpr" in enemy.keys():
    #             dpr_total = round(dpr_total + (enemy["dpr"] * enemy["count"]), 2)

        return render_template("statblock.html", enemy=enemy)
    
@app.route("/removeenemy", methods=["GET", "POST"])
def removeenemy():
    if request.method == "POST":
        enemies = session.get("enemies")
        name = request.form.get("name")
        for enemy in enemies:
            if enemy["name"] == name:
                if enemy["count"] > 1:
                    enemy["count"] -= 1
                else:
                    enemies.remove(enemy)
                    if len(enemies) == 0:
                        session["encounter"] = {"party": {"count": 0}, "enemies": {"count": 0}}
        encounter = session.get("encounter")
        update_enemies(enemies, encounter)
        party = session.get("party")
        if len(party) > 0:
            update_party(party, encounter)
            if encounter["enemies"]["count"] > 0:
                for character in party:
                    ave_pc_dmg(character, encounter)
    return redirect("/enemies")

@app.route("/addenemy", methods=["GET", "POST"])
def addenemy():
    if request.method == "POST":
        enemies = session.get("enemies")
        name = request.form.get("name")
        for enemy in enemies:
            if enemy["name"] == name:
                enemy["count"] += 1
        encounter = session.get("encounter")
        update_enemies(enemies, encounter)
        party = session.get("party")
        if len(party) > 0:
            update_party(party, encounter)
            if encounter["enemies"]["count"] > 0:
                for character in party:
                    ave_pc_dmg(character, encounter)

    return redirect("/enemies")

@app.route("/removepc", methods=["GET", "POST"])
def removepc():
    if request.method == "POST":
        party = session.get("party")
        name = request.form.get("name")
        for character in party:
            if character["name"] == name:
                party.remove(character)
                if not party:
                    session["encounter"] = {"party": {"count": 0}, "enemies": {"count": 0}}
        encounter = session.get("encounter")
        update_party(party, encounter)
        enemies = session.get("enemies")
        if len(enemies) > 0:
            update_enemies(enemies, encounter)
            if encounter["party"]["count"] > 0:
                for enemy in enemies:
                    ave_enemy_dmg(enemy, encounter)

    return redirect("/party")

@app.route("/editpc", methods=["GET", "POST"])
def editpc():    
    if request.method == "POST":
        weapons = get_weapons()
        spells = get_spells()
        party = session.get("party")
        name = request.form.get("name")
        pc = {}
        for character in party:
            if character["name"] == name:
                temp = json.dumps(character)
                pc = json.loads(temp)
                party.remove(character)

        return render_template("editpc.html", weapons=weapons, spells=spells, party=party, pc=pc, encounter=encounter)
    return redirect("/party")


@app.route("/encounter", methods=["GET", "POST"])
def encounter():
    party = session.get("party")
    if party == None or len(party) == 0:
        return redirect("/party")
    enemies = session.get("enemies")
    if enemies == None or len(enemies) == 0:
        return redirect("/enemies")
    encounter = session.get("encounter")
    dpr_enemies = 0
    if encounter["party"]["count"] > 0:
        for enemy in enemies:
            dpr_enemies = round(dpr_enemies + (enemy["dpr"] * enemy["count"]), 2)
    dpr_party = 0
    if encounter["enemies"]["count"] > 0:
        for pc in party:
            if not pc["spellcaster"]:
                dpr_party = round(dpr_party + pc["dpr"]["base"], 2)
            else:
                dpr_party = round(dpr_party + pc["dpr"]["med"], 2)

    return render_template("encounter.html", party=party, enemies=enemies, encounter=encounter, dpr_enemies=dpr_enemies, dpr_party=dpr_party)

@app.route("/files", methods=["GET"])
def files():
    return render_template("files.html")

@app.route("/save", methods=["GET", "POST"])
def save():
    if request.method == "POST":
        party = session.get("party")
        enemies = session.get("enemies")
        encounter = session.get("encounter")
        save_type = request.form.get("save")
        if save_type == "party":
            with open(PATH + "static/files/download.party", "w") as output:
                json.dump(party, output, indent = 4)
            path = PATH + "static/files/download.party"
            return send_file(path, as_attachment=True)
        if save_type == "enemies":
            with open(PATH + "static/files/download.enemies", "w") as output:
                json.dump(enemies, output, indent = 4)
            path = PATH + "static/files/download.enemies"
            return send_file(path, as_attachment=True)
        if save_type == "encounter":
            download = {"party": party, "enemies": enemies, "encounter": encounter}
            with open(PATH + "static/files/download.encounter", "w") as output:
                json.dump(download, output, indent = 4)
            path = PATH + "static/files/download.encounter"
            return send_file(path, as_attachment=True)
    return redirect("/clean")

@app.route("/load", methods=["GET", "POST"])
def load():
    if request.method == "POST":
        party = session.get("party")
        enemies = session.get("enemies")
        encounter = session.get("encounter")
        file = request.files["file"]
        append = request.form.get("append")
        if file.filename == "":
            return redirect("/files")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            extension = filename[filename.find(".") + 1:]
            data = json.loads(file.read())
            if extension == "party":
                if append == None:
                    session["party"] = []
                    party = session.get("party")
                for pc in data:
                    if len(party) > 0:
                        for character in party:
                            if character["name"] == pc["name"]:
                                pc["name"] = pc["name"] + "*"
                    party.append(pc)
                update_party(party, encounter)
                if encounter["enemies"]["count"] > 0:
                    for pc in party:
                        ave_pc_dmg(pc, encounter)
                    for enemy in enemies:
                        ave_enemy_dmg(enemy, encounter)
                return redirect('/party')
            if extension == "enemies":
                if append == None:
                    session["enemies"] = []
                    enemies = session.get("enemies")
                for monster in data:
                    found = False
                    for enemy in enemies:
                        if enemy["name"] == monster["name"]:
                            enemy["count"] = enemy["count"] + monster["count"]
                            found = True
                    if not found:
                        enemies.append(monster)
                update_enemies(enemies, encounter)
                if encounter["party"]["count"] > 0:
                    for enemy in enemies:
                        ave_enemy_dmg(enemy, encounter)
                    for pc in party:
                        ave_pc_dmg(pc, encounter)
                return redirect("/enemies")
            if extension == "encounter":
                if append == None:
                    session["party"] = []
                    session["enemies"] = []
                    party = session.get("party")
                    enemies = session.get("enemies")
                if "party" in data.keys():
                    newparty = data["party"]
                if "enemies" in data.keys():
                    newenemies = data["enemies"]
                for pc in newparty:
                    for character in party:
                        if character["name"] == pc["name"]:
                            pc["name"] = pc["name"] + "*"
                    party.append(pc)
                for enemy in newenemies:
                    found = False
                    for monster in enemies:
                        if monster["name"] == enemy["name"]:
                            monster["count"] = monster["count"] + enemy["count"]
                            found = True
                    if not found:
                        enemies.append(enemy)
                update_party(party, encounter)
                update_enemies(enemies, encounter)
                if encounter["enemies"]["count"] > 0:
                    for pc in party:
                        ave_pc_dmg(pc, encounter)
                if encounter["party"]["count"] > 0:
                    for enemy in enemies:
                        ave_enemy_dmg(enemy, encounter)
                return redirect("/encounter")
    return redirect("/files")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
