#/usr/bin/env python
# -*- coding: utf-8 -*-
import ConfigParser
import codecs
import os
import json
import time
import urllib
import sys
import datetime
#import wikitools
from bs4 import BeautifulSoup
from sys import exit
from PIL import Image, ImageFont, ImageDraw

PAINTS = []
with open(os.path.join("data", "paints")) as f:
    for line in f.readlines():
        PAINTS.append(line[:6])
        
def main():
    cls()
    print "Unusual Schema"
    print "Loading config..."
    options = Options()
    
    # Check that a key was supplied
    if options.key == "" or options.key == "NO_KEY":
        print "ERROR: No API key specified in settings.ini."
        print "See http://steamcommunity.com/dev to acquire one."
    
    # Acquire Latest Schema
    if os.path.isfile(os.path.join("data", "schema.json")):
        print "Schema Last Updated: " + str(datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join("data", "schema.json"))))[:19]
        if options.update == 1:
            choice = raw_input("Download latest schema? (y/N) ")
            if choice in ["y", "Y"]:
                getSchema(options)
        elif options.update == 2:
                getSchema(options)
    else:
        print "No previous schema found. Downloading latest version now."
        getSchema(options)
    
    # Load schema
    print "Loading Schema."
    with open(os.path.join("data", "schema.json"), "r") as f:
        schema = Schema(f)
    print "Schema read."
    
    # Get rarities
    if options.run_rarities:
        schema = getRarities(schema)
        pause(options)
    
    # Get images
    if options.run_images:
        getImages(schema, options)
        pause(options)
    
    # Handle Edge Cases
    if options.run_edge:
        schema = edgeCases(schema)
        pause(options)
    
    # Get painted images
    if options.run_painted:
        getPaintedImages(schema, options)
        pause(options)
    
    # Export to items.js/rules.php for the time being.
    print "Exporting for tf2tags 2.0"
    itemsJS(schema)
    print "items.js produced."
    rulesPHP(schema)
    print "rules.php produced."
    
    # Save Updated Schema
    text = json.dumps(schema.schema)
    fh = codecs.open(os.path.join("data", "unusualSchema.json"), encoding='utf-8', mode='w')
    fh.write(text)
    fh.close()
    
    print "New unusualSchema.json produced."
    
    return
    
    
class Options(object):
    def __init__(self):
        # Check the settings file exists
        if not os.path.isfile("settings.ini"):
            print "ERROR: File settings.ini does not exist. Rename settings-sample.ini and include your API key and try again."
            exit()
        
        config = ConfigParser.RawConfigParser()
        config.read("settings.ini")
        
        # API
        self.key        = config.get('API', 'Key')
        self.language   = config.get('API', 'Language')
        
        # Settings
        self.update     = config.getint('Settings', 'Update')
        self.pause     = config.getint('Settings', 'Pause')
        
        # Directories
        self.image_dir  = config.get('Directories', 'Images')
        
        # Things to acquire
        self.run_rarities   = config.getint('Data', 'Rarities')
        self.run_images     = config.getint('Data', 'Images')
        self.run_painted    = config.getint('Data', 'Painted')
        self.run_edge       = config.getint('Data', 'Edge')
        
def getSchema(options):
    # Backup the old Schema if it exists
    if os.path.isfile(os.path.join("data", "schema.json")):
        timestamp = os.path.getmtime(os.path.join("data", "schema.json"))
        timestamp = datetime.date.fromtimestamp(timestamp)
        timestamp = timestamp.strftime("%Y-%m-%d")
        os.rename(os.path.join("data", "schema.json"), os.path.join("data", timestamp+" schema.json"))
        print "Previous Schema saved for backup purposes."
    
    print "Downloading latest Schema..."
    newschema = urllib.urlopen("http://api.steampowered.com/IEconItems_440/GetSchema/v0001?key="+options.key+"&language="+options.language)
    
    with open(os.path.join("data", "schema.json"), "w") as f:
        f.write(newschema.read())
        
    size = os.path.getsize(os.path.join("data", "schema.json")) / 1024
    if size < 1000:
        print "ERROR: Filesize is under 1000kb! Reverting to previous schema and aborting."
        os.remove(os.path.join(ROOT, "assets", "data", "schema.json"))
        if os.path.isfile("data", "schema.json"):
            os.rename(os.path.join(ROOT, "assets", "data", timestamp+" schema.json"), os.path.join(ROOT, "assets", "data", "schema.json"))
        exit()
        
    print "Schema downloaded. Filesize is", size, "kb."
    return True
    
