/*******
* Script for interacting with the Old School RuneScape Wiki's realtime pricing API.
*
* Please feel free to discuss in #api-discussion in the wiki's discord server, https://discord.gg/runescapewiki (react in #welcome)
*
* Provides the following functions:
getLatestLowPrice(id)
getLatestLowTime(id)
getLatestHighPrice(id)
getLatestHighTime(id)
get5mLowPrice(id)
get5mLowVolume(id)
get5mHighPrice(id)
get5mHighVolume(id)
get5mTimestamp()
get1hLowPrice(id)
get1hLowVolume(id)
get1hHighPrice(id)
get1hHighVolume(id)
get1hTimestamp()
get5mTimeSeries(id)
get1hTimeSeries(id)
*
* See https://prices.runescape.wiki or https://oldschool.runescape.wiki/w/RuneScape:Real-time_Prices for more information on the realtime prices API.
*
* If you are looking for a script for the current market prices (from Jagex, for both OSRS and RS3), see https://runescape.wiki/w/User:Gaz_Lloyd/RSW_Exchange_API_for_Google_Sheets.js
*
* Usage:
* 1) Open a Google Sheet
* 2) Tools -> Script editor...
* 3) Replace the default empty function with this script (if you already have some other custom functions, probably best to make a new file)
* 4) Save the script (top bar icon, or ctrl-s)
* 5) Name the project (name it whatever, it doesn't matter)
* 6) The functions are now working in the spreadsheet
*
* @example
* An example spreadsheet using the functions is here: https://docs.google.com/spreadsheets/d/1mn8bpaOXZsQ5xjM34jtYeyNgiyGkfmLkdJmFKhayBv0/edit#gid=0
*
* Feel free to contact me if you have any questions:
* <gaz[at]weirdgloop.org>
* <@Gaz_Lloyd> on Twitter
* <@Gaz#7521> on Discord - or #wiki-tech in the wiki's server discord.gg/runescapewiki
* <User:Gaz Lloyd> on the RuneScape Wiki
* <Gaz Lloyd> or <Gaz L> in-game
*
* @author Gaz Lloyd
*/

const CACHE_STORE_TIMEOUT = 60 * 5; // 5 min, previously 90 sec
function hard_reset_all_caches() {
	var cache = CacheService.getScriptCache();
	cache.removeAll([
		'osrs-latest-low-price',
		'osrs-latest-low-time',
		'osrs-latest-high-price',
		'osrs-latest-high-time',
		'osrs-5m-low-price',
		'osrs-5m-low-vol',
		'osrs-5m-high-price',
		'osrs-5m-high-vol',
		'osrs-5m-timestamp',
		'osrs-1h-low-price',
		'osrs-1h-low-vol',
		'osrs-1h-high-price',
		'osrs-1h-high-vol',
		'osrs-1h-timestamp',
		'osrs-latest-high-vol',
		'osrs-latest-low-vol',
		'osrs-latest-timestamp'
	]);
	_cacheLatestData();
	_getData('osrs-latest-low-price', 'latest');
	_getData('osrs-latest-low-time', 'latest');
	_getData('osrs-latest-high-price', 'latest');
	_getData('osrs-latest-high-time', 'latest');
	_getData('osrs-5m-low-price', '5m');
	_getData('osrs-5m-low-vol', '5m');
	_getData('osrs-5m-high-price', '5m');
	_getData('osrs-5m-high-vol', '5m');
	_getData('osrs-5m-timestamp', '5m');
	_getData('osrs-1h-low-price', '1h');
	_getData('osrs-1h-low-vol', '1h');
	_getData('osrs-1h-high-price', '1h');
	_getData('osrs-1h-high-vol', '1h');
	_getData('osrs-1h-timestamp', '5m');

	// FORCE UPDATE TO SHEET
	var ss = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("PRICES DATA SOURCE");
	var formulas = ss.getRange(2, 3, 1, 19).getFormulas();
	ss.getRange(2, 3, 1, 19).setFormulas(formulas);
}

