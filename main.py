#coding:utf-8

import time
import traceback
import sys
import os
import _thread
import platform
from optparse import OptionParser
import logging

from shadowsocksR import SSRParse,SSR
from speedTest import SpeedTest,setInfo
from exportResult import ExportResult
import importResult
#from socks2http import ThreadingTCPServer,SocksProxy
#from socks2http import setUpstreamPort

from config import config

loggerList = []
loggerSub = logging.getLogger("Sub")
logger = logging.getLogger(__name__)
loggerList.append(loggerSub)
loggerList.append(logger)

formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(thread)d][%(filename)s:%(lineno)d]%(message)s")
fileHandler = logging.FileHandler(time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + ".log",encoding="utf-8")
fileHandler.setFormatter(formatter)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)

VERSION = "2.1 alpha"
LOCAL_ADDRESS = "127.0.0.1"
LOCAL_PORT = 1087

def setArgsListCallback(option,opt_str,value,parser):
	assert value is None
	value = []
	def floatable(arg):
		try:
			float(arg)
			return True
		except ValueError:
			return False
	for arg in parser.rargs:
		if (arg[:2] == "--" and len(arg) > 2):
			break
		if (arg[:1] == "-" and len(arg) > 1 and not floatable(arg)):
			break
		if (arg.replace(" ","") == ""):
			continue
		value.append(arg)
#	print(parser.values)
#	print(option.dest)
#	print(opt_str)
	del parser.rargs[:len(value)]
	setattr(parser.values,option.dest,value)
#	print(value)

def setOpts(parser):
	parser.add_option(
		"-c","--config",
		action="store",
		dest="guiConfig",
		default="",
		help="Load config generated by shadowsocksr-csharp."
		)
	parser.add_option(
		"-u","--url",
		action="store",
		dest="url",
		default="",
		help="Load ssr config from subscription url."
		)
	parser.add_option(
		"-m","--method",
		action="store",
		dest="test_method",
		default="socket",
		help="Select test method in [speedtestnet,fast,socket]."
		)
	parser.add_option(
		"-M","--mode",
		action="store",
		dest="test_mode",
		default="all",
		help="Select test mode in [all,pingonly]."
		)
	parser.add_option(
		"--include",
		action="callback",
		callback = setArgsListCallback,
		dest="filter",
		default = [],
		help="Filter nodes by group and remarks using keyword."
		)
	parser.add_option(
		"--include-remark",
		action="callback",
		callback = setArgsListCallback,
		dest="remarks",
		default=[],
		help="Filter nodes by remarks using keyword."
		)
	parser.add_option(
		"--include-group",
		action="callback",
		callback = setArgsListCallback,
		dest="group",
		default=[],
		help="Filter nodes by group name using keyword."
		)
	parser.add_option(
		"--exclude",
		action="callback",
		callback = setArgsListCallback,
		dest="efliter",
		default = [],
		help="Exclude nodes by group and remarks using keyword."
		)
	parser.add_option(
		"--exclude-group",
		action="callback",
		callback = setArgsListCallback,
		dest="egfilter",
		default=[],
		help="Exclude nodes by group using keyword."
		)
	parser.add_option(
		"--exclude-remark",
		action="callback",
		callback = setArgsListCallback,
		dest="erfilter",
		default = [],
		help="Exclude nodes by remarks using keyword."
		)
	parser.add_option(
		"-y","--yes",
		action="store_true",
		dest="confirmation",
		default=False,
		help="Skip node list confirmation before test."
		)
	parser.add_option(
		"-s","--split",
		action="store",
		dest="split_count",
		default="-1",
		help="Set the number of nodes displayed in a single image when exporting images."
		)
	parser.add_option(
		"-i","--import",
		action="store",
		dest="import_file",
		default="",
		help="Import test result from json file and export it."
		)
	parser.add_option(
		"--debug",
		action="store_true",
		dest="debug",
		default=False,
		help="Run program in debug mode."
		)
	parser.add_option(
		"--paolu",
		action="store_true",
		dest="paolu",
		default=False,
		help="如题"
		)

