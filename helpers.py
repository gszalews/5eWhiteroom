import csv
import json
import re
import requests
import string
import urllib.parse

PATH = ""
#PATH = "/home/gszalews/mysite/"

def align_actions(actions, attacks):
    for i in range(len(actions)):
        actions[i]["name"] = actions[i]["name"].lower()
    for i in range(len(actions)):
        # Align multiattack actions
        if "multiattack" in attacks[0].keys():
            for j in range(len(attacks[0]["attacks"])):
                # Catch generic multiattack names like "melee" and "ranged"
                if attacks[0]["attacks"][j]["name"] == "melee":
                    if actions[i]["desc"][:5] == "Melee":
                        attacks[0]["attacks"][j]["name"] = actions[i]["name"]
                        configure_action(actions[i], attacks[0]["attacks"][j])
                if attacks[0]["attacks"][j]["name"] == "ranged":
                    if actions[i]["desc"][:6] == "Ranged" or actions[i]["desc"][:15] == "Melee or Ranged":
                        attacks[0]["attacks"][j]["name"] = actions[i]["name"]
                        configure_action(actions[i], attacks[0]["attacks"][j])

                # Align regularly named actions in multiattack
                if "name" in attacks[0]["attacks"][j].keys():
                    temp_name = attacks[0]["attacks"][j]["name"]
                    if temp_name[len(temp_name) - 1] == "s":
                        temp_name = temp_name[:len(temp_name) - 1]
                        if actions[i]["name"] == temp_name:
                            attacks[0]["attacks"][j]["name"] = temp_name
                            configure_action(actions[i], attacks[0]["attacks"][j])
                    elif actions[i]["name"] == attacks[0]["attacks"][j]["name"]:
                        configure_action(actions[i], attacks[0]["attacks"][j])

        # Align all / rest of actions
        for j in range(len(attacks)):
            if "name" in attacks[j].keys():
                if actions[i]["name"] == attacks[j]["name"]:
                    configure_action(actions[i], attacks[j])

        # Remove duplicate multiattack actions from action list and remove those without attacks
        if "multiattack" in attacks[0].keys():
            pop_list = []
            for i in range(1, len(attacks)):
                    for j in range(len(attacks[0]["attacks"])):
                        if attacks[i]["name"] == attacks[0]["attacks"][j]["name"]:
                            pop_list.append(i)
            for i in range(len(pop_list)):
                attacks.pop(pop_list[i])


def ave_vri(dmg_type, encounter):
    imm = encounter["enemies"]["dmg_immunities"].keys()
    res = encounter["enemies"]["dmg_resistances"].keys()
    vuln = encounter["enemies"]["dmg_vulnerabilities"].keys()
    i_list = []
    r_list = []
    v_list = []
    for type in dmg_type:
        if type in imm:
            i_list.append(encounter["enemies"]["dmg_immunities"][type])
        if type in res:
            r_list.append(encounter["enemies"]["dmg_resistances"][type])
        if type in vuln:
            v_list.append(encounter["enemies"]["dmg_vulnerabilities"][type])
    immune = 0
    resistant = 0
    vulnerable = 0
    for type in i_list:
        immune = immune + type
    for type in r_list:
        resistant = resistant + type
    for type in v_list:
        vulnerable = vulnerable + type
    
    if len(i_list) > 0:
        immune = immune / len(i_list)
    if len(r_list) > 0:
        resistant = resistant / len(r_list)
    if len(v_list) > 0:
        vulnerable = vulnerable / len(v_list)

    final_vri = round(((immune + (resistant * .5)) - vulnerable), 2)

    if final_vri < 0:
        final_vri = round(1 + abs(final_vri), 2)
        return final_vri
    else:
        final_vri = round(1 - final_vri, 2) # inverse to get correct ratio for damage applicaton
        return final_vri


def ave_enemy_dmg(enemy, encounter):

    spellcaster = enemy["spellcaster"]
    multi_list = []
    dmg_list = []
    dmg = 0
    rchrg_dmg = 0
    ave_dmg = 0
    recharge = False
    legendary = enemy["legendary_actions"]
    leg_limit = 3
    leg_list = []
    try:
        ac = encounter["party"]["ac"]
    except:
        ac = 16
    # determine melee damage
    # look for multiattack and process multiattack damage
    if enemy["actions"][0]["name"] == "multiattack":
        multi = enemy["actions"][0]
        mcounter = multi["multiattack"]
        for attack in multi["attacks"]:
            if "attack_bonus" in attack.keys():
                dmg = enemy_attack(ac, attack["attack_bonus"], attack["ave_dmg"], attack["number"])
                if "save" in attack.keys():
                    ability = attack["save"].lower()
                    hiton = attack["save_dc"] - encounter["party"]["saves"][ability[:3]] - 1
                    odds = hiton / 20
                    if odds > 1:
                        odds = 1
                    if odds < 0:
                        odds = 0       
                    if attack["save_half"]:
                        dmg = (dmg * odds) + (dmg * 0.5 * (1 - odds))       
                multi_list.append(dmg)
                if legendary:
                    if attack["legendary"]:
                        leg_list.append(dmg)
                mcounter = mcounter - attack["number"]
                if mcounter <= 0:
                    break
    if multi_list:
        dmg_list.append(sum(multi_list))
    # handle non-multiattack actions
    for action in enemy["actions"]:
        if "ave_dmg" and "attack_bonus" in action.keys():
            if action["name"] != "multiattack":
                if "recharge" not in action["name"]:
                    print(enemy["name"])
                    print(action["name"])
                    print(action["attack_bonus"])
                    dmg = enemy_attack(ac, action["attack_bonus"], action["ave_dmg"], action["number"])
                    if "save" in action.keys():
                        ability = action["save"].lower()
                        hiton = action["save_dc"] - encounter["party"]["saves"][ability[:3]] - 1
                        odds = hiton / 20
                        if odds > 1:
                            odds = 1
                        if odds < 0:
                            odds = 0       
                        if action["save_half"]:
                            dmg = (dmg * odds) + (dmg * 0.5 * (1 - odds))
                    dmg_list.append(dmg)
                    if legendary:
                        if action["legendary"]:
                            leg_list.append(dmg)
                if "recharge" in action["name"]:
                    rchrg_dmg =  enemy_attack(ac, action["attack_bonus"], action["ave_dmg"], action["number"])
                    if encounter["party"]["count"] > 2:
                        rchrg_dmg = rchrg_dmg * (encounter["party"]["count"] / 2)
                    recharge = True        

    # find strongest "normal" attack
    if dmg_list:
        dmg_list.sort(reverse = True)
        ave_dmg = dmg_list[0]
    else:
        ave_dmg = dmg
    
    # average with spell damage if spellcaster
    if spellcaster:
        ave_spell_dmg(enemy, encounter)
        spell_dmg = enemy["spell_dpr"]["high"]
        ave_dmg = (ave_dmg + spell_dmg) / 2
    
    # add in legendary action damage
    if legendary:
        if len(leg_list) > 0:
            legendary_dmg = ((sum(leg_list) / len(leg_list)) * leg_limit)
            ave_dmg = ave_dmg + legendary_dmg

    # average in recharge attacks like breath weapons
    if recharge:
        if legendary:
            ave_dmg = (ave_dmg * 2 + (rchrg_dmg + legendary_dmg)) / 3
        else:
            ave_dmg = (ave_dmg * 2 + rchrg_dmg) / 3

    enemy["dpr"] = round(ave_dmg, 2)
    return

