import struct
import os
import sys
 
input={}
# '''0x0 : "vertex.position",
# 0x1 : "vertex.texcoord",
# 0x4 : "vertex.color?"}'''
 
output={}
# {0x0 : "glPosition",
# 0x2 : "glTexcoord",
# 0x4 : "glTexcoord",
# 0x6 : "glColor?",
# 0x8 : "glTexcoord?"}
 
def getWord(b, k, n=4):
	return sum(list(map(lambda c: b[k+c]<<(c*8),range(n))))

def convFloat24(f):
	#seee eeee mmmm mmmm mmmm mmmm
	if f==0x0:
		return 0.0
	s=f>>23
	e=(f>>16)&0x7F
	m=f&0xffff
	x=pow(2.0,e-63)*(1 + m*pow(2.0,-16))
	if f&0x800000!=0:
		return -x
	return x

# # doesn't quite work, but could be a more accurate approach ?
# def convFloat24(val):
#	if val==0x0:
#		return 0.0
#	tmp=((val>>16)&0xFF)+0x40
#	out=(tmp<<23)|((val&0x800000)<<31)|((val&0xFFFF)<<7)
#	try:
#		return (struct.unpack("f",struct.pack("I",out)))[0]
#	except:
#		return (val)

def parseSymbol(b,o):
	len=0
	while getWord(b,o+len,1)!=0x00:
		len+=1
	return(b[o:o+len].decode("ascii"))

def parseExtTable(data):
	l=len(data)
	out=[]
	for i in range(0,l,8):
		out+=[(getWord(data, i), getWord(data, i+0x4))]
	return out

def getRegisterNameSRC1(v):
	return ("r%02X"%(v))
	if v<0x20:
		return "v"+str(v&0xF)
	else:
		return "c"+str(v-0x20)

def getRegisterNameSRC2(v):
	return ("r%02X"%(v))
	# if v<0x20:
	# 	return "v"+str(v&0xF)
	# elif v<0x6D:
	# 	return "c"+str(v-0x20)
	# else:
	# 	return "r"+str(v-0x6D)
	if v<0x20:
		return "v"+str(int(v/4))
	elif v<0x6D:
		return "c"+str(v>>1)
	else:
		return "r"+str(v-0x6D)

def getRegisterNameDST(v):
	return ("r%02X"%(v))
	if v<0x20:
		return "o"+str((v&0xF)>>2)
	elif v<0x6D:
		return "c"+str(v-0x20)
	else:
		return "r"+str(v-0x6D)

def getRegisterName(v):
	return ("r%02X"%(v))
	# if v<16:
	# 	return "v"+str(v&0xF)
	# elif v<120:
	# 	return "c"+str(v-16)
	# else:
	# 	return "b"+str(v-0x88)

def getValue(v, t):
	return t[v] if v in t else getRegisterName(v)

def getInputSymbol(v, vt, ut):
	if v in vt:
		return vt[v]
	elif v in ut:
		return "("+",".join(["%.2f"%k for k in ut[v]])+")"
	else:
		return getValue(v, input)

def getOutputSymbol(v, ot):
	return getValue(v, ot)

def getLabelSymbol(v, t):
	return t[v][1] if v in t else hex(v)

def initIndent():
	global numIdent
	numIdent=0

def indentOut():
	global numIdent
	numIdent=numIdent+1

def unindentOut():
	global numIdent
	numIdent=numIdent-1

def iprint(s, e=False):
	global numIdent
	if e:
		print("	"*numIdent+s,end='')
	else:
		print("	"*numIdent+s)

comp=["x", "y", "z", "w"]
def parseComponentMask(v):
	out=""
	for i in range(4):
		if v&(1<<(3-i))!=0x0:
			out+=comp[i]
		else:
			out+="_"
	return out

def parseExt(v):
	return {"src1"    : (v>>5)&0xFF,
			"src2"    : (v>>14)&0xFF,
			"dst"     : (v)&0x1F,
			"dstcomp" : parseComponentMask(v&0xF)}
 
def parseComponentSwizzle(v):
	out=""
	for i in range(4):
		out+=comp[(v>>((3-i)*2))&0x3]
	return out

def parseInstFormat1(v):
	return {"opcode" : v>>26,
			# "src2"   : (v>>5)&0x7F,
			"src2"   : (v>>7)&0x1F,
			# "src1"   : (v>>12)&0x7F,
			"src1"   : (v>>12)&0xFF,
			# "dst"    : (v>>19)&0x7F,
			"dst"    : (v>>21)&0x1F,
			# "extid"  : (v)&0x1F}
			"extid"  : (v)&0x7F}

