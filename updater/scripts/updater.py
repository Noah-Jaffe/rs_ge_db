import os
import requests
import json
from time import sleep, time
import aiohttp
import asyncio
import pickle
from memory_profiler import profile
from datetime import datetime, timedelta

DEBUG_MODE = True

# NOTE os.getcwd() might not be the right answer!
SUPPORTED_GAMES = {"osrs","rs"}
GAME_UPDATE_TIMESTAMP_DT_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

async def getMultipleJsonRequests(urls:list, maxRequestPerBatch:int=100, waitBetweenBatch:float=2, maxRetry:int=3) -> dict:
    """Speedy-ish way of retreiving multiple requests at once.

    Args:
        urls (list): list of urls to retreive.
        maxRequestPerBatch (int, optional): maximum requests to be sent at once. Defaults to 100. NOTE: set it to be something to not get rate limited.
        waitBetweenBatch (float, optional): between each batch have a cooldown of this many seconds. Defaults to 2. NOTE: set it to be something to not get rate limited.
        maxRetry (int, optional): retry this many times before giving up completely. Defaults to 3. NOTE: set it to be something to not get rate limited.

    Returns:
        dict:
        dict: where the keys are the urls you were retreiving, and the values are the json retreived from the url
    """
    class urlAttempt():
        TOTAL_SUCCESS = 0
        EXPECTED = 0
        def __init__(self, url) -> None:
            self.url = url
            self.attempts = 0
            self.json = None
        
        async def _fetch_json_from_url(self, session):
            self.attempts += 1
            try:
                async with session.get(self.url) as response:
                    self.json = await response.json()
                if self.json and DEBUG_MODE:
                    urlAttempt.updateSuccess()
            except:
                pass

        @staticmethod
        def updateSuccess(): # DEBUG_MODE
            urlAttempt.TOTAL_SUCCESS += 1
            print(f"{urlAttempt.TOTAL_SUCCESS}/{urlAttempt.EXPECTED}")
    
    results = {}
    
    urls = [urlAttempt(u) for u in set(urls)]
    urlAttempt.EXPECTED = len(urls)
    lastAttempted = 0

    while urls:
        # wait until its ok to proceed
        while time() - lastAttempted < waitBetweenBatch:
            sleep(waitBetweenBatch/10)
        
        # retreive batch
        batch = urls[:maxRequestPerBatch]
        urls = urls[maxRequestPerBatch:]
        
        # fetch batch
        async with aiohttp.ClientSession() as session:
            lastAttempted = time()
            await asyncio.gather(*[u._fetch_json_from_url(session) for u in batch])
        
        # parse response
        while batch:
            response = batch.pop()
            if response.json:
                # store results
                results[response.url] = response.json
            elif response.attemps < maxRetry:
                # retry again later
                urls.append(response)
            elif response.attempts == maxRetry:
                # remove completely, dont retry
                results[response.url] = None#Exception("Max retries attempted")
    return results

async def get_one(session: aiohttp.ClientSession, url: str) -> None:
    print("Requesting", url)
    async with session.get(url) as resp:
        js = await resp.json()
        print("Got response from", url)
        return js
    
async def get_all(urls: list[str], num_concurrent: int) -> None:
    url_iterator = iter(urls)
    keep_going = True
    async with aiohttp.ClientSession() as session:
        while keep_going:
            tasks = []
            for _ in range(num_concurrent):
                try:
                    url = next(url_iterator)
                except StopIteration:
                    keep_going = False
                    break
                new_task = asyncio.create_task(get_one(session, url))
                tasks.append(new_task)
            await asyncio.gather(*tasks)

def getJson(url):
    return requests.get(url).json()