def ave_pc_dmg(character, encounter):
    finesse = {"Dagger", "Dart", "Rapier", "Scimitar", "Shortsword", "Whip"}
    weapons = ["weapon1", "weapon2"]
    character["w_dpr"] = 0
    spellcaster = character["spellcaster"]
    if character["weapon2"]["name"] == "none":
        weapons.remove("weapon2")

    for weapon in weapons:
        #establish variables
        base_dmg = 0
        dmg = 0
        xdmg = 0
        archery = 0
        abl = "str"
        mon_type = ""
        abl_string = "abl mod"
        lvl = character["level"]
        if character["weapon1"]["name"] == "none":
            character["weapon1"]["dpr_string"] = "none"
            break
        # determine best correct ability modifier
        if character[weapon]["name"] in finesse:
            if character["modifiers"]["dex"] > character["modifiers"]["str"]:
                abl = "dex"
        if "category" in character[weapon].keys():
            category = character[weapon]["category"]
            r = category.find("Ranged")
            if r >= 0:
                abl = "dex"
                if character["fighting_style"] == "archery" and "Ranged" in weapon["category"]:
                    archery = 2
        # determine odds
        modifier = int(character["modifiers"][abl]) + int(character["prof_bonus"]) + int(character[weapon]["magic_bonus"]) + archery
        hiton = 20 - (encounter["enemies"]["ac"] - modifier - 1) # -1 accounts for meeting ac, not having to "beat" ac
        if hiton <= 0:
            hiton = 1
        if hiton >= 20:
            hiton = 19
        odds = hiton / 20 

        # determine damage
        abl_mod = character["modifiers"][abl]
        magical = character[weapon]["magic_bonus"]

        # get basic weapon average damage
        if character[weapon]["name"] != "none":
            base_dmg = dice_average(character[weapon]["damage_dice"])
            if character["fighting_style"] == "dueling" and character["weapon2"]["name"] == "none":
                abl_mod = abl_mod + 2
                abl_string = abl_string + " + dueling"
            if character["fighting_style"] == "great_weapon" and character["weapon2"]["name"] == "none":
                if character[weapon]["damage_dice"] == "1d8":
                    abl_mod = abl_mod + 0.75
                if character[weapon]["damage_dice"] == "1d10":
                    abl_mod = abl_mod + 0.8
                if character[weapon]["damage_dice"] == "1d12":
                    abl_mod = abl_mod + 0.83
                if character[weapon]["damage_dice"] == "2d6":
                    abl_mod = abl_mod + 1.33
                abl_string = abl_string + " + gwf"
            if weapon == "weapon2" and character["fighting_style"] != "two_weapon":
                abl_mod = 0
                abl_string = "off hand"
            dmg = base_dmg + abl_mod + magical      
        # check for extra damage
        if character[weapon]["extra_damage_dice"] == "none":
            xdmg = 0
        else:
            xdmg = dice_average(character[weapon]["extra_damage_dice"])
        # check if vulnerable, resistant, or immune to damage types
        dmg_types = [character[weapon]["damage_type"]]
        if character[weapon]["magic_bonus"] < 1:
            dmg_types.append("nonmagical")
        if "extra_damage_type" in character[weapon].keys():
            xdmg_types = [character[weapon]["extra_damage_type"]]
        else:
            xdmg_types = []
        xdmg_vri = ave_vri(xdmg_types, encounter)
        dmg_vri = ave_vri(dmg_types, encounter)

        if "extra_damage_monster_type" in character[weapon].keys():
            mon_type = character[weapon]["extra_damage_monster_type"]

        if mon_type in encounter["enemies"]["types"].keys():
            mon_ratio = encounter["enemies"]["types"][mon_type] / encounter["enemies"]["count"]
            xdmg = round(xdmg * mon_ratio, 2)
        
        final_dmg = (odds * ((dmg * dmg_vri) + (xdmg * xdmg_vri))) + (character[weapon]["crit"] * (base_dmg + xdmg))
        final_dmg = round(final_dmg, 2)

        if weapon == "weapon1":
            character["w_dpr"] = round(final_dmg, 2)

        # apply sneak attack if rogue
        rogue_str = ""
        if character["class"] == "rogue" and weapon == "weapon1":
            sneak_attack = round((round(lvl / 2) * 3.5) * 0.66, 2)
            character["w_dpr"] = round(character["w_dpr"]  + sneak_attack, 2)
            rogue_str = f" + sneak attack: {sneak_attack} = (0.66 * ((lvl){lvl} / 2) * 3.5)"

        if weapon == "weapon2" and character["w_dpr"]:
            character["w_dpr"] = round(character["w_dpr"] + final_dmg, 2)


        dmg_str = str(final_dmg)
        crit = character[weapon]["crit"]
        dpr_string = f"{dmg_str} = (odds){odds} * (((base dmg){base_dmg} + ({abl_string}){abl_mod} + (magical){magical} * (vri){dmg_vri}) + ((xdmg){xdmg} * (xmdg vri){xdmg_vri}) + ((crit %){crit} * ((base dmg){base_dmg} + (xdmg){xdmg}) {rogue_str}"
        character[weapon]["dpr_string"] = dpr_string
    character["dpr"] = {"base": 0, "med": 0, "high": 0}
    if character["caster_type"] != "none":
        ave_spell_dmg(character, encounter)
        if character["caster_type"] == "half_m":
            character["dpr"]["base"] = round((character["w_dpr"] * 2 + character["spell_dpr"]["low"]) / 3, 2)
            character["dpr"]["med"] = round((character["w_dpr"] * 2 + character["spell_dpr"]["med"]) / 3, 2)
            character["dpr"]["high"] = round((character["w_dpr"] * 2 + character["spell_dpr"]["high"]) / 3, 2)
        elif character["caster_type"] == "half_s":
            character["dpr"]["base"] = round((character["spell_dpr"]["low"] * 2 + character["w_dpr"]) / 3, 2)
            character["dpr"]["med"] = round((character["spell_dpr"]["med"] * 2 + character["w_dpr"]) / 3, 2)
            character["dpr"]["high"] = round((character["spell_dpr"]["high"] * 2 + character["w_dpr"]) / 3, 2)
        else:
            character["dpr"]["base"] = character["spell_dpr"]["low"]
            character["dpr"]["med"] = character["spell_dpr"]["med"]
            character["dpr"]["high"] = character["spell_dpr"]["high"]
    else:
        character["dpr"]["base"] = round(character["w_dpr"], 2)
        character["dpr"]["med"] = round(character["w_dpr"] * 1.3, 2)
        character["dpr"]["high"] = round(character["w_dpr"] * 1.8, 2)
    return