class Schema(object):
    def __init__(self, data):
        self.raw = data
        self.schema = json.load(self.raw)["result"]
        
    def item(self, input):
        #print "LOOKING FOR ", input
        for item in self.schema["items"]:
            if item["defindex"] == input or item["item_name"] == input:
                return item
        print "ITEM NOT FOUND!"
        return False
        
    def delete(self, input):
        matched = False
        for count in xrange(0,len(self.schema["items"])):
            if self.schema["items"][count]["defindex"] == input:
                del self.schema["items"][count]
                print "Removed item", input
                matched = True
                break
        if not matched:
            print "ITEM NOT FOUND!"
        return matched
    
    def setSlot(self, defindex, input):
        matched = False
        for count in xrange(0,len(self.schema["items"])):
            if self.schema["items"][count]["defindex"] == defindex:
                self.schema["items"][count]["item_slot"] = input
                print "Set slot for", defindex, "to", input
                matched = True
                print self.schema["items"][count]["name"], count
                break
        if not matched:
            print "ITEM NOT FOUND!"
        return matched
        
    def togglePaint(self, defindex):
        matched = False
        for count in xrange(0,len(self.schema["items"])):
            if self.schema["items"][count]["defindex"] == defindex:
                if (self.schema["items"][count]["capabilities"].get("paintable", False)):
                    del self.schema["items"][count]["capabilities"]["paintable"]
                    print "Removed paint for item", defindex
                else:
                    self.schema["items"][count]["capabilities"]["paintable"] = True
                    print "Added paint for item", defindex
                matched = True
                break
        if not matched:
            print "ITEM NOT FOUND!"
        return matched
        
    def toggleName(self, defindex):
        matched = False
        for count in xrange(0,len(self.schema["items"])):
            if self.schema["items"][count]["defindex"] == defindex:
                if (self.schema["items"][count]["capabilities"].get("nameable", False)):
                    del self.schema["items"][count]["capabilities"]["nameable"]
                    print "Removed naming for item", defindex
                else:
                    self.schema["items"][count]["capabilities"]["nameable"] = True
                    print "Added naming for item", defindex
                matched = True
                break
        if not matched:
            print "ITEM NOT FOUND!"
        return matched
        
    def removeStyles(self, defindex):
        matched = False
        for count in xrange(0,len(self.schema["items"])):
            if self.schema["items"][count]["defindex"] == defindex:
                if self.schema["items"][count].get("styles", False):
                    del self.schema["items"][count]["styles"]
                matched = True
                print "Removed styles for item", defindex
                break
        if not matched:
            print "ITEM NOT FOUND!"
        return matched
        
    def toggleRarity(self, defindex, rarity):
        matched = False
        for count in xrange(0,len(self.schema["items"])):
            if self.schema["items"][count]["defindex"] == defindex:
                if (self.schema["items"][count]["rarities"].get(rarity, False)):
                    del self.schema["items"][count]["rarities"][rarity]
                    print "Removed", rarity, "rarity from", defindex
                else:
                    self.schema["items"][count]["rarities"][rarity] = True
                    print "Added", rarity, " rarity to", defindex
                matched = True
                break
        if not matched:
            print "ITEM NOT FOUND!"
        return matched
        