/**
* Gets and caches the data from the server for the latest endpoint
*
* Cached data is in the Script cache (`CacheService.getScriptCache()`) with the keys:
*   `osrs-latest-high-price`, `osrs-latest-high-time`, `osrs-latest-low-price`, and `osrs-latest-low-time`
* The data is stored as stringified JSON objects, of item id : value.
*
* Data is cached for configured seconds.
*
* @return {void}
*/
function _cacheLatestData() {
	var resp = UrlFetchApp.fetch('https://prices.runescape.wiki/api/v1/osrs/latest');
	var data = JSON.parse(resp.getContentText());
	var highs = {},
	lows = {},
	hightimes = {},
	lowtimes = {};
	for (i in data.data) {
		if (data.data.hasOwnProperty(i)) {
			highs[i] = data.data[i].high;
			lows[i] = data.data[i].low;
			hightimes[i] = data.data[i].highTime;
			lowtimes[i] = data.data[i].lowTime;
		}
	}
	var cache = CacheService.getScriptCache();
	cache.putAll({
		'osrs-latest-high-price': JSON.stringify(highs),
		'osrs-latest-low-price': JSON.stringify(lows),
		'osrs-latest-high-time': JSON.stringify(hightimes),
		'osrs-latest-low-time': JSON.stringify(lowtimes)
	}, CACHE_STORE_TIMEOUT);
}
const sizeOf = value => typeSizes[typeof value](value)/1000;
const typeSizes = {
	"undefined": () => 0,
	"boolean": () => 4,
	"number": () => 8,
	"string": item => 2 * item.length,
	"object": item => !item ? 0: Object
	.keys(item)
	.reduce((total, key) => sizeOf(key) + sizeOf(item[key]) + total, 0)
};
/**
* Gets and caches the data from the server for the average endpoints
*
* Cached data is in the Script cache (`CacheService.getScriptCache()`) with the keys:
*   `osrs-5m-high-price`, `osrs-5m-high-vol`, `osrs-5m-low-price`, and `osrs-5h-low-vol`
*   `osrs-1h-high-price`, `osrs-1h-high-vol`, `osrs-1h-low-price`, and `osrs-1h-low-vol`
* The data is stored as stringified JSON objects, of item id : value.
*
* Data is cached for configured seconds.
*
* @param {String} tp - the endpoint to fetch (5m or 1h)
* @return {void}
*/
function _cacheAverageData(tp) {
	var url = 'https://prices.runescape.wiki/api/v1/osrs/'+tp;
	var resp = UrlFetchApp.fetch(url);
	var data = JSON.parse(resp.getContentText());
	var highs = {},
	lows = {},
	highvols = {},
	lowvols = {};
	for (i in data.data) {
		if (data.data.hasOwnProperty(i)) {
			highs[i] = data.data[i].avgHighPrice;
			lows[i] = data.data[i].avgLowPrice;
			highvols[i] = data.data[i].highPriceVolume;
			lowvols[i] = data.data[i].lowPriceVolume;
		}
	}
	var cache = CacheService.getScriptCache();
	var vals = {};
	vals['osrs-'+tp+'-high-price'] = JSON.stringify(highs);
	vals['osrs-'+tp+'-low-price'] = JSON.stringify(lows);
	vals['osrs-'+tp+'-high-vol'] = JSON.stringify(highvols);
	vals['osrs-'+tp+'-low-vol'] = JSON.stringify(lowvols);
	vals['osrs-'+tp+'-timestamp'] = ''+data.timestamp;
	cache.putAll(vals, CACHE_STORE_TIMEOUT);

}

/**
* Gets the data from the cache, invoking the above cache functions if necessary. The cache is then parsed from a string into an object.
*
* @param {String} key - the cache key to return
* @param {String} tp - the cache type (latest, 1h, 5m)
* @return {Object} - the cache
*/
function _getData(key, tp) {
	var cache = CacheService.getScriptCache();
	var val = cache.get(key);
	if (val == null) {
		if (tp == 'latest') {
			_cacheLatestData();
		} else {
			_cacheAverageData(tp);
		}
		val = cache.get(key);
	}
	return JSON.parse(val);
}