def ave_spell_dmg(character, encounter):
    if "slug" in character.keys():
        group = encounter["party"]
    else:
        group = encounter["enemies"]
    if character["spellcaster"] != True:
        return
    spell_abl = character["spell_ability"]
    dc = character["spell_dc"]
    att = character["spell_attack"]
    spellbook = character["spells"]
    for spell in spellbook:
        dmg_str = "base dmg"
        odds_str = ""
        spellsave = False
        aoe = False
        aoe_str = ""
        spatt = False
        half = False
        half_str = ""
        inc_str = ""
        keys = spell.keys()
        if "aoe" in keys:
            aoe = spell["aoe"]
        if "attack" in keys:
            spatt = spell["attack"]
        if "save_half" in keys:
            half = spell["save_half"]
        dmg = 0
        # if spell adds spell attack modifier SAM to damage
        sam = spell["damage"].find("+SAM")
        sam_dmg = 0
        if sam >= 0:
            if group == encounter["enemies"]:
                sam_dmg = character["modifiers"][spell_abl]
            else:
                sam_dmg = get_mod(character[spell_abl])
            dice = spell["damage"][:sam]
        else:
            dice = spell["damage"]
        
        # set average damage for the spell
        base_dmg = dice_average(dice)
        dmg = sam_dmg + base_dmg
        if sam_dmg > 0:
            dmg_str = dmg_str + " + SAM"
        # calculate odds if save is required
        if spell["save"] != "None":
            save = spell["save"][:3].lower()
            grp_save = group["saves"][save]
            hiton = dc - grp_save - 1 # -1 meets instead of beats spell dc
            odds_str = f"((dc){dc} - (save mod){grp_save} - 1) / 20"
            odds = hiton / 20 # player odds of enemy failing saving throw
            spellsave = True

        # calculate odds if spell attack is required
        elif spell["save"] == "None" and spatt == True:
            ac = group["ac"]
            hiton = 20 - (ac - att - 1)
            odds = hiton / 20
            odds_str = f"(20 - ((ac){ac} - (sp attk mod){att} - 1)) / 20"
        
        elif spell["save"] == "None" and spatt == False:
            odds = 1

        if odds > 1:
            odds = 1
        if odds < 0:
            odds = 0
        
        if spellsave == True:
            if half == True:
                half_chance = round(1 - odds, 2)
                dmg = (dmg * odds) + (dmg * 0.5 * half_chance)
                half_str = f" + ({dmg_str}){base_dmg} * 0.5 * ({half_chance}) "
            else:
                dmg = (dmg * odds)
        else:
            dmg = dmg * odds
        count = group["count"]

        # adjust damage for area of effect
        if aoe == True and count > 2:
            dmg = dmg * (count  / 2)
            aoe_str = f"aoe multiplier: {count / 2}"

        # check for cantrip increase
        if spell["increase"] == "TRUE":
            level = character["level"]
            if level >= 17:
                inc_str = f"({dmg} * 4)"
                dmg = dmg * 4
            elif level >= 11:
                inc_str = f"({dmg} * 3)"
                dmg = dmg * 3
            elif level >= 5:
                inc_str = f"({dmg} * 2)"
                dmg = dmg * 2

        
        # check for vulnerability, resistance, and immunity
        dt = spell["type"].replace(",", "")
        dt = dt.lower()
        dmg_type = dt.split()
        vri = ave_vri(dmg_type, encounter)
        dmg = round(dmg * vri, 2)
        spell["dpr"] = dmg
        spell["dpr_string"] = f"{dmg} " + inc_str + f"= ({dmg_str}){base_dmg} * (odds){odds}" + half_str + aoe_str
        spell["odds_string"] = f"{odds} = " + odds_str

    low = 0
    med = 0
    high = 0
    size = len(spellbook)
    dmg_list = []
    for spell in spellbook:
        dmg_list.append(spell["dpr"])
    dmg_list.sort(reverse = True)
    if size > 0:
        if "slug" in character.keys():
            low = dmg_list[len(dmg_list) - 1]
        else:
            low = spellbook[0]["dpr"]
        med = sum(dmg_list) / len(dmg_list)
        if size >= 3 :
            high = (dmg_list[0] + dmg_list[1])/ 2
        else:
            high = dmg_list[0]
    
    character["spell_dpr"] = {"low": round(low, 2), "med": round(med, 2), "high": round(high, 2)}
    return