def getRarities(schema):
    templateRarities = ["Vintage", "Strange", "Genuine", "Unusual", "Haunted"]
    listRarities = ["Community", "Self-Made"]
    
    rarityDict = {}
    for rarity in templateRarities:
        print "Acquiring " + rarity + " items..."
        if not os.path.isfile(os.path.join("data", rarity + ".txt")):
            print "Downloading... " + rarity
            raw = urllib.urlopen("http://wiki.teamfortress.com/wiki/Template:"+rarity+"_quality_table")
            raw = raw.read()
            fh = codecs.open(os.path.join("data", rarity + ".txt"), encoding='utf-8', mode='w')
            fh.write(unicode(raw, 'utf-8'))
            fh.close()
        
        raw = open(os.path.join("data", rarity + ".txt")).read()
        soup = BeautifulSoup(raw)
        text = soup.get_text()

        # Invalid Data reduction
        begin = "Possible "+rarity+" quality items"
        start = text.find(begin)
        text = text[start+len(begin):]

        end = " Note"
        finish = text.find(end)
        
        if finish == -1:
            end = "This template uses translation"
            finish = text.find(end)
        
        text = text[:finish]

        text = text.split("\n")

        newtext = []
        for line in text:
            if line == " " or line == "":
                continue
            if line[1] in "1234567890":
                continue
            
            if line[1:] in ["Scout", "Soldier", "Pyro", "Demoman", "Heavy", "Engineer", "Medic", "Sniper", "Spy", "All classes", "Miscellaneous items"]:
                continue
                
            if line[1:] in ["Primary", "Secondary", "Melee", "PDA", "PDA2", "Building", "Watch"]:
                continue
                
            if line[1:] == "N/A":
                continue
            
            # Special cases
            if line[-1] in "1234567890":
                line = line[:-1]
            
            # Wiki name discrepencies
            if line == " Submachine Gun":
                line = " SMG"
                
            if line == u" Übersaw":
                line = " Ubersaw"
            
            newtext.append(line[1:])
            
        text = newtext
        
        # Assign to dict
        rarityDict[rarity] = text
        
        
        """
        #Dump text files for quick verification
        fh = codecs.open(os.path.join(ROOT, "assets", "data", rarity+"Soup.txt"), encoding='utf-8', mode='w')
        for line in text:
            fh.write(line + "\n")
        fh.close()
        """

    # HANDLE OTHER RARITIES
    ############################################################################################################################################
    # Self_Made Items
    print "Acquiring Self-Made items..."
    if not os.path.isfile(os.path.join("data", "Self_Made" + ".txt")):
        print "Downloading... " + "Self_Made"
        raw = urllib.urlopen("http://wiki.teamfortress.com/wiki/List_of_community-contributed_items") #Community Contributed means self-made.
        raw = raw.read()
        fh = codecs.open(os.path.join("data", "Self_Made" + ".txt"), encoding='utf-8', mode='w')
        fh.write(unicode(raw, 'utf-8'))
        fh.close()
    
    raw = open(os.path.join("data", "Self_Made" + ".txt")).read()
    soup = BeautifulSoup(raw)
    text = soup.get_text()
    
    text = text.split("\n")
    newtext = []
    
    
    count = 0
    for line in text:
        if line == " " or line == "":
                continue
        if line == "  See also ":
            break
        count += 1
        newtext.append(line)
    text = newtext
    # Assign to dict
    rarityDict["Self-Made"] = text
    ############################################################################################################################################
    # Community Items
    print "Acquiring Community items..."
    if not os.path.isfile(os.path.join("data", "Community" + ".txt")):
        print "Downloading... " + "Community"
        raw = urllib.urlopen("http://wiki.teamfortress.com/wiki/List_of_Community_item_owners") #Community Contributed means self-made.
        raw = raw.read()
        fh = codecs.open(os.path.join("data", "Community" + ".txt"), encoding='utf-8', mode='w')
        fh.write(unicode(raw, 'utf-8'))
        fh.close()
    
    raw = open(os.path.join("data", "Community" + ".txt")).read()
    soup = BeautifulSoup(raw)
    text = soup.find_all("a")
    newtext = []
    
    
    count = 0
    for line in text:
        count += 1
        newtext.append(line.string)
    text = newtext
    # Assign to dict
    rarityDict["Community"] = text
    
    # Dump text files for quick verification
    #fh = codecs.open(os.path.join(ROOT, "assets", "data", "community"+"Soup.txt"), encoding='utf-8', mode='w')
    #for line in text:
    #    fh.write(line + "\n")
    #fh.close()
    ############################################################################################################################################
    
    # Insert rarity data into schema
    counts = {"Normal":0, "Unique":0, "Vintage":0, "Strange":0, "Genuine":0, "Unusual":0, "Haunted":0, "Self-Made":0, "Community":0} # Count of item rarities
    for item in schema.schema["items"][31:]: #Start at [31] to ignore default weapons
        item["rarities"] = {}
        # Stock items
        if item["defindex"] < 35:
            item["rarities"]["Normal"] = True
            counts["Normal"] += 1
            
        # Additional items
        item["rarities"]["Unique"] = True
        counts["Unique"] += 1
        for rarity in templateRarities + ["Self-Made", "Community"]:
            if item["item_name"] in rarityDict[rarity]:
                item["rarities"][rarity] = True
                counts[rarity] += 1

    print "Marked items."
    for rarity in counts:
       print rarity, counts[rarity] 
    return schema
        