class PriceTs():
    """instance of timestamp - price - volume"""
    def __init__(self, src:str, timestamp:datetime, price:int, volume:int=None):
        self.timestamp = timestamp
        self.price = price
        self.volume = volume
        self.src = src
    
    def filter(self, **kwargs):
        """Returns self if any of the given kwargs match by value
        Returns:
            PriceTs | None: returns self if filter matches, else None
            Ex:
            obj.filter(timestamp=datetime(2001, 1, 7, 0, 0), price=1234) 
            returns obj if obj.timestamp == datetime(2001, 1, 7, 0, 0) OR obj.price == 1234
        """
        for k in kwargs:
            if self.__getattribute__(k) == kwargs[k]:
                return self
        return None
    
    def getAs(self, mode:str, **kwargs):
        """Returns this instance represented as the given datatype.
        Args:
            mode (str): {'json','csv','tsv','repr','pickle'}
        Returns:
            datatype compatable with the given mode.
        """
        if mode == 'json':
            return vars(self)
        elif mode == 'csv':
            return kwargs.get('delim',",").join([self.timestamp.strftime(kwargs.get('tsFormat', '%Y-%m-%d %H:%M')), str(self.price), str(self.volume) if self.volume is not None else ''])
        elif mode == 'tsv':
            return kwargs.get('delim',"\t").join([self.timestamp.strftime(kwargs.get('tsFormat', '%Y-%m-%d %H:%M')), str(self.price), str(self.volume) if self.volume is not None else ''])
        elif mode == 'repr':
            return repr(vars(self))
        elif mode == 'pickle':
            if kwargs.get('fp'):
                pickle.dump(self, kwargs.get('fp'))
            return pickle.dumps(self)
        raise ValueError(f"'{mode}' is an unsupported datatype!")

class PriceHistory():
    """Historical price info"""
    def __init__(self) -> None:
        self.history = {}
    
    def add(self, timestamp, price:int, volume:int=None, src:str=None):
        """
        Adds a record to the history
        Args:
            timestamp (str | int | float | datetime) some representation of the timestamp
            price (int | str) some representation of the price
            volume (int | str | None) OPTIONAL some representation of the volume
            src (str | None) OPTIONAL the src if you want to keep track of it
        """
        # TODO: allow conversion here or do it at read time?
        if isinstance(timestamp, datetime):
            pass
        elif isinstance(timestamp, str):
            if ":" in timestamp:
                timestamp = datetime.strptime(timestamp)
            else:
                try:
                    timestamp = datetime.fromtimestamp(float(timestamp))
                except:
                    timestamp = datetime.fromtimestamp(float(timestamp)/1000)
        elif type(timestamp) in {int, float}:
            try:
                timestamp = datetime.fromtimestamp(timestamp)
            except:
                timestamp = datetime.fromtimestamp(timestamp/1000)
        else:
            raise Exception('idk how to convert the timestamp')
        
        
        self.history[timestamp] = PriceTs(timestamp=timestamp, price=price, volume=volume, src=src)
    
    def getFilteredPrices(self, filterMode:str="all", since:datetime=None):
        """get the prices filtered a certain way
        
        Args:
            filterMode (any):
        "" "
        assert isinstance(filterMode, str) and len(set(filterMode.strip().lower().split("|")) - {"all", "simplified", "normalized"}) == 0, f"Unsupported filterMode of {filterMode}"
        assert isinstance(since, datetime)
        keys = sorted(self.history, reverse=True)
        vals = [[datetime.strftime(k,"%y-%m-%d %H:%M"), *self.history[k]] for k in keys]
        if "normalized" in filterMode and vals:
            m1, m2 = vals[0][1], 0
            for v in vals:
                if v[1] > m2:
                    m2 = v[1]
                if v[1] < m1:
                    m1 = v[1]
            maxed = m2 - m1
            if maxed > 0:
                for v in vals:
                    v[1] = round((v[1] - m1)/maxed,4)
        
        if "simplified" in filterMode and vals:
            begin = 0
            repeated = 0
            while begin + repeated < len(vals):
                if vals[begin][1] == vals[begin + repeated + 1][1]:
                    repeated += 1
                else:
                    if repeated > 2:
                        # cut out extra repititions (keep both ends like bookmarks)
                        vals = vals[:begin + 1] + vals[begin + repeated:]
                    begin = begin + repeated + 1
                    repeated = 0
            if repeated > 0:
                vals = vals[:begin + 1]
        
        return vals
        """ # TODO: INCOMPLETE, UNKNOWN USAGE

class RetreiveJSON():
    MAX_BATCH_SIZE = 100
    LAST_BATCH_ATTEMPT = datetime(2001,1,7,0,0)
    WAIT_BETWEEN_BATCHES = 10
    MAX_ATTEMPTS = 3

    def __init__(self, url) -> None:
        self.url = url
        self.attempts = 0
        self.json = None
    
    async def _fetch_json_from_url(self, session):
        self.attempts += 1
        async with session.get(self.url) as response:
            self.json = await response.json()