# take in full enemy action and configured enemy action (what will be written into json) and get the attack bonus,
# average the damage on a successful hit, and find any saving throw that players need to make
def configure_action(full_action, conf_action):
    desc = full_action["desc"]
    # Find attack roll modifier
    hit = get_hit(desc)
    if hit is not None:
        conf_action["attack_bonus"] = hit
    # find average damage
    dmg = get_damage(desc)
    damage = 0
    if dmg is not None:
        for d in dmg:
            damage += d["dmg"]
        conf_action["ave_dmg"] = damage
    #find the saving throw if needed for a given action
    save = get_save(desc)
    if save is not None:
        conf_action["save"] = save["ability"]
        conf_action["save_dc"] = save["dc"]
        conf_action["save_half"] = save["save_half"]

    return conf_action


def dice_average(dmg_dice):
    damage = 0
    samloc = dmg_dice.find("+SAM")
    if samloc >= 0:
        dmg_dice = dmg_dice[:samloc]
    if dmg_dice == "none":
        return damage
    if dmg_dice[0] == "(":
        dmg_dice = dmg_dice[1:len(dmg_dice) - 2]
    for punct in string.punctuation:
        if punct != "+":
            dmg_dice = dmg_dice.replace(punct, "")
    dice_sets = []
    if "+" in dmg_dice:
        j = 0
        for i in range(len(dmg_dice)):
            if dmg_dice[i] == "+":
                dice_sets.append(dmg_dice[j:i])
                j = i + 1
                dice_sets.append(dmg_dice[j:])
    else:
        dice_sets.append(dmg_dice)
    for dice in dice_sets:
        if "d" in dice:
            d = dice.find("d")
            dice_times = int(dice[:d])
            dmg_die = int(dice[d + 1:])
            damage = dice_times * ((dmg_die / 2) + 0.5)
        else:
            damage = damage + int(dice)
    return damage


# function for doing basic monster damage math
def enemy_attack(ac, bonus, ave_dmg, number):
    hiton = 20 - (ac - bonus - 1) # -1 accounts for meeting ac, not having to "beat" ac
    if hiton <= 0:
        hiton = 1
    if hiton >= 20:
        hiton = 19
    odds = hiton / 20
    dmg = odds * ave_dmg * number
    return dmg
   

def get_type(desc):
    # Determine type of attack
    if not desc or desc == None:
        return None
    type_results = re.search(r"^((?:(?:Melee)|(?:Ranged))|(?:Melee or Ranged)) Weapon Attack:", desc)
    if type_results:
        return (type_results.group(1))
    else:
        return ("Spell or Ability")


def get_hit(desc):
    # Extract "to hit" value from desc
    if not desc or desc == None:
        return None
    hit_results = re.search(r"^.*\+(\d+) to hit.*$", desc)
    if hit_results:
        return (int(hit_results.group(1)))
    else:
        return None


def get_damage(desc):
    # Find damage done by action
    if not desc or desc == None:
        return None
    dmg = []
    dmg_results = re.findall(r" (\d+) \((.*?)\) (\b\w*) damage", desc)
    if dmg_results:
        for d in range(len(dmg_results)):
            dmg.append({"dmg": int(dmg_results[d][0]), "dice": dmg_results[d][1], "type": dmg_results[d][2]})
    else:
        dmg = None
    return dmg


def get_save(desc):
    # Find if saving throw needed and details
    half = False
    if not desc or desc == None:
        return None
    if "or half as much damage" in desc:
        half = True
    save_results = re.search(r"^.*DC (\d+) (\b\w*) saving throw.*$", desc)
    if save_results:
        return {"dc": int(save_results.group(1)), "ability": save_results.group(2), "save_half": half}
    else:
        return None
    

# Return modifier for a given score
def get_mod(score):
    return score // 2 - 5


def get_xp(cr):
    crxp = {}
    with open(PATH + 'static/files/cr_xp.csv', 'r', encoding='utf-8-sig') as csvfile:
        xpreader = csv.reader(csvfile)
        for row in xpreader:
            crxp[str(row[0])] = int(row[1])
    return crxp[cr]

def get_enemy(name, slug):
    spell_dict = get_spells()
    enemy = pull_monster(name, slug)
    process_enemy(enemy)
    return enemy

def process_enemy(enemy):
    if enemy:
        if "hit_points" not in enemy.keys():
            try:
                enemy["hit_points"] = process_hptext(enemy["hpText"])
            except KeyError:
                pass
        processed_enemy = process_actions(enemy)
        enemy["actions"] = processed_enemy["actions"]
        enemy["legendary_actions"] = processed_enemy["legendary_actions"]
        hits = 0
        if enemy["actions"][0]["name"] == "multiattack":
            hits = hits + enemy["actions"][0]["multiattack"]
        else:
            hits += 1
        if enemy["legendary_actions"]:
            hits = hits + 3
        enemy["attacks"] = hits
        enemy["spellcaster"] = False
        if "spell_list" not in enemy.keys():
            enemy["spell_list"] = ""
        if len(enemy["spell_list"]) > 0:
            # convert spell api calls into spell data w/ function
            spellbook = process_spell_list(spell_dict, enemy["spell_list"])
            enemy["spells"] = spellbook
            desc = ""
            # find spellcasting ability description in enemy data
            for i in range(len(enemy["special_abilities"])):
                if enemy["special_abilities"][i]["name"] == "Spellcasting":
                    enemy["spellcasting"] = True
                    desc = enemy["special_abilities"][i]["desc"]
                    break
            # analyze description to obtain key stats, if errors -> set to defaults
            if len(desc) > 0:
                desc = desc.lower()
                desc_split = desc.split(".")
                ability = {"intelligence", "wisdom", "charisma"}
                brake = False
                for sentence in desc_split:
                    for abl in ability:
                        if f"spellcasting ability is {abl}" in sentence:
                            enemy["spell_ability"] = abl
                    loc = sentence.find("spell save dc")
                    if loc >= 0:
                        stat_search = sentence[loc:].split()
                        dc = stat_search[3]
                        dc = dc.replace(",", "")
                        try:
                            enemy["spell_dc"] = int(dc)
                        except:
                            enemy["spell_dc"] = 16
                        if "+" in stat_search[4]:
                            attack = stat_search[4]
                            attack = attack.replace("+", "")
                            try:
                                enemy["spell_attack"] = int(attack)
                            except:
                                enemy["spell_attack"] = 8
                            break
    return enemy


def get_prof(level):
    lvl = int(level)
    prof_bonus = 0
    if lvl < 5:
        prof_bonus = 2
    elif lvl < 9:
        prof_bonus = 3
    elif lvl < 13:
        prof_bonus = 4
    elif lvl < 17:
        prof_bonus = 5
    elif lvl > 16:
        prof_bonus = 6
    return prof_bonus