def getImages(schema, options):
    print "Downloading Images."
    for item in schema.schema["items"]:
        fname = str(item["defindex"])
        
        # Check if the image already exists
        if os.path.isfile(os.path.join(options.image_dir, fname+".png")):
            continue
        
        if item.get("image_url", False):
            url = item["image_url"].replace("\\", "")
        else:
            print fname + " has no image"
            continue
        
        # Download the file
        urllib.urlretrieve(url, os.path.join(options.image_dir, fname+".png"))
        print "Downloading #"+ str(fname), item["item_name"]

def edgeCases(schema):
    cases = open(os.path.join("data", "edgeCases.dat")).readlines()
    
    #print len(schema.schema["items"])
    for case in cases:
        #Comments
        if case[0] == "#":
            continue
        
        case = case.split(";")[0]
        data = case.split(" ")
        
        if data[0] == "DELETE":
            schema.delete(int(data[2]))
            
        elif data[0] == "SET" and data[1] == "SLOT":
            schema.setSlot(int(data[2]), data[3])
            
        elif data[0] == "TOGGLE" and data[1] == "PAINT":
            schema.togglePaint(int(data[2]))
            
        elif data[0] == "TOGGLE" and data[1] == "NAMING":
            schema.toggleName(int(data[2]))
        
        elif data[0] == "TOGGLE" and data[1] == "RARITY":
            schema.toggleRarity(int(data[2]), data[3])
    
        elif data[0] == "REMOVE" and data[1] == "STYLES":
            schema.removeStyles(int(data[2]))
            
    """
    for item in schema.schema["items"]:
        if "Botkiller" in item["item_name"]:
            item["rarities"]["Strange"] = True
            try:
                del(item["rarities"]["Unique"])
            except:
                pass
    """
    #print len(schema.schema["items"])
    return schema
    