class GEObject():
    def __init__(self, id:int=None, name:str=None, members:bool=None, value:int=None, highalch:int=None, lowalch:int=None, prices:PriceHistory=None):
        self.key = int(id)
        self.name = name
        self.isMembers = True if members else False
        self.value = value
        self.highalch = highalch
        self.lowalch = lowalch
        self.prices = prices if isinstance(prices, PriceHistory) else PriceHistory()
    
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, GEObject):
            return self.key == int(__value.key) and self.game == __value.game
        elif isinstance(__value, dict):
            return self.key == int(__value.get("key")) and self.game == __value.get("game")
        return False
    
    async def retreiveAllHistory(self):
        """Loads all the available history for this object from online sources
        """
        raise NotImplementedError()
    
    def updateMetadata(self, **kwargs):
        for kw in kwargs:
            self.__setattr__(kw, kwargs[kw])

class GameData():
    SUPPORTED_GAMES = {"osrs","rs"}
    LAST_UPDATE_TIMESTAMP_FILE_NAME = "LAST_UPDATED"
    LAST_UPDATE_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    SEREALIZED_DATABASE_FILE_NAME = "game.pkl"

    def __init__(self, game:str, isUpdateAvailableFunc:callable, periodicUpdaterFunc:callable):
        """Initalizes the object for the given game.
        Sets up directory or files if they dont exist.
        Args:
            game (str): the game mode this is for.
        """
        game = str(game).lower().strip()
        assert game in GameData.SUPPORTED_GAMES, f"{game} is invalid value for game argument"
        
        self.game = game
        self.gameDir = f"{os.getcwd()}/data/{game}/"
        
        if not os.path.isdir(self.gameDir):
            os.mkdir(self.gameDir)
        
        self.lastLocalDbUpdateTsFilePath = f"{self.gameDir}/{self.LAST_UPDATE_TIMESTAMP_FILE_NAME}"
        self.localDBFilePath = f"{self.gameDir}/{self.SEREALIZED_DATABASE_FILE_NAME}"
        
        self.isUpdateAvailableFunc = isUpdateAvailableFunc
        self.periodicUpdateFunc = periodicUpdaterFunc

        self.database = {}
    
    def checkLastLocalDbUpdate(self) -> bool:
        """
        Returns:
            bool: if master database has an update ready
        """
        if not os.path.isfile(self.lastLocalDbUpdateTsFilePath):
            self.lastLocalDbUpdateTimestamp = datetime(2001,1,7,0,0,0)
            with open(self.lastLocalDbUpdateTsFilePath,'w') as f:
                f.write(self.lastLocalDbUpdateTimestamp.strftime(self.LAST_UPDATE_TIMESTAMP_FORMAT))
        else:
            with open(self.lastLocalDbUpdateTsFilePath,'r') as f:
                self.lastLocalDbUpdateTimestamp = datetime.strptime(f.read().strip(), self.LAST_UPDATE_TIMESTAMP_FORMAT)
        return self.lastLocalDbUpdateTimestamp
    
    def loadLocalDatabase(self):
        """Loads local database into memory."""
        if os.path.isfile(self.localDBFilePath):
            with open(self.localDBFilePath, 'r') as f:
                self.database = pickle.load(f)
        else:
            self.database = {}
            self._resetLocalDatabase()
    
    def _resetLocalDatabase(self):
        """Loads ALL possible price history into database.
        """
        self.updateItemDatabase()
        
        urls = [f"https://api.weirdgloop.org/exchange/history/{self.game}/all?compress=true&id={itemId}" for itemId in self.database]
        if DEBUG_MODE:
            urls = urls[:200]
        results = asyncio.run(getMultipleJsonRequests(urls=urls, maxRequestPerBatch=100, waitBetweenBatch=3, maxRetry=3))
        while results:
            url, js = results.popItem()
            if js:
                k = list(js.keys())
                if len(k) == 1:
                    # then convert to PriceHistory
                    phObj = self.database[int(js[k])]
                    for row in js[k]:
                        phObj.add(timestamp=row[0], price=row[1], volume=row[2] if len(row)>2 else None, src="all")
                else:
                    print(f"Failed to retreive json data from: {url}")

    def isUpdateAvailable(self) -> bool:
        """Abstract-ish: returns if there is a GE update available for this game.
        Returns:
            bool: if there is a GE update available for this game.
        """
        js = getJson("https://api.weirdgloop.org/exchange")
        self.lastLiveUpdate = datetime.strptime(js[self.game], GameData.LAST_UPDATE_TIMESTAMP_FORMAT)
        if self.lastLiveUpdate > self.lastLocalDbUpdateTimestamp:
            if self.isUpdateAvailableFunc:
                return self.isUpdateAvailableFunc(self)
            return True
        return False
    
    def periodicUpdate(self):
        """Abstract-ish: periodic update. Handles updating the database since the last run.
        """
        if self.periodicUpdateFunc:
            self.periodicUpdateFunc(self)
        else:
            raise NotImplementedError("Need to implement this function")
    
    def updateItemDatabase(self):
        """Abstract: Updates the items in the database. Does not delete unavailable items.
        Additional functions may be required by subclasses."""
        db = getJson(f"https://chisel.weirdgloop.org/gazproj/gazbot/{self.game[0]}s_dump.json")
        goodKeys = {"id","name","members","highalch","lowalch","value"}
        for badId in ['%JAGEX_TIMESTAMP%', '%UPDATE_DETECTED%']:
            if badId in db:
                del db[badId]
        for itemId in db:
            dct = {gk: db[itemId].get(gk) for gk in goodKeys}
            if itemId in self.database:
                dct.popitem('id')
                self.database[int(itemId)].updateMetadata(**dct)
            else:
                self.database[int(itemId)] = GEObject(**dct)

    def writeLocalDatabaseFiles(self):
        raise NotImplementedError("")