def get_spells():
    spells = []
    with open(PATH + 'static/files/spells.csv', 'r', encoding='utf-8-sig') as csvfile:
        spell_info = csv.DictReader(csvfile)
        for spell in spell_info:
            spells.append(spell)
    return spells


def get_weapons():
    url = "https://api.open5e.com/weapons/?document__slug=wotc-srd"
    response = requests.get(url)
    weapons = response.json()
    v_weapons = []
    for weapon in weapons["results"]:
        if weapon["properties"] != None:
            for prop in weapon["properties"]:
                vers_loc = prop.find("versatile")
                if vers_loc >= 0:
                    start = prop.find("(")
                    end = prop.find(")")
                    v_dmg = prop[start + 1: end]
                    temp_weapon = json.loads(json.dumps(weapon, indent = 4))
                    temp_weapon["name"] = "Versatile " + weapon["name"]
                    temp_weapon["damage_dice"] = v_dmg
                    v_weapons.append(temp_weapon)
    for weapon in v_weapons:
        weapons["results"].append(weapon)
        weapons["count"] += 1
    return weapons


def parse_dmg_types(string):
    semi_loc = string.find(";")
    if semi_loc >= 0:
        split_string = string.split(";")
        dmg_types = split_string[0].split(", ")
        if "silvered" or "nonsilver" in split_string[1]:
            dmg_types.append("nonmagical")
            dmg_types.append("nonsilvered")
        elif "adamantine" in split_string[1]:
            dmg_types.append("nonmagical")
            dmg_types.append("nonadamantine")
        else:
            dmg_types.append("nonmagical")
    else:
        dmg_types = string.split(", ")
    
    return dmg_types


def process_actions(enemy):
    processed_enemy = {}
    attacks = {}
    # List of actions from enemy API
    action_names = []
    # List of actions for processed enemy
    attack_list = []
    # List of actions in multiattack to remove from attack list
    pop_list = []
    # Create action list to use for multiattack and dpr analysis
    for i in range(len(enemy["actions"])):
        action_names.append(enemy["actions"][i]["name"].lower())

    # Handle multiattacks if available
    if "multiattack" in action_names:
        action_names.pop(action_names.index("multiattack"))
        multi = enemy["actions"][0]["desc"]
        for i in string.punctuation:
            multi = multi.replace(i, "")
        multi_split = multi.split()

        # Process multiattack
        multiattacks = process_multiattack(multi_split, action_names)
        attack_list.append(multiattacks)

        # Remove multiattack actions from main action list
        for i in range(len(action_names)):
            for j in range(len(attack_list[0]["attacks"])):
                temp_name = attack_list[0]["attacks"][j]["name"]
                if temp_name[len(temp_name) - 1] == "s":
                    temp_name = temp_name[:len(temp_name) - 1]
                    if action_names[i] == temp_name:
                        pop_list.append(action_names[i])
                if action_names[i] == attack_list[0]["attacks"][j]["name"]:
                    pop_list.append(action_names[i])
        for i in range(len(pop_list)):
            action_names.remove(pop_list[i])

    # Add actions to processed enemy
    for i in range(len(action_names)):
        attack_list.append({"name": action_names[i], "number": 1})
    processed_enemy["actions"] = attack_list
    align_actions(enemy["actions"], processed_enemy["actions"])
    # Process any legendary actions
    if "legendary_actions" not in enemy.keys():
        enemy["legendary_actions"] = None
    if enemy["legendary_actions"] is not None:
        process_legendary(enemy["legendary_actions"], processed_enemy["actions"])
        processed_enemy["legendary_actions"] = True
    else:
        processed_enemy["legendary_actions"] = False
    return processed_enemy


# find legendary actions that correspond to attack actions listed previously
def process_legendary(leg_actions, actions):
    legendary = []
    acts = []
    # search through multiattack actions for corresponding legendary action
    if actions[0]["name"] == "multiattack":
        for i in range(len(actions[0]["attacks"])):
            for j in range(len(leg_actions)):
                lgnd_name = leg_actions[j]["name"].lower()
                if " attack" in lgnd_name:
                    lgnd_name.replace(" attack", "")
                lgnd_desc = leg_actions[j]["desc"].lower()
                att_name = actions[0]["attacks"][i]["name"]
                if att_name in lgnd_desc or att_name == lgnd_name:
                    actions[0]["attacks"][i]["legendary"] = True
                    break
                else:
                    actions[0]["attacks"][i]["legendary"] = False
    # if actions are not in multiattack or there is no multiattack, look through list of "regular" actions
    for i in range(len(actions)):
        if actions[i]["name"] != "multiattack":
            for j in range(len(leg_actions)):
                lgnd_name = leg_actions[j]["name"].lower()
                if " attack" in lgnd_name:
                    lgnd_name.replace(" attack", "")
                lgnd_desc = leg_actions[j]["desc"].lower()
                legendary.append(lgnd_name)
                att_name = actions[i]["name"]
                acts.append(att_name)
                if att_name in lgnd_desc or att_name == lgnd_name:
                    actions[i]["legendary"] = True
                    break
                else:
                    actions[i]["legendary"] = False
    # list of attack names can be processed as increased number of specified attacks when calculating damage
    return