def export(Result,split = 0,exportOnly = False):
	er = ExportResult()
	if (not exportOnly):
		er.exportAsJson(Result)
	if (split > 0):
		i = 0
		id = 1
		while (i < len(Result)):
			_list = []
			for j in range(0,split):
				_list.append(Result[i])
				i += 1
				if (i >= len(Result)):
					break
			er.exportAsPng(_list,id)
			id += 1
	else:
		er.exportAsPng(Result)


def checkPlatform():
		tmp = platform.platform()
		if ("Windows" in tmp):
			return "Windows"
		elif("Linux" in tmp):
			return "Linux"
		else:
			return "Unknown"

if (__name__ == "__main__"):
	#setUpstreamPort(LOCAL_PORT)

	DEBUG = False
	CONFIG_LOAD_MODE = 0 #0 for import result,1 for guiconfig,2 for subscription url
	CONFIG_FILENAME = ""
	CONFIG_URL = ""
	IMPORT_FILENAME = ""
	FILTER_KEYWORD = []
	FILTER_GROUP_KRYWORD = []
	FILTER_REMARK_KEYWORD = []
	EXCLUDE_KEYWORD = []
	EXCLUDE_GROUP_KEYWORD = []
	EXCLUDE_REMARK_KEWORD = []
	TEST_METHOD = ""
	TEST_MODE = ""
	SPLIT_CNT = 0
	SKIP_COMFIRMATION = False

	parser = OptionParser(usage="Usage: %prog [options] arg1 arg2...",version="SSR Speed Tool " + VERSION)
	setOpts(parser)
	(options,args) = parser.parse_args()

	if (options.paolu):
		for root, dirs, files in os.walk(".", topdown=False):
			for name in files:
				try:
					os.remove(os.path.join(root, name))
				except:
					pass
			for name in dirs:
				try:
					os.remove(os.path.join(root, name))
				except:
					pass

	if (options.debug):
		DEBUG = options.debug
		for item in loggerList:
			item.setLevel(logging.DEBUG)
			item.addHandler(fileHandler)
			item.addHandler(consoleHandler)
	else:
		for item in loggerList:
			item.setLevel(logging.INFO)
			item.addHandler(fileHandler)
			item.addHandler(consoleHandler)

	if (logger.level == logging.DEBUG):
		logger.debug("Program running in debug mode")

	#print(options.test_method)
	if (options.test_method == "speedtestnet"):
		TEST_METHOD = "SPEED_TEST_NET"
	elif(options.test_method == "fast"):
		TEST_METHOD = "FAST"
	else:
		TEST_METHOD = "SOCKET"

	if (options.test_mode == "pingonly"):
		TEST_MODE = "TCP_PING"
	elif(options.test_mode == "all"):
		TEST_MODE = "ALL"
	else:
		logger.error("Invalid test mode : %s" % options.test_mode)
		sys.exit(1)
	

	if (options.confirmation):
		SKIP_COMFIRMATION = options.confirmation

	if (len(sys.argv) == 1):
		parser.print_help()
		exit(0)

	if (options.import_file):
		CONFIG_LOAD_MODE = 0
	elif (options.guiConfig):
		CONFIG_LOAD_MODE = 1
		CONFIG_FILENAME = options.guiConfig
	elif(options.url):
		CONFIG_LOAD_MODE = 2
		CONFIG_URL = options.url
	else:
		logger.error("No config input,exiting...")
		sys.exit(1)


	if (options.filter):
		FILTER_KEYWORD = options.filter
	if (options.group):
		FILTER_GROUP_KRYWORD = options.group
	if (options.remarks):
		FILTER_REMARK_KEYWORD = options.remarks

	if (options.efliter):
		EXCLUDE_KEYWORD = options.efliter
	#	print (EXCLUDE_KEYWORD)
	if (options.egfilter):
		EXCLUDE_GROUP_KEYWORD = options.egfilter
	if (options.erfilter):
		EXCLUDE_REMARK_KEWORD = options.erfilter

	logger.debug(
		"\nFilter keyword : %s\nFilter group : %s\nFilter remark : %s\nExclude keyword : %s\nExclude group : %s\nExclude remark : %s" % (
			str(FILTER_KEYWORD),str(FILTER_GROUP_KRYWORD),str(FILTER_REMARK_KEYWORD),str(EXCLUDE_KEYWORD),str(EXCLUDE_GROUP_KEYWORD),str(EXCLUDE_REMARK_KEWORD)
		)
	)

	if (int(options.split_count) > 0):
		SPLIT_CNT = int(options.split_count)

	if (options.import_file and CONFIG_LOAD_MODE == 0):
		IMPORT_FILENAME = options.import_file
		export(importResult.importResult(IMPORT_FILENAME),SPLIT_CNT,True)
		sys.exit(0)