def isUpdateAvailableOSRS(gameObj:GameData) -> bool:
    """Specific for OSRS, retreives if there is an update available for this game
    Args:
        gameObj (GameData): the game object for this game
    Returns:
        bool: if game update is available for this game
    """
    js = getJson("https://prices.runescape.wiki/api/v1/osrs/latest")
    lastRealtimeLiveUpdate = datetime.fromtimestamp(max([a[k] for a in js['data'].values() for k in a if 'Time' in k and a[k]]))
    return lastRealtimeLiveUpdate > gameObj.lastLocalDbUpdateTimestamp

if __name__ == "__main__":
    games = {
        'rs': GameData('rs', None, None),
        'osrs': GameData('osrs', isUpdateAvailableOSRS, None)
    }
    for game in games:
        games[game].checkLastLocalDbUpdate()
        if games[game].isUpdateAvailable():
            games[game].loadLocalDatabase()
            games[game].periodicUpdate()
            games[game].writeLocalDatabaseFiles()
    print("?")


@profile    # DEBUG
def getNormalizedItemDB(game:str) -> dict:
    """
    Gets a list of items, their names, buy limits, (shop/alch) values, and is members info.
    Arguments:
        game (str) the game mode to get for (see: SUPPORTED_GAMES)
    RETURNS:
        dict: of the following key value pair schema:
            keys (str) the id.
            values: dictionary with the following schema:
                "id" (num),
                "name" (str) item name,
                "members" (bool),
                "highalch" (num),
                "lowalch" (num),
                "value" (num) the store value
    """
    r = wait_out_rate_limiter()
    db = r.json()