def process_multiattack(multi_split, action_names):
    # Set keywords to look for in multi_split strig
    attack_words = ["attacks", "attacks.", "attacks:"]
    multi_words = ["one", "once", "two", "twice", "three", "four", "five"]
    multi_words_num = [1, 1, 2, 2, 3, 4, 5]
    pop_words = ["with", "its", "and", "to"]
    # Set variables
    attacks_pos = 0
    attacks = 0
    action_name = "melee"
    multiattack = {"name": "multiattack", "multiattack": 0}
    attack_list = []
    action_list_temp = []
    for i in range(len(action_names)):
        action_list_temp.append(action_names[i])

    # Search for number of attacks being made
    for i in range(len(multi_split)):
        for j in range(len(attack_words)):
            if attack_words[j] == multi_split[i]:
                attacks_pos = i
                break
        if attacks_pos > 0:
            break

    # If number of number of attacks found turn the number into an int using keyword lists
    attack_split = multi_split[:attacks_pos]
    for i in range(len(attack_split)):
        for j in range(len(multi_words)):
            if multi_words[j] == multi_split[i]:
                number_word = multi_split[i]
                attacks = multi_words_num[multi_words.index(number_word)]

    # Prep action list for more options and lowercase to match action_split
    for i in range(len(action_list_temp)):
        temp = action_list_temp[i].lower()
        action_list_temp[i] = temp
        action_list_temp.append(action_list_temp[i] + "s")
        action_list_temp.append(action_list_temp[i] + "es")
    multiattack["multiattack"] = attacks

    # If there is only one multiattack option get the name and return
    if len(multi_split[attacks_pos + 1:]) == 0 or attacks_pos == 0:
        for i in range(len(action_list_temp)):
            if action_list_temp[i] in attack_split:
                action_name = action_list_temp[i]
        if multiattack["multiattack"] == 0:
            multiattack["multiattack"] = 1
        if attacks == 0:
            attacks = 1
        attack_list.append({"name": action_name, "number": attacks})
        multiattack["attacks"] = attack_list
        return multiattack

    # For more than one multiattack option, cut string for naming and counting
    # specific attacks
    action_split = multi_split[attacks_pos +1:]

    # Get positions of counting words to split attack phrases
    while len(action_split) > 0:
        multi_count_pos = []
        for i in range(len(action_split)):
            for j in range(len(multi_words)):
                if multi_words[j] in action_split[i]:
                    multi_count_pos.append(i)
            if len(multi_count_pos) == 2:
                break

        # Use position counts to examine single attack-type substring
        # If there are no more words found
        if len(multi_count_pos) == 0:
            action_split.clear()
            break

        # If there is only one term left
        elif len(multi_count_pos) == 1:
            attack_substring = action_split[:]

        # If there are two or more terms
        else:
            attack_substring = action_split[:multi_count_pos[1]]
            temp_split = action_split[multi_count_pos[1]:]
            action_split = temp_split

        # Remove typical extra words
        for i in range(len(pop_words)):
            if pop_words[i] in attack_substring:
                attack_substring.remove(pop_words[i])

        # How many attacks are being made
        if len(attack_substring) > 0:
            if attack_substring[0] in multi_words:
                attack_count = multi_words_num[multi_words.index(attack_substring[0])]
            else:
                attack_count = 1
        else:
            action_split.clear()

        # Get name of attack
        if len(multi_count_pos) == 1:
            action_split.clear()
        if len(attack_substring) > 1:
            attack_name = attack_substring[1]
        else:
            attack_name = "N/A"

        # Add name and number to attacks
        attack_list.append({"name": attack_name, "number": attack_count})

    multiattack["attacks"] = attack_list
    return multiattack


def process_pc_spells(character):
    if character["spellcaster"] != True:
        return
    spell_abilities = {"artificer": "int", "bard": "cha", "cleric": "wis", "druid": "wis", "fighter": "int", "monk": "wis",
                        "paladin": "cha", "ranger": "wis", "rogue": "int", "sorcerer": "cha", "warlock": "cha", "wizard": "int"}
    spell_abl = spell_abilities[character["class"]]
    character["spell_ability"] = spell_abl
    dc = 8 + character["modifiers"][spell_abl] + character["prof_bonus"]
    character["spell_dc"] = dc
    att = dc - 8
    character["spell_attack"] = att
    spellbook = character["spells"]
    for spell in spellbook:
        #look up spell in open5e api
        name = spell["name"]
        url = f"https://api.open5e.com/spells/?search={urllib.parse.quote(name)}"
        response = requests.get(url)
        srdjson = response.json()
        # handle multiple types of return from api - more than one spell, single spell, or no spell
        if srdjson["count"] > 1:
            for entry in srdjson["results"]:
                if entry["name"] == name:
                    srdspell = entry
        elif srdjson["count"] == 1:
            srdspell = srdjson["results"][0]
        elif srdjson["count"] == 0:
            srdspell = {"desc": ""}
        # set variables for determining spell type and outcome
        spatt = False
        half = False
        desc = srdspell["desc"].lower()
        loc = desc.find("ranged spell attack")
        if loc >= 0:
            spatt = True
        loc2 = desc.find("half as much damage on a successful")
        if loc2 >= 0:
            half = True
        area_of_effect = ["circle", "cone", "cube", "cylinder", "line", "sphere", "wall"]
        aoe = False
        # Look for area of effect in spell
        if "-foot" or "you create a wall" in desc:
            for area in area_of_effect:
                if area in desc:
                    aoe = True
                    break
        spell["aoe"] = aoe
        spell["attack"] = spatt
        spell["save_half"] = half
    return

def process_spell_list(spells_dict, spell_list):
    spellbook = []
    area_of_effect = ["circle", "cone", "cube", "cylinder", "line", "sphere", "wall"]
    for url in spell_list:
        response = requests.get(url)
        item = response.json()
        desc = item["desc"].lower()
        aoe = False
        spatt = False
        half = False
        # Look for area of effect in spell
        if "-foot" or "you create a wall" in desc:
            for area in area_of_effect:
                if area in desc:
                    aoe = True
                    break
        # Look for melee / ranged spell attack
        if "melee spell attack" or "ranged spell attack" in desc:
            spatt = True
        # Look for half damage in spell save
        if "half as much damage on a successful" in desc:
            half = True
        # Load spellbook info from csv
        for spell in spells_dict:
            if item["name"] == spell["name"]:
                spell["aoe"] = aoe
                spell["attack"] = spatt
                spell["save_half"] = half
                spellbook.append(spell)

    return spellbook

def process_statblock(enemy):
    enemy["speed_str"] = statblock_speed(enemy["speed"])
    enemy["skills_str"] = statblock_skills(enemy["skills"])
    enemy["save_str"] = statblock_saves(enemy)
    enemy["xp"] = get_xp(enemy["challenge_rating"])
    enemy["int_stats"] = statblock_stats(enemy)
    for action in enemy["actions"]:
        action["desc"] = statblock_action(action["desc"])
    return enemy


def statblock_action(desc):
    # Add italics to action descriptions
        results = re.search(r"(\w+:)(\w+)(Hit:)(\w+)", desc)
        if results:
            return ("<i>" + results[1] + "</i>" + results[2] + "<i>" + results[3] + "</i>" + results[4])
        else:
            return desc