def itemsJS(schema):
    """
    [486, "Summer Shades", 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, ]
    [0] - Image ID
    [1] - Name
    [2] - Paint
    [3] - Forms
    [4] - Haunted
    [5] - Unique
    [6] - Vintage
    [7] - Genuine
    [8] - Strange
    [9] - Unusual
    [10]- Community
    [11]- Self-Made
    [12]- Valve
    """
    slots = ["", "primary", "secondary", "melee", "pda", "pda2", "head", "misc", "action"]
    ordered = sorted(schema.schema["items"], key=lambda attrib: attrib["item_name"].lower())
    
    text = "//Items.js - Last Updated " + str(datetime.datetime.now()) + "\n"
    text += "function getItems(classname, slot)\n"
    text += "{\n"
    text += "\titems=[];\n\n"
    
    for role in ["Scout", "Soldier", "Pyro", "Demoman", "Heavy", "Engineer", "Medic", "Sniper", "Spy", "All"]:
        text += "\tif (classname == '"+role.lower()+"')\n"
        text += "\t{\n"
        text += "\t\tswitch (slot)\n"
        text += "\t\t{\n"
        for x in xrange(1,9):
            text += "\t\tcase "+str(x)+":\n"
            text += "\t\t{\n"
            text += "\t\t\titems = [\n"
            for item in ordered:
                if item.get("item_slot") and item["defindex"] >= 35:
                    if ((item.get("used_by_classes") and role in item["used_by_classes"]) or (role == "All" and not ("used_by_classes" in item))) and item["item_slot"] == slots[x]:
                        if (item["capabilities"].get("nameable")):
                            text += "\t\t\t[" + str(item["defindex"]) + ", \"" + (item["proper_name"]*"The ") + item["item_name"].replace("'", "=") + "\", "
                            text += str(int(item["capabilities"].get("paintable", 0))) + ", "
                            text += str(int(("styles" in item))) + ", "
                            text += str(int(("Haunted" in item["rarities"]))) + ", "
                            text += str(1) + ", "
                            text += str(int(("Vintage" in item["rarities"]))) + ", "
                            text += str(int(("Genuine" in item["rarities"]))) + ", "
                            text += str(int(("Strange" in item["rarities"]))) + ", "
                            text += str(int(("Unusual" in item["rarities"]))) + ", "
                            text += str(int(("Community" in item["rarities"]))) + ", "
                            text += str(int(("Self-Made" in item["rarities"]))) + ", "
                            text += str(1)
                            text += "],\n"
                        
            text += "\t\t\t];\n"
            text += "\t\t\treturn items;\n"
            text += "\t\t}\n"
        text += "\t\t}\n"
        text += "\t}\n"
    text += "return items;\n}"
    fh = codecs.open(os.path.join("data", "items.js"), encoding='utf-8', mode='w')
    fh.write(text)
    fh.close()
    return True
    
def rulesPHP(schema):
    """
    $items['486-all'] = array("Summer Shades", 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, "all", 7);
    [0] = Name
    [1] = Paint
    [2] = Forms
    [3] = Haunted
    [4] = Unique
    [5] = Vintage
    [6] = Genuine
    [7] = Strange
    [8] = Unusual
    [9] = Community
    [10] = Self-Made
    [11] = Valve
    [12] = Class
    [13] = Slot
    """
    
    slotNum = {"primary":1, "secondary":2, "melee":3, "pda":4, "pda2":5, "head":6, "misc":7, "action":8, "building":4}
    
    text = "<?php\n//Rules.php - Last updated: "+str(datetime.datetime.now())+"\n"
    text += "$items=array();\n"
    for item in schema.schema["items"]:
        if (item["capabilities"].get("nameable") and item["defindex"] >= 35):
            roles = item.get("used_by_classes", ["all"])
            for role in roles:
                #print "DEFINDEX:", item["defindex"]
                text += "$items['"+str(item["defindex"])+"-"+role.lower()+"'] = array("
                text += '"'+(item["proper_name"]*"The ") + item["item_name"]+'", '
                text += str(int(item["capabilities"].get("paintable", 0)))+", "
                text += str(int(("styles" in item))) + ", "
                text += str(int(("Haunted" in item["rarities"]))) + ", "
                text += str(1) + ", "
                text += str(int(("Vintage" in item["rarities"]))) + ", "
                text += str(int(("Genuine" in item["rarities"]))) + ", "
                text += str(int(("Strange" in item["rarities"]))) + ", "
                text += str(int(("Unusual" in item["rarities"]))) + ", "
                text += str(int(("Community" in item["rarities"]))) + ", "
                text += str(int(("Self-Made" in item["rarities"]))) + ", "
                text += str(1) + ", "
                text += '"'+role.lower()+'"'+", "                
                text += str(slotNum[item["item_slot"]])
                text += ");\n"
                
    text += "?>"
    fh = codecs.open(os.path.join("data", "rules.php"), encoding='utf-8', mode='w')
    fh.write(text)
    fh.close()

def cls():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