@profile    # DEBUG
def getNormalizedPriceData(game: str, itemId: str, historyLen:str='all') -> dict:
    """
    Gets normalized price data for the given item in the given game. 
    Args:
        game (str) the game code id (see: SUPPORTED_GAMES)
        itemId (str | int) the item ID to get
        historyLen (str) the history type to get. VALID values are: {
            'all'     -> all records of this data
            'last90d' -> up to the last 90 days of data (can be 0-90 long)
            'sample'  -> ~499 of randomly(?) selected records (fairly spaced out?)}
            
    Returns:
        dict: with the following key value pair schema:
            "all": Array of [timestamp {str}, price {num}, volume {num, optional}]
            "5m"|"1h" {Array, optional}: [timestamp {str}, avgHighPrice {num}, highPriceVolume {num}, avgLowPrice {num}, lowPriceVolume {num}]
            *Note*: timestamps have fmt "yy/mm/dd HH:MM"
            example: 
            getNormalizedPriceData("osrs",6) => {
                "all":[["2023/01/15 13:24",34],["2023/01/16 13:12",46,2827],...],
                "5m":[["2023/01/15 13:24",36,43,33,53],...]
                "1h":[["2023/01/15 13:24",36,43,33,53],...]
            }
    """
    game = str(game).lower()
    historyLen = str(historyLen).lower()
    assert game in SUPPORTED_GAMES, f"expected game in {SUPPORTED_GAMES}"
    assert historyLen in {'all', 'sample', 'last90d'}, "expected historyLen in {'all', 'sample', 'last90d'}"
    url = f"https://api.weirdgloop.org/exchange/history/{game}/{historyLen}?compress=true&id={itemId}"
    ret = {}
    try:
        ret["all"] = [[datetime.fromtimestamp(row[0]/1000).strftime("%y/%m/%d %H:%M"), *row[1:]] for row in wait_out_rate_limiter(url).json().get(str(itemId))]
    except Exception as e:
        print(game, "all", itemId, e)
        ret["all"] = [["err getting data for id", itemId]]
    if game == "osrs":
        for x in ["5m","1h"]:
            try:
                ret[x] =[[datetime.fromtimestamp(row.get("timestamp",0)).strftime("%y/%m/%d %H:%M"),  *[row.get(k) for k in { "avgHighPrice", "highPriceVolume", "avgLowPrice", "lowPriceVolume"}]] for row in wait_out_rate_limiter(f"https://prices.runescape.wiki/api/v1/osrs/timeseries?timestep={x}&id={itemId}").json().get("data",[])]
            except Exception as e:
                print(game, x, itemId, e)
                ret[x]=[[f"error getting {x} for id",itemId,itemId,itemId,itemId]]
    return ret

@profile    # DEBUG
def getGamesInNeedOfUpdate(lastUpdateTimes:dict) -> dict:
    """
    Gets dict of games that need to be updated.

    Args:
        lastUpdateTimes (dict): where keys are the SUPPORTED_GAMES and the values are the timestamps of the last local db update.

    Returns:
        dict: where keys are the SUPPORTED_GAMES in need of updates, and the values are the last update time of the live database.
    """
    assert len(SUPPORTED_GAMES - set(lastUpdateTimes.keys())) == 0, "lastUpdateTimes is malformed."
    r = wait_out_rate_limiter("https://api.weirdgloop.org/exchange").json()
    ret = {}
    for game in lastUpdateTimes:
        try:
            lastUpdateTime = datetime.strptime(r.get(game),"%Y-%m-%dT%H:%M:%S.%fZ")
            if lastUpdateTime > lastUpdateTimes[game]:
                ret[game] = lastUpdateTime
        except:
            pass
    return ret

@profile    # DEBUG
def getLastLocalDBUpdateTimes() -> dict:
    """
    Returns:
        dict: where keys are SUPPORTED_GAMES, and values are the last local db update time.
        *Note* failure to retreive last update time will return 2001/01/07 00:00.
    """
    ret = {}
    for game in SUPPORTED_GAMES:
        try:
            fn = f"{os.getcwd()}/data/{game}/UPDATE_TIMESTAMP"
            if not os.path.isfile(fn) and not os.path.isdir(f"{os.getcwd()}/data/{game}"):
                os.mkdir(f"{os.getcwd()}/data/{game}")
            with open(fn, 'r') as f:
                ret[game] = datetime.strptime(f.read().strip(), GAME_UPDATE_TIMESTAMP_DT_FORMAT)
        except:
            print(f"unable to get {game} last updated timestamp, setting to be updated")
            ret[game] = datetime(2001, 1, 7, 0, 0)  # midnight on Jan 7th, 2001
    return ret