function getAllRecentGEInfo(key) {
	if (key == null) {
		return ["LatestLowPrice",
			"LatestHighPrice",
			"LatestLowTime",
			"LatestHighTime",
			"1hLowVolume",
			"1hHighVolume",
			"5mLowVolume",
			"5mHighVolume"
		];
	}
	return [getLatestLowPrice(key),
		getLatestHighPrice(key),
		getLatestLowTime(key),
		getLatestHighTime(key),
		get1hLowVolume(key),
		get1hHighVolume(key),
		get5mLowVolume(key),
		get5mHighVolume(key)
	];
	/*
	if (typeof key === "number") {
		// gets all values via the ID.



	} else if (typeof key === "string") {
		// convert to the ID.
		var k = parseInt(key);
		if (k.toString() == key) {
			// if its the full number
			return getAllRecentGEInfo(k);
		} else {
			// get id of the item given
			var dbsheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("ITEMS DB");
			var db = dbsheet.getSheetValues(1, 1, dbsheet.getLastRow() - 1, dbsheet.getLastColumn() - 1);
			for (var i = 0; i < db.length; ++i) {
				if (db[i][0].trim().toLowerCase() == key.trim().toLowerCase()) {
					return getAllRecentGEInfo(db[i][1]);
				}
			}
		}
	} else if (Array.isArray(key)) {
		var ret = [['LatestLowPrice',
			'LatestHighPrice',
			'LatestLowTime',
			'LatestHighTime',
			'1hLowVolume',
			'1hHighVolume',
			'5mLowVolume',
			'5mHighVolume']];
		for (var i = 0; i < key.length; ++i) {
			ret.push(getAllRecentGEInfo(key[i]));
		}
		return ret;
	}
	*/
}

/******************
LATEST
*******************/

/**
* Gets either a single value or a list of values
*/
function _getValsByIds(id, data) {
	if (typeof id === "number" || typeof id === "string") {
		return data[''+id];
	} else if (Array.isArray(id)) {
		var ret = [];
		for (var i = 0; i < id.length; ++i) {
			ret.push(_getValsByIds(id[i], data));
		}
		return ret;
	}
}

/**
* converts the given unix number to a local time string.
*/
function _unixToTimestampStr(unix) {
	switch (typeof unix) {
		case "number":
			return new Date(unix * 1000).toLocaleString("en-us").replace(",", "");
		case "string":
			return new Date(parseInt(unix) * 1000).toLocaleString("en-us").replace(",", "");
		case "object":
			var ret = [];
			for (var i = 0; i < unix.length; ++i) {
				ret.push(_unixToTimestampStr(unix[i]));
			}
			return ret;
		default:
			return null;
	}

}

/**
* Gets the latest low price
*
* @param {Integer} id - the item ID
* @return {Integer} - the low price
*/
function getLatestLowPrice(id) {
	var info = _getData('osrs-latest-low-price', 'latest');
	return _getValsByIds(id, info);
}

/**
* Gets the latest low time
*
* @param {Integer} id - the item ID
* @return {Integer} - the low time
*/
function getLatestLowTime(id) {
	var info = _getData('osrs-latest-low-time', 'latest');
	return _unixToTimestampStr(_getValsByIds(id, info));
}

/**
* Gets the latest high price
*
* @param {Integer} id - the item ID
* @return {Integer} - the high price
*/
function getLatestHighPrice(id) {
	var info = _getData('osrs-latest-high-price', 'latest');
	return _getValsByIds(id, info);
}

/**
* Gets the latest high time
*
* @param {Integer} id - the item ID
* @return {Integer} - the high time
*/
function getLatestHighTime(id) {
	var info = _getData('osrs-latest-high-time', 'latest');
	return _unixToTimestampStr(_getValsByIds(id, info));
}


/******************
5m
*******************/
/**
* Gets the 5m average low price
*
* @param {Integer} id - the item ID
* @return {Integer} - the low price
*/
function get5mLowPrice(id) {
	var info = _getData('osrs-5m-low-price', '5m');
	return _getValsByIds(id, info);
}