def getPaintedImages(schema, options):
    # This function is ran after edge cases to easily deal with not downloading images that will never exist or we never want to have
    # Find every painted image
    
    # Initialize the font for placeholder images
    font = ImageFont.truetype("victor-pixel.ttf", 10)
    
    
    for item in schema.schema["items"]:
        if not item["capabilities"].get("paintable", False):
            continue
        stillMissing = []
        for style in xrange(0,len(item.get("styles", "1"))):
            dlQueue = []
            styleNum = style
            
            if style == 0:
                style = ""
                styleName = ""
            else:
                style = "-" + str(style)
                styleName = item["styles"][styleNum]["name"].replace(" ", "_")
            # Check that the folder for paints exists, if not, make it
            defindex = str(item["defindex"])
            imagePath = os.path.join(options.image_dir, defindex)
            if not os.path.exists(imagePath):
                os.mkdir(imagePath)
                
            # See what paint images don't exist
            for paint in PAINTS:
                if not os.path.isfile(os.path.join(imagePath, paint + style + ".png")):
                    dlQueue.append(paint)
                
            
            # See what paint images are just placeholders
            if os.path.isfile(os.path.join(imagePath, "missing.dat")):
                with open(os.path.join(imagePath, "missing.dat")) as f:
                    for missing in f.readlines():
                        print missing[:-1]
                        dlQueue.append(missing[:-1])
            
            
            # Download them if possible
            for paint in dlQueue:
                # Find the url from the painted page
                url = "http://wiki.teamfortress.com/wiki/File:Painted_" + item["item_name"].replace(" ", "_").encode('utf-8') + "_" + paint + ("_"*(styleName != "")) + styleName + ".png"
                #url = "http://wiki.teamfortress.com/wiki/"+item["item_name"].replace(" ", "_").encode('utf-8')
                url = url.replace("?", "_") # Dangersque, Too? Fix
                
                #print url
                page = urllib.urlopen(url).read()
                
                start = page.find('fullImageLink" id="file"><a href="')+34
                page = page[start:]
                end = page.find('.png')
                page = page[:end]
                #print start, end, page
                
                # Download the image
                url = "http://wiki.teamfortress.com" + page
                print "Downloading", defindex, item["item_name"], paint
                #print "FROM: ", url
                try:
                    urllib.urlretrieve(url, os.path.join(imagePath, paint + style + ".png"))
                except:
                    pass
                # See if we downloaded it
                try:
                    #print "Downloaded"
                    image = Image.open(os.path.join(imagePath, paint + style + ".png"))
                    placeholder = False
                except:
                    print "File Not Found. Using a placeholder instead"
                    image = Image.open(os.path.join(imagePath + ".png"))
                    placeholder = True
                
                # Resize the image (only for good images, not placeholders)
                if not placeholder:
                    image.thumbnail((85, 85), Image.ANTIALIAS)
                    width = image.size[0]
                    height = image.size[1]
                    
                    output = Image.new("RGBA", (128,128))
                    output.paste(image, ((128-width)/2, (128-height)/2))
                else: # Mark placeholders
                    output = Image.new("RGBA", (128,128))
                    output.paste(image, (0,0))
                    textimg = ImageDraw.Draw(output)
                    textimg.text((2, 118), "#"+paint, font=font, fill=(255,215,0))
                    stillMissing.append(paint + "-" + str(styleNum) + " " + styleName)
                    
                #print "RESIZED"
                try:
                    output.save(os.path.join(imagePath, paint + style + ".png"))
                except:
                    print "----- COULDN'T SAVE", imagePath, paint, style
            if style != "":
                print "Done with style", styleName
        
        if len(stillMissing) > 0:
            missingList = open(os.path.join(imagePath, "missing.dat"), "w")
            for line in stillMissing:
                missingList.write(line + "/n")
            missingList.close()
            print "Wrote missing.dat"
    print "ALL PAINTS DOWNLOADED."
    
def pause(options):
    if options.pause == True:
        raw_input("PAUSED")

if __name__ == "__main__": main()