@profile    # DEBUG
def updateLocalDatabases(game:str, database:dict, timestamp:datetime):
    """
    Updates the local files.
    Args:
        game (str): the game string. (see SUPPORTED_GAMES)
        database (dict): the database object
        timestamp (datetime): the timestamp of the update for the given game
    """
    game = str(game).lower()
    assert game in SUPPORTED_GAMES, f"expected game in {SUPPORTED_GAMES}"
    # update files
    # update the up to date timestamp
    try:
        DEBUG_WRITE_PY_DUMP(game, database)
    except:
        pass
    writeDbAsJson(game, database)
    writeDbAsTsv(game, database)
    # TODO: writeDbAsXml(game, database)
    writeUpdatedTs(game, timestamp)

def DEBUG_WRITE_PY_DUMP(game:str, database:dict):
    """Writes the database as a python dict file

    Args:
        game (str): game mode
        database (dict): game db
    """
    with open(f"{os.getcwd()}/data/{game}/data.py",'w') as f:
        f.write(repr(database))

@profile    # DEBUG
def writeDbAsJson(game:str, database:dict):
    """Writes the database as a json file

    Args:
        game (str): game mode
        database (dict): game db
    """
    fn = f"{os.getcwd()}/data/{game}/data.json"
    with open(fn, 'w') as f:
        json.dump(database, fp=f, indent=0)

@profile    # DEBUG
def writeDbAsTsv_SLOW(game:str, database:dict):
    """Writes database as single 2d csv file.

    Args:
        game (str): game mode
        database (dict): game db
    """
    fn = f"{os.getcwd()}/data/{game}/data.tsv"

    GOOGLE_SHEETS_MAX_CELL_LEN = 32000 - 10 # -10 for padding?
    def flattenPrices(data: list, maxLen:int, n:str='\n', v:str='\t') -> list:
        """Converts a dict of data into list of strings of max maxLen size.

        Args:
            data (list): the 2dlist of data to be converted
            maxLen (int): the max len of the strings
            n (str): delim for row/newline
            v (str): delim for col

        Returns:
            list<str>: list of strings (orderd by first col descending)
        """
        PADDING = '{}'
        
        ret = []
        currBlock = ""
        data = [v.join([str(x).replace('"','""').replace('\t',' ').replace('\n',' ') for x in row]) for row in data.sort(key=lambda l:l[0], reverse=True)]
        if len(data) > 1:
            PADDING = '"{}"'
        PADDING_LEN = len(PADDING.format(''))
        while data:
            row = data.pop()
            if len(currBlock) + len(row) + len(n) + PADDING_LEN < maxLen:
                currBlock = currBlock + n + row
            else:
                ret.append(PADDING.format(currBlock))
                currBlock = row
        if len(currBlock) > 0:
            ret.append(PADDING.format(currBlock))
        return ret

    # need to reformat the nested database
    # setup vars to compute flattened price columns
    rowDelim = "\n"
    colDelim = "\t"
    flattenedPricesMaxCols = {}
    for row in database:
        for k in row['price']:
            flattenedPricesMaxCols[k] = 0
        break
    # convert prices into columns of maxLen
    for row in database:
        for k in row['price']:
            row['price'][k] = flattenPrices(row['price'][k], maxLen=GOOGLE_SHEETS_MAX_CELL_LEN, n=rowDelim, v=colDelim)
            if len(row['price'][k]) > flattenedPricesMaxCols[k]:
                flattenedPricesMaxCols[k] = len(row['price'][k])
    
    # setup headers
    headers = ['id', 'name', 'members', 'value', 'highalch', 'lowalch',]
    for k in flattenedPricesMaxCols:
        headers += [f"{k}#{i}" for i in range(flattenedPricesMaxCols[k])] # or just f"{k}"?
    
    outContents = colDelim.join(headers)
    while database:
        outContents += rowDelim
        key, row = database.popitem()
        # format item metadata
        outContents += colDelim.join([row.get(h) for h in ['id', 'name', 'members', 'value', 'highalch', 'lowalch']])
        # format item prices
        for k in flattenedPricesMaxCols:
            outContents += colDelim + colDelim.join(row['price'][k] + ['']*(flattenedPricesMaxCols[k] - len(row['price'][k])))
    
    with open(fn, 'w') as f:
        f.write(outContents)