def parseInstFormat2(v):
	return {"opcode" : v>>26,
			"addr"   : (v>>8)&0x3FFC,
			"flags"  : (v>>22)&0x3F,
			"ret"    : (v)&0x3FF}
#?
def parseInstFormat3(v):
	return {"opcode" : v>>26,
			"src2"   : (v>>0)&0x7F,
			"src1"   : (v>>7)&0x7F,
			"dst"    : (v>>14)&0x7F}
# MOV?
def parseInstFormat4(v):
	return {"opcode" : v>>26,
			"src1"   : (v>>7)&0x7F,
			"dst"    : (v>>14)&0x7F,
			"extid"    : (v)&0x3F}
# CONDJUMP
def parseInstFormat5(v):
	return {"opcode" : v>>26,
			"addr"   : (v>>8)&0x3FFC,
			"bool"  : (v>>22)&0xF,
			"ret"    : (v)&0x3FF}

def outputStringList(strl, fmtl):
	l=len(strl)
	out=""
	if l==len(fmtl):
		for i in range(l):
			str=strl[i]
			fmt=fmtl[i]
			if fmt:
				v=len(str)
				if v<fmt:
					str+=" "*(fmt-v)
			out+=str
	iprint(out)


def printInstFormat1(n, inst, e, lt, vt, ut, ot):
	ext=e[inst["extid"]][0]
	extd=parseExt(ext)
	outputStringList([n,
					# getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"],
					getRegisterNameDST(inst["dst"])+"."+extd["dstcomp"],
					" <- ",
					# getInputSymbol(inst["src1"], vt[0], ut)+"."+(parseComponentSwizzle(extd["src1"])),
					getRegisterNameSRC1(inst["src1"])+"."+(parseComponentSwizzle(extd["src1"])),
					" , ",
					# getInputSymbol(inst["src2"], vt[1], ut)+"."+(parseComponentSwizzle(extd["src2"])),
					getRegisterNameSRC2(inst["src2"])+"."+(parseComponentSwizzle(extd["src2"])),
					" ("+hex(inst["extid"])+")"],
					[8, 16, None, 16, None, 16, None])

def printInstFormat4(n, inst, e, lt, vt, ut, ot):
	ext=e[inst["extid"]][0]
	extd=parseExt(ext)
	outputStringList([n,
					# getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"],
					getRegisterNameDST(inst["dst"])+"."+extd["dstcomp"],
					" <- ",
					# getInputSymbol(inst["src1"], vt[0], ut)+"."+(parseComponentSwizzle(extd["src1"])),
					getRegisterNameSRC1(inst["src1"])+"."+(parseComponentSwizzle(extd["src1"])),
					"   ", "",
					" ("+hex(inst["extid"])+")"],
					[8, 16, None, 16, None, 16, None])

def printInstFormat2(n, inst, e, lt, vt, ut, ot):
	iprint(n + " "*(7-len(n)) +
			getLabelSymbol(inst["addr"], lt)+
			" ("+str(inst["ret"])+ " words, flags: "+bin(inst['flags'])+")")

# CONDJUMP
def printInstFormat5(n, inst, e, lt, vt, ut, ot):
	outputStringList([n,
					getLabelSymbol(inst["addr"], lt),
					" ,  ",
					getInputSymbol((inst['bool']&0xF)+0x88, vt[2], ut),
					"   ", "",
					" ("+str(inst["ret"])+ " words, "+str(inst['bool']&0xF)+")"],
					[8, 16, None, 16, None, 16, None])

instList={}
# fmtList=[(parseInstFormat1, printInstFormat1), (parseInstFormat2, printInstFormat2), (parseInstFormat2, printInstFormat2), (parseInstFormat4, printInstFormat4)]
fmtList=[(parseInstFormat1, printInstFormat1), (parseInstFormat2, printInstFormat2), (parseInstFormat2, printInstFormat2), (parseInstFormat1, printInstFormat4), (parseInstFormat5, printInstFormat5)]

instList[0x00]={"name" : "ADD", "format" : 0}
instList[0x01]={"name" : "DP3", "format" : 0}
instList[0x02]={"name" : "DP4", "format" : 0}
instList[0x08]={"name" : "MUL", "format" : 0}
instList[0x09]={"name" : "MAX", "format" : 0}
instList[0x0A]={"name" : "MIN", "format" : 0}
instList[0x13]={"name" : "MOV", "format" : 3}
instList[0x24]={"name" : "CALL", "format" : 1}
instList[0x25]={"name" : "CALL", "format" : 1}
instList[0x26]={"name" : "CALLC", "format" : 4} #conditional call (uniform bool)
instList[0x27]={"name" : "IFU", "format" : 4} #conditional jump (uniform bool)
instList[0x2e]={"name" : "CMP?", "format" : 0}