def statblock_saves(enemy):
    # Generate saveing throw string
    save_list = ["strength_save", "dexterity_save", "constitution_save", "intelligence_save", "wisdom_save", "charisma_save"]
    save_str = ""
    counter = 0
    for save in save_list:
        if enemy[save] is not None:
            if counter > 0:
                comma = ", "
            else:
                comma = ""
            stat = save[:3].capitalize()
            save_str = save_str + comma + stat + " +" + str(enemy[save])
            counter += 1
    return save_str


def statblock_skills(skills):
    #Generate skills string for statblock
    skills_str = ""
    counter = 0
    for key in skills.keys():
        if counter > 0:
            comma = ", "
        else:
            comma = ""
        skills_str = skills_str + comma + key.capitalize() + " +" + str(skills[key])
        counter += 1
    return skills_str


def statblock_speed(speed):
    # Generate speed string for statblock
    speed_str = ""
    counter = 0
    for key in speed.keys():
        if counter > 0:
            comma = ", "
        else:
            comma = ""
        speed_str = speed_str + comma + key.capitalize() + " " + str(speed[key]) + " ft."
        counter += 1
    return speed_str


def statblock_stats(enemy):
    int_stats = {"strength":int(enemy["strength"]), "dexterity":int(enemy["dexterity"]), "constitution":int(enemy["constitution"]), 
                 "intelligence":int(enemy["intelligence"]), "wisdom":int(enemy["wisdom"]), "charisma":int(enemy["charisma"])}
    return int_stats


def pull_monster(name, slug):
    url = f"https://api.open5e.com/monsters/?search={urllib.parse.quote(name)}&document__slug={urllib.parse.quote(slug)}"
    response = requests.get(url)
    enemy = response.json()
    if enemy["count"] == 1:
        return enemy["results"][0]
    else:
        for i in range(len(enemy["results"])):
            enemy_name = enemy["results"][i]["name"]
            if enemy_name == name:
                return enemy["results"][i]
    return


def update_enemies(enemies, encounter):
    # read csv to link cr rating to experience points
    damge_types = ["acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
                    "poison", "psychic", "radiant", "slashing", "thunder", "nonmagical", "nonsilvered", "nonadamantine"]
    # read csv to link encounter multiplier to enemy count
    enc_multiply = {}
    with open(PATH + 'static/files/encounter_multipliers.csv', 'r', encoding='utf-8-sig') as csvfile:
        multiplyreader = csv.reader(csvfile)
        for row in multiplyreader:
            enc_multiply[str(row[0])] = float(row[1])

    if len(enemies) > 0:
        total_hp = 0
        num = 0
        group_ac = 0
        hits = 0
        total_xp = 0
        enc_xp = 0
        types = {}
        dmg_resist = {}
        dmg_immune = {}
        dmg_vuln = {}
        saves = {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0}
        for enemy in enemies:
            # add monster types to a dictionary for count
            if enemy["type"] in types.keys():
                types[enemy["type"]] = types[enemy["type"]] + enemy["count"]
            else:
                types[enemy["type"]] = enemy["count"]
            # handle damage resistance, immunity, and vulnerability
            if "damage_resistances" not in enemy.keys():
                enemy["damage_resistances"] = ""
            if len(enemy["damage_resistances"]) > 0:
                dmg_res = parse_dmg_types(enemy["damage_resistances"])
                for dmg_type in dmg_res:
                    if dmg_type not in dmg_resist.keys():
                        dmg_resist[dmg_type] = enemy["count"] * enemy["hit_points"]
                    else:
                        dmg_resist[dmg_type] = dmg_resist[dmg_type] + (enemy["count"] * enemy["hit_points"])

            if "damage_immunities" not in enemy.keys():
                enemy["damage_immunities"] = ""
            if len(enemy["damage_immunities"]) > 0:
                dmg_imm = parse_dmg_types(enemy["damage_immunities"])
                for dmg_type in dmg_imm:
                    if dmg_type not in dmg_immune.keys():
                        dmg_immune[dmg_type] = enemy["count"] * enemy["hit_points"]
                    else:
                        dmg_immune[dmg_type] = dmg_immune[dmg_type] + (enemy["count"] * enemy["hit_points"])

            if "damage_vulnerabilities" not in enemy.keys():
                enemy["damage_vulnerabilities"] = ""            
            if len(enemy["damage_vulnerabilities"]) > 0:
                dmg_vul = parse_dmg_types(enemy["damage_vulnerabilities"])
                for dmg_type in dmg_vul:
                    if dmg_type not in dmg_vuln.keys():
                        dmg_vuln[dmg_type] = enemy["count"] * enemy["hit_points"]
                    else:
                        dmg_vuln[dmg_type] = dmg_vuln[dmg_type] + (enemy["count"] * enemy["hit_points"])

            # handle basic stats
            total_hp = total_hp + (enemy["hit_points"] * enemy["count"])
            group_ac = group_ac + (enemy["armor_class"] * enemy["hit_points"] * enemy["count"])
            hits = hits + (enemy["attacks"] * enemy["count"])
            total_xp = total_xp + (get_xp(enemy["challenge_rating"]) * enemy["count"])
            num = num + enemy["count"]

            # handle saving throws
            if enemy["strength_save"] == None:
                saves["str"] = saves["str"] + (get_mod(enemy["strength"]) * enemy["hit_points"])
            else:
                saves["str"] = saves["str"] + (enemy["strength_save"] * enemy["hit_points"])
            if enemy["dexterity_save"] == None:
                saves["dex"] = saves["dex"] + (get_mod(enemy["dexterity"]) * enemy["hit_points"])
            else:
                saves["dex"] = saves["dex"] + (enemy["dexterity_save"] * enemy["hit_points"])
            if enemy["constitution_save"] == None:
                saves["con"] = saves["con"] + (get_mod(enemy["constitution"]) * enemy["hit_points"])
            else:
                saves["con"] = saves["con"] + (enemy["constitution_save"] * enemy["hit_points"])
            if enemy["intelligence_save"] == None:
                saves["int"] = saves["int"] + (get_mod(enemy["intelligence"]) * enemy["hit_points"])
            else:
                saves["int"] = saves["int"] + (enemy["intelligence_save"] * enemy["hit_points"])
            if enemy["wisdom_save"] == None:
                saves["wis"] = saves["wis"] + (get_mod(enemy["wisdom"]) * enemy["hit_points"])
            else:
                saves["wis"] = saves["wis"] + (enemy["wisdom_save"] * enemy["hit_points"])
            if enemy["charisma_save"] == None:
                saves["cha"] = saves["cha"] + (get_mod(enemy["charisma"]) * enemy["hit_points"])
            else:
                saves["cha"] = saves["cha"] + (enemy["charisma_save"] * enemy["hit_points"])

        # some basic group stats
        encounter["enemies"]["hp"] = total_hp
        encounter["enemies"]["count"] = num
        encounter["enemies"]["attacks"] = hits
        encounter["enemies"]["xp"] = total_xp
        encounter["enemies"]["types"] = types

        # determine encounter multiplier based on monster count
        if num <= 15:
            enc_xp = enc_multiply[str(num)] * total_xp
        elif num > 15:
            enc_xp = enc_multiply["15"] * total_xp
        encounter["enemies"]["enc_xp"] = enc_xp

        # vulnerabilities, resistances, and immunities are given an overall percentage weighted by hit points
        if dmg_vuln:
            for dmg_type in dmg_vuln:
                dmg_vuln[dmg_type] = round(dmg_vuln[dmg_type] / total_hp, 2)
        encounter["enemies"]["dmg_vulnerabilities"] = dmg_vuln
        if dmg_resist:
            for dmg_type in dmg_resist:
                dmg_resist[dmg_type] = round(dmg_resist[dmg_type] / total_hp, 2)
        encounter["enemies"]["dmg_resistances"] = dmg_resist
        if dmg_immune:
            for dmg_type in dmg_immune:
                dmg_immune[dmg_type] = round(dmg_immune[dmg_type] / total_hp, 2)
        encounter["enemies"]["dmg_immunities"] = dmg_immune

        # average saveing throws weighted by hit points
        for key in saves.keys():
            saves[key] = int(round(saves[key] / total_hp))
        encounter["enemies"]["saves"] = saves
        #enemy group ac is weighted by hit points
        if total_hp > 0:
            encounter["enemies"]["ac"] = int(round(group_ac / total_hp))
        # adjust encounter multiplier based on party size
        if "thresholds" in encounter["party"]:
            if encounter["party"]["count"] < 3:
                if num < 15:
                    enc_xp = enc_xp + (total_xp * .5)
                else:
                    enc_xp = enc_xp + total_xp
                encounter["enemies"]["enc_xp"] = enc_xp
            if encounter["party"]["count"] > 5:
                if num < 15:
                    enc_xp = enc_xp - (total_xp * .5)
                else:
                    enc_xp = enc_xp - total_xp
            # find encounter threshold based on party level
            i = 0
            for threshold in encounter["party"]["thresholds"]:
                if threshold > enc_xp:
                    break
                else:
                    i += 1
            enc_dif = ["Trivial", "Easy", "Medium", "Hard", "Deadly"]
            encounter["enemies"]["difficulty"] = enc_dif[i]
        else:
            encounter["enemies"]["difficulty"] = "N/A"
    return