@profile    # DEBUG
def writeDbAsTsv(game:str, database:dict):
    """Writes database as single 2d csv file.

    Args:
        game (str): game mode
        database (dict): game db
    """
    fn = f"{os.getcwd()}/data/{game}/data.tsv"

    GOOGLE_SHEETS_MAX_CELL_LEN = 32000 - 10 # -10 for padding?
    @profile    # DEBUG
    def flattenPrices(data: list, maxLen:int, n:str='\n', v:str='\t') -> list:
        """Converts a dict of data into list of strings of max maxLen size.

        Args:
            data (list): the 2dlist of data to be converted
            maxLen (int): the max len of the strings
            n (str): delim for row/newline
            v (str): delim for col

        Returns:
            list<str>: list of strings (orderd by first col descending)
        """
        PADDING = '{}'
        
        ret = []
        currBlock = ""
        currBlockLen = 0
        currBlocks = []
        data = [v.join([str(x).replace('"','""').replace('\t',' ').replace('\n',' ') for x in row]) for row in data.sort(key=lambda l:l[0], reverse=True)]
        if len(data) > 1:
            PADDING = '"{}"'
        PADDING_LEN = len(PADDING.format(''))
        while data:
            row = data.pop()
            if currBlockLen + len(row)*len(currBlocks) + len(n) + PADDING_LEN < maxLen:
                currBlocks.append(row)
            else:
                ret.append(PADDING.format(n.join(currBlocks)))
                currBlocks = [row]
        if len(currBlock) > 0:
            ret.append(PADDING.format(n.join(currBlocks)))
        return ret

    # need to reformat the nested database
    # setup vars to compute flattened price columns
    rowDelim = "\n"
    colDelim = "\t"
    flattenedPricesMaxCols = {}
    for iid in database:
        for k in database[iid]['price']:
            flattenedPricesMaxCols[k] = 0
        break
    # convert prices into columns of maxLen
    for row in database:
        for k in database[row]['price']:
            database[row]['price'][k] = flattenPrices(database[row]['price'][k], maxLen=GOOGLE_SHEETS_MAX_CELL_LEN, n=rowDelim, v=colDelim)
            if len(database[row]['price'][k]) > flattenedPricesMaxCols[k]:
                flattenedPricesMaxCols[k] = len(database[row]['price'][k])
    
    # setup headers
    headers = ['id', 'name', 'members', 'value', 'highalch', 'lowalch',]
    for k in flattenedPricesMaxCols:
        headers += [f"{k}#{i}" for i in range(flattenedPricesMaxCols[k])] # or just f"{k}"?
    
    outContents = [headers]
    while database:
        key, row = database.popitem()
        # format item metadata
        line = [str(row.get(h)) for h in ['id', 'name', 'members', 'value', 'highalch', 'lowalch']]
        # format item prices
        for k in flattenedPricesMaxCols:
            line += row['price'][k] + ['']*(flattenedPricesMaxCols[k] - len(row['price'][k]))
        outContents.append(line)
    
    outContents = rowDelim.join(colDelim.join(line) for line in outContents)
    with open(fn, 'w') as f:
        f.write(outContents)

@profile    # DEBUG
def writeUpdatedTs(game:str, timestamp:datetime):
    """Writes the new (live) update time of the (local) database.

    Args:
        game (str): game str, see SUPPORTED_GAMES
        timestamp (str): timestamp value to write
    """
    fn = f"{os.getcwd()}/data/{game}/UPDATE_TIMESTAMP"
    with open(fn, 'w') as f:
        f.write(timestamp.strftime(GAME_UPDATE_TIMESTAMP_DT_FORMAT))

def run():
    """
    """
    # todo: optimize runtime, at least after the first run
    lastUpdateTimes = getLastLocalDBUpdateTimes()
    gamesToUpdate = getGamesInNeedOfUpdate(lastUpdateTimes)
    for game in gamesToUpdate:
        daysSinceLastSuccessfulUpdate = (gamesToUpdate[game] - lastUpdateTimes[game]).days
        historyLenToGet = 'all'
        if daysSinceLastSuccessfulUpdate < 90:
            historyLenToGet = 'last90d'
        if daysSinceLastSuccessfulUpdate < 2:
            historyLenToGet = 'one'
        database = GameData(game=game)
        database
        
        for itemId in tqdm.tqdm(database, desc=game):
            database[itemId]["price"] = getNormalizedPriceData(game, itemId, historyLenToGet)
        updateLocalDatabases(game, database, gamesToUpdate[game])