def parseCode(data, e, lt, vt, ut, ot):
	l=len(data)
	for k in range(0,l,4):
		v=getWord(data,k)
		opcode=v>>26

		if k in lt:
			iprint("%08x [--------] "%(k), True)
			iprint(lt[k][1]+":")

		iprint("%08x [%08x]	"%(k,v), True)

		if opcode in instList:
			fmt=instList[opcode]["format"]
			inst=fmtList[fmt][0](v)
			fmtList[fmt][1](instList[opcode]["name"], inst, e, lt, vt, ut, ot)
		elif opcode==0x21:
			iprint("END")
		elif opcode==0x22:
			iprint("FLUSH")
		# elif opcode==0x2e:
		# 	inst=parseInstFormat1(v)
		# 	ext=e[inst["extid"]][0]
		# 	extd=parseExt(ext)
		# 	iprint("CMP?   "+
		# 	       getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"]+
		# 	       "   <-	"+
		# 	       getInputSymbol(inst["src1"], vt[0], ut)+"."+(parseComponentSwizzle(extd["src1"]))+
		# 		" ("+hex(inst["extid"])+", src2: "+hex(inst["src2"])+")")
		elif  opcode==0x28:
			inst=parseInstFormat2(v)
			addr=inst["addr"]
			iprint("IF?    "+getLabelSymbol(inst["addr"], lt)+
			       " ("+str(inst["ret"])+ " words, flags: "+bin(inst['flags'])+" "+hex(inst['flags'])+")")
		elif opcode==0x2A:
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("EMITV? "+
			       getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], vt[0], ut)+"."+(parseComponentSwizzle(extd["src1"]))+
			       "   .   "+
			       getInputSymbol(inst["src2"], vt[1], ut)+"."+(parseComponentSwizzle(extd["src2"]))+
			       " ("+hex(inst["extid"])+")")
		elif opcode==0x2D:
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("SUB?   "+
			       getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], vt[0], ut)+"."+(parseComponentSwizzle(extd["src1"]))+
			       "   .   "+
			       getInputSymbol(inst["src2"], vt[1], ut)+"."+(parseComponentSwizzle(extd["src2"]))+
			       " ("+hex(inst["extid"])+")")
		else:
			inst=parseInstFormat1(v)
			if inst["extid"] < len(e):
				ext=e[inst["extid"]][0]
				extd=parseExt(ext)
				outputStringList(["???",
					# getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"],
					getRegisterNameDST(inst["dst"])+"."+extd["dstcomp"],
					" <- ",
					# getInputSymbol(inst["src1"], vt[0], ut)+"."+(parseComponentSwizzle(extd["src1"])),
					getRegisterNameSRC1(inst["src1"])+"."+(parseComponentSwizzle(extd["src1"])),
					" , ",
					# getInputSymbol(inst["src2"], vt[1], ut)+"."+(parseComponentSwizzle(extd["src2"])),
					getRegisterNameSRC2(inst["src2"])+"."+(parseComponentSwizzle(extd["src2"])),
					" ("+hex(inst["extid"])+")"],
					[8, 16, None, 16, None, 16, None])
			else:
				inst=parseInstFormat3(v)
				iprint("???    "+
				       getOutputSymbol(inst["dst"], ot)+
				       "   <-	"+
				       getInputSymbol(inst["src1"], vt[0], ut)+
				       "   .   "+
				       getInputSymbol(inst["src2"], vt[1], ut)+
				       " (invalid extension id)")

		k+=0x4

def parseDVLP(data, lt, vt, ut, ot):
	l=len(data)
	extOffset=getWord(data, 0x10)
	extSize=getWord(data, 0x14)*8
	ext=parseExtTable(data[extOffset:(extOffset+extSize)])
	codeOffset=getWord(data, 0x8)
	codeSize=getWord(data, 0xC)*4
	parseCode(data[codeOffset:(codeOffset+codeSize)], ext, lt, vt, ut, ot)

def parseLabelTable(data, sym):
	l=len(data)
	out={}
	for i in range(0,l,0x10):
		id=getWord(data,i,1)
		loc=getWord(data,i+0x4)*4
		off=getWord(data,i+0xC)
		out[loc]=(id,parseSymbol(sym,off))
	return out

#dirty, waiting to find real transform
def transformRegisterValue(v):
	if v<16:
		return (v&0xF)
	# elif v<120:
	# 	return v+16
	# else:
	# 	return -1
	return v+16


