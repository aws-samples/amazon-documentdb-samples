import os
import sys
import pymongo

#Insert sample data
SEED_DATA = [
{"title" : "The Old Guard", "description": "A covert team of immortal mercenaries are suddenly exposed and must now fight to keep their identity a secret just as an unexpected new member is discovered."},
{"title" : "Greyhound", "description": "Early in World War II, an inexperienced U.S. Navy captain must lead an Allied convoy being stalked by Nazi U-boat wolfpacks."},
{"title" : "Palm Springs", "description": "When carefree Nyles and reluctant maid of honor Sarah have a chance encounter at a Palm Springs wedding, things get complicated as they are unable to escape the venue, themselves, or each other."},
{"title" : "Hamilton", "description": "The real life of one of America's foremost founding fathers and first Secretary of the Treasury, Alexander Hamilton. Captured live on Broadway from the Richard Rodgers Theater with the original Broadway cast."},
{"title" : "365 Days", "description": "Massimo is a member of the Sicilian Mafia family and Laura is a sales director. She does not expect that on a trip to Sicily trying to save her relationship, Massimo will kidnap her and give her 365 days to fall in love with him."},
{"title" : "Relic", "description": "A daughter, mother and grandmother are haunted by a manifestation of dementia that consumes their family's home."},
{"title" : "Project Power", "description": "When a pill that gives its users unpredictable superpowers for five minutes hits the streets of New Orleans, a teenage dealer and a local cop must team with an ex-soldier to take down the group responsible for its creation."},
{"title" : "Desperados", "description": "A panicked young woman, with her reluctant friends in tow, rushes to Mexico to try and delete a ranting email she sent to her new boyfriend."},
{"title" : "Tenet", "description": "Armed with only one word -- Tenet -- and fighting for the survival of the entire world, the Protagonist journeys through a twilight world of international espionage on a mission that will unfold in something beyond real time."},
{"title" : "Jerry Maguire", "description": "When a sports agent has a moral epiphany and is fired for expressing it, he decides to put his new philosophy to the test as an independent agent with the only athlete who stays with him and his former colleague."},
{"title" : "The Gentlemen", "description": "An American expat tries to sell off his highly profitable marijuana empire in London, triggering plots, schemes, bribery and blackmail in an attempt to steal his domain out from under him."},
{"title" : "Love", "description": "Murphy is an American living in Paris who enters a highly sexually and emotionally charged relationship with the unstable Electra. Unaware of the effect it will have on their relationship, they invite their pretty neighbor into their bed."},
{"title" : "Fatal Affair", "description": "Ellie tries to mend her marriage with her husband Marcus after a brief encounter with an old friend, David, only to find that David is more dangerous and unstable than she'd realized."},
{"title" : "The New Mutants", "description": "Five young mutants, just discovering their abilities while held in a secret facility against their will, fight to escape their past sins and save themselves."},
{"title" : "Twins", "description": "A physically perfect but innocent man goes in search of his long-lost twin brother, who is short, a womanizer, and small-time crook."},
{"title" : "Joker", "description": "In Gotham City, mentally troubled comedian Arthur Fleck is disregarded and mistreated by society. He then embarks on a downward spiral of revolution and bloody crime. This path brings him face-to-face with his alter-ego: the Joker."},
{"title" : "Parasite", "description": "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan."},
{"title" : "Doctor Sleep", "description": "Years following the events of The Shining (1980), a now-adult Dan Torrance must protect a young girl with similar powers from a cult known as The True Knot, who prey on children with powers to remain immortal."},
{"title" : "Midway", "description": "The story of the Battle of Midway, told by the leaders and the sailors who fought it."},
{"title" : "Ford v Ferrari", "description": "American car designer Carroll Shelby and driver Ken Miles battle corporate interference and the laws of physics to build a revolutionary race car for Ford in order to defeat Ferrari at the 24 Hours of Le Mans in 1966."}
]

#Get Amazon DocumentDB ceredentials from enviornment variables
username = os.environ.get("USERNAME")
password = os.environ.get("PASSWORD")
clusterendpoint = os.environ.get("DOCDB_ENDPOINT")


def main(args):
    #Establish DocumentDB connection
    client = pymongo.MongoClient(clusterendpoint, username=username, password=password)
    db = client.media
    profiles = db['movie']
    
    #ids for documents
    ids = 0

    #Insert data
    while True:
        for i in SEED_DATA:
            ids += 1
            i.update({"_id":ids})
            profiles.insert(i)
            print("Record inserted data")

    client.close()
    
if __name__ == '__main__':
    main(sys.argv[1:])