def update_party(party, encounter):
    threshold = {}
    with open(PATH + 'static/files/xp_thresholds.csv', 'r', encoding='utf-8-sig') as csvfile:
        threshreader = csv.reader(csvfile)
        for row in threshreader:
            threshold[str(row[0])] = [int(row[1]), int(row[2]), int(row[3]), int(row[4])]
    ac_weight = {"fighter": 100,
                 "barbarian": 100,
                 "paladin": 100,
                 "monk": 75,
                 "ranger": 75,
                 "cleric": 75,
                 "rogue": 60,
                 "artificer": 60,
                 "druid": 50,
                 "bard": 50,
                 "warlock": 50,
                 "sorcerer": 40,
                 "wizard": 40}
    
    save_prof = {"fighter": ["str", "con"],
                 "barbarian": ["str", "con"],
                 "paladin": ["wis", "cha"],
                 "monk": ["str", "dex"],
                 "ranger": ["str", "dex"],
                 "cleric": ["wis", "cha"],
                 "rogue": ["dex", "int"],
                 "artificer": ["con", "int"],
                 "druid": ["int", "wis"],
                 "bard": ["dex", "cha"],
                 "warlock": ["wis", "cha"],
                 "sorcerer": ["con", "cha"],
                 "wizard": ["int", "wis"]}

    pc_saves = {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0}

    if len(party) > 0:
        
        total_hp = 0
        num = 0
        group_ac = 0
        group_weight = 0
        hits = 0
        # encounter difficulty threshold categories
        easy_enc = 0
        med_enc = 0
        hard_enc = 0
        dead_enc = 0
        for pc in party:
            # basic stats
            total_hp = total_hp + pc["hp"]
            num += 1
            group_ac = group_ac + pc["ac"] * ac_weight[pc["class"]]
            group_weight = group_weight + ac_weight[pc["class"]]
            hits = hits + pc["attacks"]
            # XP thresholds for determining encounter difficulty
            easy_enc = easy_enc + threshold[str(pc["level"])][0]
            med_enc = med_enc + threshold[str(pc["level"])][1]
            hard_enc = hard_enc + threshold[str(pc["level"])][2]
            dead_enc = dead_enc + threshold[str(pc["level"])][3]
            # apply proficiency bonuses to class specific saving throws
            for key in pc_saves.keys():
                pc_saves[key] = pc_saves[key] + pc["modifiers"][key]
                if key in save_prof[pc["class"]]:
                    pc_saves[key] = pc_saves[key] + pc["prof_bonus"]
        # average saving throws by party count - no weight / plain average
        for save in pc_saves:
            pc_saves[save] = int(round(pc_saves[save] / num))
        encounter["party"]["saves"] = pc_saves    
        encounter["party"]["hp"] = total_hp
        encounter["party"]["count"] = num
        encounter["party"]["attacks"] = hits
        encounter["party"]["thresholds"] = [easy_enc, med_enc, hard_enc, dead_enc]
        # party group ac is weighted by class - strong martial classes more likely to be target or 
        # tanking so greater representation in group ac
        if group_weight > 0:
            encounter["party"]["ac"] = int(round(group_ac / group_weight))
    return