def parseVarTable(data, sym):
	l=len(data)
	iprint("Uniforms :")
	indentOut()
	src1={}
	src2={}
	srcb={}
	for i in range(0,l,0x8):
		off=getWord(data,i)
		v1=getWord(data,i+4,2)
		v2=getWord(data,i+6,2)

		base=transformRegisterValue(v1)
		end=transformRegisterValue(v2)

		# iprint(getRegisterName(v1)+" - "+getRegisterName(v2)+" : "+parseSymbol(sym,off))
		iprint(getRegisterNameSRC1(base)+" - "+getRegisterNameSRC1(end)+" : "+parseSymbol(sym,off))
		for k in range(base, end+1):
			name=parseSymbol(sym,off)+"["+str(k-base)+"]"
			if k<0x20:
				src1[k/4]=name
				src2[k]=name
			# else:
			# 	src1[k]=name
			if k>=0x88:
				srcb[k]=parseSymbol(sym,off)

	unindentOut()
	print("")
	return (src1,src2,srcb)

def parseConstTable(data, sym):
	l=len(data)
	iprint("Constants :")
	indentOut()
	out={}
	for i in range(0,l,0x14):
		# r=transformRegisterValue(getWord(data,i+2,2))
		r=getWord(data,i+2,2)+0x20
		vec=[convFloat24(getWord(data,i+k)) for k in range(4,0x14,4)]
		# iprint(getRegisterName(r)+" = "+str(vec))
		iprint(getRegisterNameSRC1(r)+" = "+str(vec))
		out[r]=vec

	unindentOut()
	print("")
	return out

outputTypes={0x0 : "result.position",
			0x2 : "result.color",
			0x3 : "result.texcoord0",
			0x5 : "result.texcoord1",
			0x6 : "result.texcoord2",
			0x8 : "result.view"}

def parseOutputTable(data, sym):
	l=len(data)
	iprint("Output :")
	indentOut()
	out={}
	for i in range(0,l,0x8):
		off=getWord(data,i+4)
		v1=getWord(data,i,2)
		v2=getWord(data,i+2,2)

		if v1 in outputTypes:
			out[v2*4]=outputTypes[v1]

		iprint("o"+str(v2)+" = "+(outputTypes[v1] if v1 in outputTypes else hex(v1))+" ("+hex(off)+")")

	unindentOut()
	print("")
	return out

def parseDVLE(data,dvlp, k):
	l=len(data)

	iprint("DVLE "+str(k))

	shaderType=getWord(data, 0x6, 1)
	mainStart=getWord(data, 0x8)*4
	mainEnd=getWord(data, 0xC)*4

	iprint("vertex shader" if shaderType==0x0 else "geometry shader")
	iprint("main : "+hex(mainStart)+"-"+hex(mainEnd))
	print("")

	codeStartOffset=getWord(data, 0x8)
	codeEndOffset=getWord(data, 0xC)

	unifOffset=getWord(data, 0x18)
	unifSize=getWord(data, 0x1C)*0x14

	labelOffset=getWord(data, 0x20)
	labelSize=getWord(data, 0x24)*0x10

	outputOffset=getWord(data, 0x28)
	outputSize=getWord(data, 0x2C)*0x8

	varOffset=getWord(data, 0x30)
	varSize=getWord(data, 0x34)*0x8

	symbolOffset=getWord(data, 0x38)
	symbolSize=getWord(data, 0x3C)

	sym=data[symbolOffset:(symbolOffset+symbolSize)]
	labelTable=parseLabelTable(data[labelOffset:(labelOffset+labelSize)],sym)
	varTable=parseVarTable(data[varOffset:(varOffset+varSize)],sym)
	unifTable=parseConstTable(data[unifOffset:(unifOffset+unifSize)],sym)
	outputTable=parseOutputTable(data[outputOffset:(outputOffset+outputSize)],sym)

	parseDVLP(dvlp, labelTable, varTable, unifTable, outputTable)
	print("")

	return (labelTable,varTable,unifTable,range(codeStartOffset,codeEndOffset))

def parseDVLB(data):
	l=len(data)
	n=getWord(data, 0x4)
	dvleTable={}
	labelTable={}
	varTable={}
	unifTable={}
	dvlp=data[(0x8+0x4*n):l]
	for i in range(n):
		offset=getWord(data, 0x8+0x4*i)
		r=parseDVLE(data[offset:l],dvlp,i)
		# for k in r[3]:
		# 	dvleTable[k*4]=i
		# labelTable.update(r[0])
		# varTable[i]=r[1]
		# unifTable[i]=r[2]
	# parseDVLP(dvlp,labelTable,varTable,unifTable,dvleTable)
 
initIndent()
src1fn=sys.argv[1]
data=bytearray(open(src1fn, "rb").read())
l=len(data)

for i in range(0,l-4,4):
	if getWord(data, i)==0x424C5644:
		parseDVLB(data[i:l])
