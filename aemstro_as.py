import sys
import os
import re

def getRegisterFromName(s):
	if s[0]=="v":
		return int(s[1:])
	elif s[0]=="c":
		return int(s[1:])+16
	elif s[0]=="b":
		return int(s[1:])+120
	else:
		print("error : "+s+" is not a valid register name")

def assembleFormat1(d):
	return (d["opcode"]<<26)|((d["dst"]&0x7F)<<19)|((d["src1"]&0x7F)<<12)|((d["src2"]&0x7F)<<5)|(d["extid"]&0x1F);

def parseFormat1(s):
	operandFmt="[^\s,]*"
	p=re.compile("^\s*("+operandFmt+"),\s*("+operandFmt+"),\s*("+operandFmt+") \(([0-9]*)\)")
	r=p.match(s)
	if r:
		return {"dst" : getRegisterFromName(r.group(1)),
			"src1" : getRegisterFromName(r.group(2)),
			"src2" : getRegisterFromName(r.group(3)),
			"extid" : int(r.group(4))}
	else:
		print("encountered error while parsing instruction")

instList={}
fmtList=[(parseFormat1, assembleFormat1)]

instList["add"]={"opcode" : 0x00, "format" : 0}
instList["dp3"]={"opcode" : 0x01, "format" : 0}
instList["dp4"]={"opcode" : 0x02, "format" : 0}
instList["mul"]={"opcode" : 0x08, "format" : 0}
instList["max"]={"opcode" : 0x09, "format" : 0}
instList["min"]={"opcode" : 0x0A, "format" : 0}
instList["mov"]={"opcode" : 0x13, "format" : 0}

#makes copy pasting to hex editor easier
def printLE(v):
	print("%02X%02X%02X%02X"%(v&0xFF,(v>>8)&0xFF,(v>>16)&0xFF,(v>>24)&0xFF))

def parseInstruction(s):
	s=s.lower()
	p=re.compile("^\s*([^\s]*)(.*)")
	r=p.match(s)
	if r:
		name=r.group(1)
		if name in instList:
			fmt=instList[name]["format"]
			out=fmtList[fmt][0](r.group(2))
			if out:
				out["opcode"]=instList[name]["opcode"]
				v=fmtList[fmt][1](out)
				print(hex(v))
				printLE(v)
		else:
			print(name+" : no such instruction")