#	exit(0)

	#socks2httpServer = ThreadingTCPServer((LOCAL_ADDRESS,FAST_PORT),SocksProxy)
	#_thread.start_new_thread(socks2httpServer.serve_forever,())
	#print("socks2http server started.")
	ssrp = SSRParse()
	if (CONFIG_LOAD_MODE == 1):
		ssrp.readGuiConfig(CONFIG_FILENAME)
	else:
		ssrp.readSubscriptionConfig(CONFIG_URL)
	ssrp.excludeNode([],[],config["excludeRemarks"])
	ssrp.filterNode(FILTER_KEYWORD,FILTER_GROUP_KRYWORD,FILTER_REMARK_KEYWORD)
	ssrp.excludeNode(EXCLUDE_KEYWORD,EXCLUDE_GROUP_KEYWORD,EXCLUDE_REMARK_KEWORD)
	ssrp.printNode()
	if (not SKIP_COMFIRMATION):
		if (TEST_MODE == "TCP_PING"):
			logger.info("Test mode : tcp ping only.")
		#	print("Your test mode is tcp ping only.")
		else:
			logger.info("Test mode : speed and tcp ping.\nTest method : %s." % TEST_METHOD)
		#	print("Your test mode : speed and tcp ping.\nTest method : %s." % TEST_METHOD)
		ans = input("Before the test please confirm the nodes,Ctrl-C to exit. (Y/N)")
		if (ans == "Y"):
			pass
		else:
			sys.exit(0)

	'''
		{
			"group":"",
			"remarks":"",
			"loss":0,
			"ping":0.01,
			"gping":0.01,
			"dspeed":10214441 #Bytes
		}
	'''
	Result = []
	retryList = []
	retryConfig = []
	retryMode = False

	ssr = SSR()

	if (checkPlatform() == "Windows" and TEST_MODE == "ALL"):
		configs = ssrp.getAllConfig()
		ssr.addConfig(configs)
		ssr.startSsr()
		setInfo(LOCAL_ADDRESS,LOCAL_PORT)
		time.sleep(1)
		while(True):
			config = ssr.getCurrrentConfig()
			if (not config):
				logger.error("Get current config failed.")
				time.sleep(2)
				continue
			_item = {}
			_item["group"] = config["group"]
			_item["remarks"] = config["remarks"]
			logger.info("Starting test for %s - %s" % (config["group"],config["remarks"]))
			time.sleep(1)
			try:
				st = SpeedTest()
				latencyTest = st.tcpPing(config["server"],config["server_port"])
				if (int(latencyTest[0] * 1000) != 0):
					time.sleep(1)
					testRes = st.startTest(TEST_METHOD)
					_item["dspeed"] = testRes[0]
					_item["maxDSpeed"] = testRes[1]
					time.sleep(1)
				else:
					_item["dspeed"] = 0
					_item["maxDSpeed"] = 0
				_item["loss"] = 1 - latencyTest[1]
				_item["ping"] = latencyTest[0]
				logger.info(
					"%s - %s - Loss:%s%% - TCP_Ping:%d - AvgSpeed:%.2fMB/s - MaxSpeed:%.2fMB/s" % (
						_item["group"],
						_item["remarks"],
						_item["loss"] * 100,
						int(_item["ping"] * 1000),
						_item["dspeed"] / 1024 / 1024,
						_item["maxDSpeed"] / 1024 / 1024
						)
					)
				Result.append(_item)
			except:
				logger.exception("")
				ssr.stopSsr()
			if (not ssr.nextWinConf()):
				break
			time.sleep(1)
	elif(checkPlatform() == "Linux" and TEST_MODE == "ALL"):
		config = ssrp.getNextConfig()
		while(True):
			setInfo(LOCAL_ADDRESS,LOCAL_PORT)
			_item = {}
			_item["group"] = config["group"]
			_item["remarks"] = config["remarks"]
			config["local_port"] = LOCAL_PORT
			config["server_port"] = int(config["server_port"])
			ssr.startSsr(config)
			logger.info("Starting test for %s - %s" % (_item["group"],_item["remarks"]))
			time.sleep(1)
			try:
				st = SpeedTest()
				latencyTest = st.tcpPing(config["server"],config["server_port"])
				if (latencyTest[0] != 0):
					time.sleep(1)
					testRes = st.startTest(TEST_METHOD)
					_item["dspeed"] = testRes[0]
					_item["maxDSpeed"] = testRes[1]
					time.sleep(1)
				else:
					_item["dspeed"] = 0
					_item["maxDSpeed"] = 0
				ssr.stopSsr()
				time.sleep(1)
			#	.print (latencyTest)
				_item["loss"] = 1 - latencyTest[1]
				_item["ping"] = latencyTest[0]
			#	_item["gping"] = st.googlePing()
				_item["gping"] = 0
				if ((int(_item["dspeed"]) == 0) and (retryMode == False)):
				#	retryList.append(_item)
					Result.append(_item)
				#	retryConfig.append(config)
				else:
					Result.append(_item)
				logger.info(
					"%s - %s - Loss:%s%% - TCP_Ping:%d - AvgSpeed:%.2fMB/s - MaxSpeed:%.2fMB/s" % (
						_item["group"],
						_item["remarks"],
						_item["loss"] * 100,
						int(_item["ping"] * 1000),
						_item["dspeed"] / 1024 / 1024,
						_item["maxDSpeed"] / 1024 / 1024
						)
					)
				#socks2httpServer.shutdown()
				#logger.debug("Socks2HTTP Server already shutdown.")
			except Exception:
				ssr.stopSsr()
				#socks2httpServer.shutdown()
				#logger.debug("Socks2HTTP Server already shutdown.")
				#traceback.print_exc()
				logger.exception("")
				sys.exit(1)
			ssr.stopSsr()
			if (retryMode):
				if (retryConfig != []):
					config = retryConfig.pop(0)
				else:
					config = None
			else:
				config = ssrp.getNextConfig()

			if (config == None):
				if ((retryMode == True) or (retryList == [])):
					break
				ans = str(input("%d node(s) got 0kb/s,do you want to re-test these node? (Y/N)" % len(retryList))).lower()
				if (ans == "y"):
				#	logger.debug(retryConfig)
					retryMode = True
					config = retryConfig.pop(0)
				#	logger.debug(config)
					continue
				else:
					for r in retryList:
						for s in range(0,len(Result)):
							if (r["remarks"] == Result[s]["remarks"]):
								Result[s]["dspeed"] = r["dspeed"]
								Result[s]["maxDSpeed"] = r["maxDSpeed"]
								Result[s]["ping"] = r["ping"]
								Result[s]["loss"] = r["loss"]
								break
					break
	
	if (TEST_MODE == "TCP_PING"):
		config = ssrp.getNextConfig()
		while (True):
			_item = {}
			_item["group"] = config["group"]
			_item["remarks"] = config["remarks"]
			config["server_port"] = int(config["server_port"])
			st = SpeedTest()
			latencyTest = st.tcpPing(config["server"],config["server_port"])
			_item["loss"] = 1 - latencyTest[1]
			_item["ping"] = latencyTest[0]
			_item["dspeed"] = -1
			_item["maxDSpeed"] = -1
			Result.append(_item)
			logger.info("%s - %s - Loss:%s%% - TCP_Ping:%d" % (_item["group"],_item["remarks"],_item["loss"] * 100,int(_item["ping"] * 1000)))
			config = ssrp.getNextConfig()
			if (config == None):break

	export(Result,SPLIT_CNT)
	time.sleep(1)
	ssr.stopSsr()