/**
* Gets the 5m volume at the low price
*
* @param {Integer} id - the item ID
* @return {Integer} - the low volume
*/
function get5mLowVolume(id) {
	var info = _getData('osrs-5m-low-vol', '5m');
	return _getValsByIds(id, info);
}

/**
* Gets the 5m average high price
*
* @param {Integer} id - the item ID
* @return {Integer} - the high price
*/
function get5mHighPrice(id) {
	var info = _getData('osrs-5m-high-price', '5m');
	return _getValsByIds(id, info);
}

/**
* Gets the 5m volume at the high price
*
* @param {Integer} id - the item ID
* @return {Integer} - the high volume
*/
function get5mHighVolume(id) {
	var info = _getData('osrs-5m-high-vol', '5m');
	return _getValsByIds(id, info);
}

/**
* Gets the timestamp of the 5m average data
*
* @return {Integer} - the timestamp
*/
function get5mTimestamp() {
	return _getData('osrs-5m-timestamp', '5m');
}

/******************
1h
*******************/
/**
* Gets the 1h average low price
*
* @param {Integer} id - the item ID
* @return {Integer} - the low price
*/
function get1hLowPrice(id) {
	var info = _getData('osrs-1h-low-price', '1h');
	return _getValsByIds(id, info);
}

/**
* Gets the 1h at the low price
*
* @param {Integer} id - the item ID
* @return {Integer} - the low volume
*/
function get1hLowVolume(id) {
	var info = _getData('osrs-1h-low-vol', '1h');
	return _getValsByIds(id, info);
}

/**
* Gets the 1h average high price
*
* @param {Integer} id - the item ID
* @return {Integer} - the high price
*/
function get1hHighPrice(id) {
	var info = _getData('osrs-1h-high-price', '1h');
	return _getValsByIds(id, info);
}

/**
* Gets the 1h volume at the high price
*
* @param {Integer} id - the item ID
* @return {Integer} - the high volume
*/
function get1hHighVolume(id) {
	var info = _getData('osrs-1h-high-vol', '1h');
	return _getValsByIds(id, info);
}

/**
* Gets the timestamp of the 1h average data
*
* @return {Integer} - the timestamp
*/
function get1hTimestamp() {
	return _getData('osrs-1h-timestamp', '5m');
}


/*****************
* time series
*****************/

/**
* Fetches the time series data from the server, and formats it.
*
* @param {Integer} id - the item ID to fetch
* @param {String} tp - the time series type (1h or 5m)
* @return {Array<Array<Integer>>} - The time series data, formatted to be returned to the sheet
*/
function _loadTimeSeries(id, tp) {
	if (!(tp === "5m" || tp === "1h" || tp === "6h")) {
		return "invalid time series type, expected one of: '5m', '1hr', or '6hr'";
	}
	var resp = UrlFetchApp.fetch('https://prices.runescape.wiki/api/v1/osrs/timeseries?timestep='+tp+'&id='+id);
	var data = JSON.parse(resp.getContentText());
	var out = [];
	for (var i = 0; i < 300; i++) {
		var d = data.data[''+i];
		out.push([
			d.timestamp,
			d.avgHighPrice,
			d.highPriceVolume,
			d.avgLowPrice,
			d.lowPriceVolume
		]);
	}
	return out;
}

/**
* Loads the 5m time series data for an item
*
* Data is returned filling up 5 columns and 300 rows, where the columns are:
*   timestamp, average high price, high price volume, average low price, low price volume
*
* @param {Integer} id - the item ID
* @return {Array<Array<Integer>>} - the time series data, formatted to be a 5x300 table.
*/
function get5mTimeSeries(id) {
	return _loadTimeSeries(id, '5m');
}

/**
* Loads the 1h time series data for an item
*
* Data is returned filling up 5 columns and 300 rows, where the columns are:
*   timestamp, average high price, high price volume, average low price, low price volume
*
* @param {Integer} id - the item ID
* @return {Array<Array<Integer>>} - the time series data, formatted to be a 5x300 table.
*/
function get1hTimeSeries(id) {
	return _loadTimeSeries(id, '1h');
}

