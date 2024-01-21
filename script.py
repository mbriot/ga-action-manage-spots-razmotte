import os
import json
import random
from urllib.parse import urlparse

def exitError(reason):
    with open(stepOutputPath, 'a') as file:
        file.write("docker-ga-action-error=true\n")
        file.write(f"docker-ga-action-reason={reason}\n")
        exit(0)

def readSpots(repoPath):
    try:
        with open(f"{repoPath}/src/spots.json", 'r') as file:
            spots = json.load(file)
    except FileNotFoundError:
        print(f"file {file} not found.")
    except json.JSONDecodeError:
        print(f"json not valid in {file}.")
    return spots

def parseSpot(body) :
    spotStart = False
    spot = {}
    for line in body.split('\n') :
        if "Spot Template a remplir" in line :
            spotStart = not spotStart
        elif spotStart :
            if line.startswith('\#') or ":" not in line:
                continue
            try:
                spot[line.split(':',1)[0].strip()] = line.split(':',1)[1].strip()
            except :
                exitError(f"Erreur: pb sur la ligne : {line}")
    return spot

def checkSpotFields(spot,operation):
    if spot.get('name', None) is None:
        exitError("Erreur: la variable **name** est obigatoire")
    
    if spot.get('type',None) is not None and spot.get('type',None) not in ['bord-de-mer','plaine','treuil']:
        exitError("Erreur : La variable **type** doit etre renseignée et avoir comme valeur **bord-de-mer**, **plaine** ou **treuil**")
    
    if spot.get('type',None) is not None and spot.get('type',None) == "bord-de-mer" and spot.get('tideTableUrl',None) is None:
        exitError("Erreur : la variable **type** etant **bord-de-mer**, il faut renseigner **tideTableUrl** avec l url des marées")

    if spot.get('tideTableUrl', None) is not None:
        spot['tideTableUrl'] = spot['tideTableUrl'].split('/')[-2] + '/'
    
    if spot.get('type',None) == "bord-de-mer" :
        spot['needSeaCheck'] = True

    if spot.get('localisation',None) is not None and spot['localisation'] not in ['nord','autre']:
        exitError("Erreur : la variable **localisation** prend comme valeur **nord** ou **autre**")

    if spot.get('url',None) is not None:
        spot['url'] = os.path.basename(urlparse(spot['url']).path)

    if spot.get('goodDirection',None) is not None:
        spot['goodDirection'] = spot['goodDirection'].split()
    
    if spot.get('maxSpeed',None) is not None :
        try :
            spot['maxSpeed'] = int(spot['maxSpeed'])
        except Error:
            exitError("Erreur : les variables **maxSpeed** et **minSpeed** doivent etre des entiers")
    
    if spot.get('minSpeed',None) is not None :
        try :
            spot['minSpeed'] = int(spot['minSpeed'])
        except Error:
            exitError("Erreur : les variables **maxSpeed** et **minSpeed** doivent etre des entiers")

    try:
        if spot.get('excludeDays', None) is not None:
            spot['excludeDays'] = [int(value) for value in spot['excludeDays'].split()]
    except Error:
        exitError("Erreur: la variable **excludeDays** doit contenir une liste de chiffre entre 0 et 6 séparé par des espaces")

    try:
        if spot.get('monthsToExcludes', None) is not None:
            spot['monthsToExcludes'] = [int(value) for value in spot['monthsToExcludes'].split()]
    except Error:
        exitError("Erreur: la variable **monthToExcludes** doit contenir une liste de chiffre entre 1 et 12 séparé par des espaces")

    if operation == "create":
        requiredFields = ["name","type","localisation","url","goodDirection","minSpeed","maxSpeed","distance","geoloc","description"]
        checkRequiredFields(spot,requiredFields)
    
    if operation in ["update","delete"]:
        checkRequiredFields(spot,["name"])

    return spot

def checkRequiredFields(spot, requiredFields):
    for field in requiredFields:
        if spot.get(field,None) is None:
            exitError(f"Erreur: le champ **{field}** est obligatoire")

def checkSpotAlreadyPresent(spots,spot):
    newSpotName = spot['name']
    for spot in spots['spots']:
        if newSpotName == spot['name'] :
            return True
    return False

def parseOperation(body):
    creation = False
    update = False
    delete = False

    for line in body.split('\n'):
        if "[x]" in line :
            if "Ajout" in line:
                creation = True
            if "Modification" in line : 
                update = True
            if "Suppression" in line :
                delete = True
    
    if [creation, update, delete].count(True) == 0 :
        exitError("Erreur : aucune opération n a été choisie. Mettre un x entre les crochets d'une des opérations")
    
    if [creation, update, delete].count(True) >= 2 :
        exitError("Erreur : plus d une opération a été coché. Une seule opération à la fois.")

    return "update" if update else "delete" if delete else "create"

def updateSpots(spots,updatedSpot):
    for spot in spots['spots']:
        if spot['name'] == updatedSpot['name']:
            for key in updatedSpot.keys():
                spot[key] = updatedSpot[key]
    return spots

def run():
    repoPath = os.environ.get('GITHUB_WORKSPACE',None)
    issueBody = os.environ.get('INPUT_ISSUE_BODY',None)
    global stepOutputPath
    stepOutputPath = os.environ.get('GITHUB_OUTPUT',None)
    operation = parseOperation(issueBody)
    spot = parseSpot(issueBody)
    spot = checkSpotFields(spot,operation)
    spots = readSpots(repoPath)

    if checkSpotAlreadyPresent(spots,spot) and operation == "create":
        reason = f"Erreur : Le spot **{spot['name']}** existe déjà. Si vous vouliez le mettre à jour, il faut renseigner UPDATE au lieu de CREATE. Vous pouvez editer l issue en corrigeant pour relancer le processus."
        exitError(reason)
    
    if not checkSpotAlreadyPresent(spots,spot) and operation in ["update","delete"]:
        reason = f"Erreur : Le spot **{spot['name']}** n existe pas. Vous avez fait une erreur en orthographiant le nom du spot ?"
        exitError(reason)

    if operation == "create":
        spots['spots'].append(spot)
    elif operation == "delete":
        spots['spots'] = [newSpot for newSpot in spots['spots'] if newSpot["name"] != spot["name"]] 
    elif operation == "update":
        spots = updateSpots(spots,spot)

    try:
        with open(f"{repoPath}/src/spots.json", 'w') as file:
            json.dump(spots, file, indent=2)
    except FileNotFoundError:
        exitError(f"file {file} not found.")

    with open(stepOutputPath, 'a') as file:
        file.write("docker-ga-action-error=false\n")
        exit(0)

if __name__ == "__main__":
    run()