/**
* @param {array{number}} data - the data to parse
* @param {float} threshold - estimated percent (0.00 to 1.00, exclusive) for expected number of data points to not be removed
* @return {Array<number>} - the subset of input data that meet within the threshold limitations
*/
function removeOutliers(data, threshold) {
	const defaultThresh = 0.95;
	// fix threshold value
	threshold = parseFloat(threshold);
	if (threshold <= 0) {
		threshold = defaultThresh; // % of expexted in range = 1 - (1/{threshold}^2)
	} else if (threshold > 1) {
		if (threshold >= 100) {
			threshold = defaultThresh;
		} else {
			threshold = threshold / 100;
		}
	}
	var mean = (data.reduce((a, b) => parseFloat(a) + parseFloat(b))) / data.length;
	var ssd = Math.sqrt(data.map(x => Math.pow(x - mean, 2)).reduce((a, b) => parseFloat(a) + parseFloat(b)) / (data.length-1));
	var ssdMult = 1 / Math.sqrt(1-threshold);
	var filtered = data.filter(v => Math.abs(v - mean) <= (ssdMult * ssd));

	return filtered;
}

/**
* Fetches the time series data from the server and analyzies it for if it should be bought or sold
*
* @param {Integer} id - the item ID to fetch
* @param {String} tp - the time series type (1h or 5m)
* @return {Array<Array<Integer>>} - The time series data, formatted to be returned to the sheet
*/
function currPriceTimeSeriesPercentile(id, tp, outlierThresh) {
	if (!(tp === "5m" || tp === "1h" || tp === "6h")) {
		return "invalid time series type, expected one of: '5m', '1hr', or '6hr'";
	}
	var resp = UrlFetchApp.fetch('https://prices.runescape.wiki/api/v1/osrs/timeseries?timestep='+tp+'&id='+id);
	var data = JSON.parse(resp.getContentText());
	var prices = [];

	for (var i = 0; i < data.data.length; i++) {
		var d = data.data[''+i];
		prices.push(
			(d.avgHighPrice * d.highPriceVolume
				+ d.avgLowPrice * d.lowPriceVolume)
			/
			(d.highPriceVolume + d.lowPriceVolume)
		);
	}
	var last_key = '' + data.data.length - 1;
	var last_25_days = [...prices.slice(25)].sort(function(a, b) {
		return a - b;
	});
	var last_75_days = [...prices].sort(function(a, b) {
		return a - b;
	});
	var curr_vol = data.data[last_key].highPriceVolume + data.data[last_key].lowPriceVolume;
	var curr_avg_price = (
		data.data[last_key].avgHighPrice * data.data[last_key].highPriceVolume
		+ data.data[last_key].avgLowPrice * data.data[last_key].lowPriceVolume)
	/ (curr_vol);

	var l25clean = removeOutliers (last_25_days, outlierThresh);
	var l75clean = removeOutliers (last_75_days, outlierThresh);
	//Logger.log((last_25_days.length - l25clean.length) + " removed from L25 for " + id);

	var price_percentile_25 = _binSearchInsertFindPercentile(l25clean, curr_avg_price);
	var price_percentile_75 = _binSearchInsertFindPercentile(l75clean, curr_avg_price);
	return [curr_avg_price,
		l25clean[0],
		l25clean[l25clean.length-1],
		l75clean[0],
		l75clean[l75clean.length-1],
		price_percentile_25,
		price_percentile_75,
		l25clean[l25clean.length-1] - l25clean[0],
		l75clean[l75clean.length-1] - l75clean[0]];
}

function _binSearchInsertFindPercentile (arr, val) {
	var start = 0;
	var end = arr.length - 1;
	var mid = Math.floor((start + end)/2);
	// Iterate while start not meets end
	while (start <= end) {
		mid = Math.floor((start + end)/2);
		if (arr[mid] < val)
			start = mid + 1;
		else if (arr[mid] > val)
			end = mid - 1;
		else //if (arr[mid] === val)
			break;
	}
	var percentile = (mid / arr.length) * 100;
	return percentile;
}
