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

lineIndentLevel={}

def indentLine(k):
	if not(k in lineIndentLevel):
		lineIndentLevel[k]=0
	lineIndentLevel[k]+=1

def unindentLine(k):
	if not(k in lineIndentLevel):
		lineIndentLevel[k]=0
	lineIndentLevel[k]-=1

def resetIndentLevel():
	for k in lineIndentLevel:
		lineIndentLevel[k]=0

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

def getRegisterNameSRC(v):
	if v<0x80:
		return getRegisterNameSRC1(v)
	elif v<0x88:
		return "i"+str(v-0x80)
	else:
		return "b"+str(v-0x88)

def getRegisterNameSRC1(v):
	if v<0x10:
		return "v"+str(v&0xF)
	elif v<0x20:
		return "r"+str(v-0x10)
	elif v<0x80:
		return "c"+str(v-0x20)
	else:
		return ("r%02X"%(v))

def getRegisterNameSRC2(v):
	return getRegisterNameSRC1(v)

def getRegisterNameDST(v):
	if v<0x10:
		return ("o%X"%(v))
	elif v<0x20:
		return "r"+str(v-0x10)
	else:
		return ("r%02X"%(v))

def getRegisterName(v):
	return ("r%02X"%(v))
	# if v<16:
	# 	return "v"+str(v&0xF)
	# elif v<120:
	# 	return "c"+str(v-16)
	# else:
	# 	return "b"+str(v-0x88)


def getInputSymbol(v, vt, ut, idx):
	src=getRegisterNameSRC(v)
	return getInputSymbolFromString(src, vt, ut, idx)

def getInputSymbolFromString(src, vt, ut, idx):
	idxstr=""

	if idx==1:
		idxstr="[idx1]"
	elif idx==2:
		idxstr="[idx2]"
	elif idx==3:
		idxstr="[lcnt]"

	if src in vt:
		return vt[src]+idxstr
	if src in ut:
		return ut[src]+idxstr
	else:
		f=src.find(".")
		if f>=0:
			src=getInputSymbolFromString(src[:f], vt, ut, idx)+src[f:]
			idxstr=""
		return src+idxstr

def getOutputSymbol(v, ot):
	dst=getRegisterNameDST(v)
	return ot[dst] if dst in ot else dst

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
			"src3"    : (v>>23)&0xFF,
			"nsrc1"   : (v>>4)&0x1, #negation bit
			"nsrc2"   : (v>>13)&0x1, #negation bit
			"nsrc3"   : (v>>22)&0x1, #negation bit
			"dst"     : (v)&0x1F,
			"dstcomp" : parseComponentMask(v&0xF),
			"rest" : (v>>22)}
 
def parseComponentSwizzle(v):
	out=""
	for i in range(4):
		out+=comp[(v>>((3-i)*2))&0x3]
	return out

def parseInstFormat10(k, v, lt={}):
	return {"opcode" : v>>26,
			"src2"   : (v>>7)&0x1F,
			"src1"   : (v>>12)&0x7F,
			"idx_1"    : (v>>19)&0x3,
			"idx_2"    : 0x0,
			"cmpY"    : (v>>21)&0x7,
			"cmpX"    : (v>>24)&0x7,
			"extid"  : (v)&0x7F}

def parseInstFormat1(k, v, lt={}):
	return {"opcode" : v>>26,
			"src2"   : (v>>7)&0x1F,
			"src1"   : (v>>12)&0x7F,
			"idx_1"    : (v>>19)&0x3,
			"idx_2"    : 0x0,
			"dst"    : (v>>21)&0x1F,
			"extid"  : (v)&0x7F}

def parseInstFormat8(k, v, lt={}):
	return {"opcode" : v>>26,
			"src2"   : (v>>7)&0x7F,
			"src1"   : (v>>14)&0x1F,
			"idx_1"    : 0x0,
			"idx_2"    : (v>>19)&0x3,
			"dst"    : (v>>21)&0x1F,
			"extid"  : (v)&0x7F}

def parseInstFormat9(k, v, lt={}):
	return {"opcode" : v>>26,
			"dst"   : (v>>24)&0x1F,
			"src1"   : (v>>17)&0x7F,
			"src2"   : (v>>10)&0x7F,
			"src3"    : (v>>5)&0x1F,
			"idx_1"    : 0x0,
			"idx_2"    : 0x0,
			"extid"  : (v)&0x1F}

def parseInstFormat12(k, v, lt={}):
	return {"opcode" : v>>26,
			"dst"   : (v>>24)&0x1F,
			"src1"   : (v>>17)&0x7F,
			"src2"   : (v>>12)&0x1F,
			"src3"    : (v>>5)&0x7F,
			"idx_1"    : 0x0,
			"idx_2"    : 0x0,
			"extid"  : (v)&0x1F}

def parseInstFormat2(k, v, lt={}):
	ret={"opcode" : v>>26,
			"addr"   : (v>>8)&0x3FFC,
			"flags"  : (v>>22)&0xF,
			"ret"    : (v)&0x3FF}
	if ret["opcode"]==0x28: #IF?
		for i in range(k+4,ret["addr"],4):
			indentLine(i)
		for i in range(ret["addr"],ret["addr"]+ret["ret"]*4,4):
			indentLine(i)
		if ret["ret"]>0:
			lt[ret["addr"]]=(-1,"ELSE_%X"%(k))
	return ret

#?
def parseInstFormat3(k, v, lt={}):
	return {"opcode" : v>>26,
			"src2"   : (v>>0)&0x1F,
			"src1"   : (v>>7)&0x7F,
			"dst"    : (v>>14)&0x1F}

#?
def parseInstFormat6(k, v, lt={}):
	return {"opcode" : v>>26,
			"vtxid"   : (v>>24)&0x3,
			"primid"   : (v>>22)&0x3}
# MOV?
def parseInstFormat4(k, v, lt={}):
	return {"opcode" : v>>26,
			"src1"   : (v>>7)&0x7F,
			"dst"    : (v>>14)&0x1F,
			"extid"    : (v)&0x3F}
# CONDJUMP
def parseInstFormat5(k, v, lt={}):
	ret={"opcode" : v>>26,
			"addr"   : (v>>8)&0x3FFC,
			"bool"  : (v>>22)&0xF,
			"ret"    : (v)&0x3FF}
	if ret["opcode"]==0x27: #IFU
		for i in range(k+4,ret["addr"],4):
			indentLine(i)
		for i in range(ret["addr"],ret["addr"]+ret["ret"]*4,4):
			indentLine(i)
		if ret["ret"]>0:
			lt[ret["addr"]]=(-1,"ELSE_%X"%(k))
	elif ret["opcode"]==0x29: #LOOP
		for i in range(k+4,ret["addr"]+4,4):
			indentLine(i)
	return ret

def outputStringList(k, strl, fmtl):
	l=len(strl)
	if k in lineIndentLevel and lineIndentLevel[k]>0:
		out="	"*lineIndentLevel[k]
	else:
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


def printInstFormat1(k, n, inst, e, lt, vt, ut, ot):
	ext=e[inst["extid"]][0]
	extd=parseExt(ext)
	nsrc1="-" if extd["nsrc1"]==1 else ""
	nsrc2="-" if extd["nsrc2"]==1 else ""
	outputStringList(k, [n,
					getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"],
					" <- ",
					nsrc1+getInputSymbol(inst["src1"], vt, ut, inst["idx_1"])+"."+(parseComponentSwizzle(extd["src1"])),
					" , ",
					nsrc2+getInputSymbol(inst["src2"], vt, ut, inst["idx_2"])+"."+(parseComponentSwizzle(extd["src2"])),
					" ("+hex(inst["extid"])+" "+hex(extd["rest"])+")"],
					[8, 32, None, 32, None, 32, None])

cmpOp={0x0 : "EQ", 0x1 : "NE", 0x2 : "LT", 0x3 : "LE", 0x4 : "GT", 0x5 : "GE", 0x6 : "??", 0x7 : "??"}

def printInstFormat10(k, n, inst, e, lt, vt, ut, ot):
	ext=e[inst["extid"]][0]
	extd=parseExt(ext)
	nsrc1="-" if extd["nsrc1"]==1 else ""
	nsrc2="-" if extd["nsrc2"]==1 else ""
	outputStringList(k, [n,
					nsrc1+getInputSymbol(inst["src1"], vt, ut, inst["idx_1"])+"."+(parseComponentSwizzle(extd["src1"])),
					"("+cmpOp[inst["cmpX"]]+", "+cmpOp[inst["cmpY"]]+")",
					nsrc2+getInputSymbol(inst["src2"], vt, ut, inst["idx_2"])+"."+(parseComponentSwizzle(extd["src2"])),
					" ("+hex(inst["extid"])+")"],
					[8, 32, 12, 32, None])

def printInstFormat9(k, n, inst, e, lt, vt, ut, ot):
	ext=e[inst["extid"]][0]
	extd=parseExt(ext)
	nsrc1="-" if extd["nsrc1"]==1 else ""
	nsrc2="-" if extd["nsrc2"]==1 else ""
	nsrc3="-" if extd["nsrc3"]==1 else ""
	outputStringList(k, [n,
					getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"],
					" <- ",
					nsrc1+getInputSymbol(inst["src1"], vt, ut, inst["idx_1"])+"."+(parseComponentSwizzle(extd["src1"])),
					" , ",
					nsrc2+getInputSymbol(inst["src2"], vt, ut, inst["idx_2"])+"."+(parseComponentSwizzle(extd["src2"])),
					" , ",
					nsrc3+getInputSymbol(inst["src3"], vt, ut, 0)+"."+(parseComponentSwizzle(extd["src3"])),
					" ("+hex(extd["rest"])+")"],
					[8, 32, None, 16, None, 16, None, 16, None])

def printInstFormat4(k, n, inst, e, lt, vt, ut, ot):
	ext=e[inst["extid"]][0]
	extd=parseExt(ext)
	nsrc1="-" if extd["nsrc1"]==1 else ""
	nsrc2="-" if extd["nsrc2"]==1 else ""
	outputStringList(k, [n,
					getOutputSymbol(inst["dst"], ot)+"."+extd["dstcomp"],
					" <- ",
					nsrc1+getInputSymbol(inst["src1"], vt, ut, inst["idx_1"])+"."+(parseComponentSwizzle(extd["src1"])),
					"   ", "",
					" ("+hex(inst["extid"])+")"],
					[8, 32, None, 32, None, 32, None])

def printInstFormat7(k, n, inst, e, lt, vt, ut, ot):
	ext=e[inst["extid"]][0]
	extd=parseExt(ext)
	nsrc1="-" if extd["nsrc1"]==1 else ""
	nsrc2="-" if extd["nsrc2"]==1 else ""
	outputStringList(k, [n,
					"idx.xy__",
					" <- ",
					nsrc1+getInputSymbol(inst["src1"], vt, ut, inst["idx_1"])+"."+(parseComponentSwizzle(extd["src1"])),
					"   ", "",
					" ("+hex(inst["extid"])+")"],
					[8, 32, None, 32, None, 32, None])

def printInstFormat6(k, n, inst, e, lt, vt, ut, ot):
	outputStringList(k, [n,
					"vtx%02X," % inst["vtxid"],
					"PRIM_EMIT" if inst["primid"]&2==2 else "",
					"UNK_FLAG" if inst["primid"]&1==1 else ""],
					[8, 8, 12, 16])

def printInstFormat2(k, n, inst, e, lt, vt, ut, ot):
	outputStringList(k, [n,
					getLabelSymbol(inst["addr"], lt),
					" ("+str(inst["ret"])+ " words, flags: "+bin(inst['flags'])+")"],
					[8, 32, 32])

# CONDJUMP (uniform)
def printInstFormat5(k, n, inst, e, lt, vt, ut, ot):
	if inst["opcode"]==0x29: #LOOP
		reg=getRegisterNameSRC((inst['bool']&0xF)+0x80)
		start=getInputSymbolFromString(reg+".y", vt, ut, 0)
		end=start+"+"+getInputSymbolFromString(reg+".x", vt, ut, 0)
		stride=getInputSymbolFromString(reg+".z", vt, ut, 0)
		outputStringList(k, [n,
						"(lcnt = "+start+"; lcnt <= "+end+"; lcnt += "+stride+")",
						" (adr "+getLabelSymbol(inst["addr"], lt)+", "+str(inst["ret"])+ " words, "+str(inst['bool']&0xF)+")"],
						[8, 16, 16])
	elif inst["opcode"]==0x27: #IFU
		outputStringList(k, [n,
						"("+getInputSymbol((inst['bool']&0xF)+0x88, vt, ut, 0)+")",
						" ("+getLabelSymbol(inst["addr"], lt)+", "+str(inst["ret"])+ " words, "+str(inst['bool']&0xF)+")"],
						[8, 16, 16])
	elif inst["opcode"]==0x2d: #JMPU
		outputStringList(k, [n,
						getLabelSymbol(inst["addr"], lt),
						" ,  ",
						("!" if inst["ret"]==1 else "")+getInputSymbol((inst['bool']&0xF)+0x88, vt, ut, 0),
						"   ", "",
						" ("+str(inst["ret"])+ " words, "+str(inst['bool']&0xF)+")"],
						[8, 16, None, 16, None, 16, None])
	else:
		outputStringList(k, [n,
						getLabelSymbol(inst["addr"], lt),
						" ,  ",
						getInputSymbol((inst['bool']&0xF)+(0x80 if inst["opcode"]==0x29 else 0x88), vt, ut, 0),
						"   ", "",
						" ("+str(inst["ret"])+ " words, "+str(inst['bool']&0xF)+")"],
						[8, 16, None, 16, None, 16, None])

# CONDJUMP (dynamic)
def printInstFormat11(k, n, inst, e, lt, vt, ut, ot):
		cond=""
		if inst["flags"]&0x3==0x0: #OR
			cond=("!" if inst["flags"]&0x8 == 0 else "")+"cmp.x"+" || "+("!" if inst["flags"]&0x4 == 0 else "")+"cmp.y"
		elif inst["flags"]&0x3==0x1: #AND
			cond=("!" if inst["flags"]&0x8 == 0 else "")+"cmp.x"+" && "+("!" if inst["flags"]&0x4 == 0 else "")+"cmp.y"
		elif inst["flags"]&0x3==0x2: #X
						cond=("!" if inst["flags"]&0x8 == 0 else "")+"cmp.x"
		elif inst["flags"]&0x3==0x3: #Y
						cond=("!" if inst["flags"]&0x4 == 0 else "")+"cmp.y"

		if inst["opcode"]==0x23: #BREAK
			outputStringList(k, [n,
							"("+cond+")",
							"   ", "",
							" ("+str(inst["ret"])+ " words, "+str(inst['flags']&0xF)+")"],
							[8, 16, None, 16, None])
		elif inst["opcode"]==0x28: #IF
			outputStringList(k, [n,
							"("+cond+")",
							" ,  ",
							getLabelSymbol(inst["addr"], lt),
							"   ", "",
							" ("+str(inst["ret"])+ " words, "+str(inst['flags']&0xF)+")"],
							[8, 16, None, 16, None, 16, None])
		else:
			outputStringList(k, [n,
							getLabelSymbol(inst["addr"], lt),
							" ,  ",
							"("+cond+")",
							"   ", "",
							" ("+str(inst["ret"])+ " words, "+str(inst['flags']&0xF)+")"],
							[8, 16, None, 16, None, 16, None])

instList={}
fmtList=[(parseInstFormat1, printInstFormat1), (parseInstFormat2, printInstFormat2), (parseInstFormat2, printInstFormat2), (parseInstFormat1, printInstFormat4), (parseInstFormat5, printInstFormat5), (parseInstFormat6, printInstFormat6), (parseInstFormat1, printInstFormat7), (parseInstFormat8, printInstFormat1), (parseInstFormat9, printInstFormat9), (parseInstFormat10, printInstFormat10), (parseInstFormat2, printInstFormat11), (parseInstFormat12, printInstFormat9)]

instList[0x00]={"name" : "ADD", "format" : 0} #really SUB ?
instList[0x01]={"name" : "DP3", "format" : 0}
instList[0x02]={"name" : "DP4", "format" : 0}
instList[0x03]={"name" : "DPH", "format" : 0} #tested, definitely
instList[0x05]={"name" : "EX2", "format" : 3} #tested, definitely
instList[0x06]={"name" : "LG2", "format" : 3} #tested, definitely
instList[0x08]={"name" : "MUL", "format" : 0}
instList[0x09]={"name" : "SGE", "format" : 0}
instList[0x0A]={"name" : "SLT", "format" : 0}
instList[0x0B]={"name" : "FLR", "format" : 3} #tested, definitely FLR and not FRC
instList[0x0C]={"name" : "MAX", "format" : 0} #definitely
instList[0x0D]={"name" : "MIN", "format" : 0} #definitely
instList[0x0E]={"name" : "RCP", "format" : 3} #1/op1
instList[0x0F]={"name" : "RSQ", "format" : 3} #1/sqrt(op1)
instList[0x12]={"name" : "SETIDX", "format" : 6}
instList[0x13]={"name" : "MOV", "format" : 3}
instList[0x18]={"name" : "DPHI", "format" : 7}
instList[0x1A]={"name" : "SGEI", "format" : 7}
instList[0x1B]={"name" : "SLTI", "format" : 7}
instList[0x23]={"name" : "BREAKC", "format" : 10} #conditional break
instList[0x24]={"name" : "CALL", "format" : 1} #unconditional call
instList[0x25]={"name" : "CALLC", "format" : 10} #conditional call
instList[0x26]={"name" : "CALLU", "format" : 4} #conditional call (uniform bool)
instList[0x27]={"name" : "IFU", "format" : 4} #if/else statement (uniform bool)
instList[0x28]={"name" : "IFC", "format" : 10}
instList[0x29]={"name" : "LOOP", "format" : 4}
instList[0x2b]={"name" : "SETEMIT", "format" : 5}
instList[0x2c]={"name" : "JMPC", "format" : 10} #conditional jump
instList[0x2d]={"name" : "JMPU", "format" : 4} #conditional jump (uniform bool)
for i in range(0x2):
	instList[0x2e+i]={"name" : "CMP", "format" : 9}
for i in range(0x8):
	instList[0x30+i]={"name" : "MADI", "format" : 11}
for i in range(0x8):
	instList[0x38+i]={"name" : "MAD", "format" : 8}

def parseCode(data, e, lt, vt, ut, ot):
	l=len(data)
	for k in range(0,l,4):
		v=getWord(data,k)
		opcode=v>>26

		if k in lt:
			iprint("%08x [--------]	"%(k), True)
			unindentLine(k)
			outputStringList(k, [lt[k][1]+":"], [8])
			indentLine(k)

		iprint("%08x [%08x]	"%(k,v), True)

		if opcode in instList:
			fmt=instList[opcode]["format"]
			inst=fmtList[fmt][0](k, v, lt)
			fmtList[fmt][1](k, instList[opcode]["name"], inst, e, lt, vt, ut, ot)
		elif opcode==0x21:
			# outputStringList(k,["END"],[8])
			outputStringList(k,["NOP"],[8])
		elif opcode==0x22:
			outputStringList(k,["END"],[8])
		elif opcode==0x2A:
			inst=parseInstFormat1(k, v)
			outputStringList(k,["EMITVERTEX"],[10])
		else:
			inst=parseInstFormat1(k, v)
			if inst["extid"] < len(e):
				ext=e[inst["extid"]][0]
				extd=parseExt(ext)
				printInstFormat1(k, "???%02X"%(inst["opcode"]), inst, e, lt, vt, ut, ot)
			else:
				inst=parseInstFormat3(k, v)
				outputStringList(k,["???%02X"%(inst["opcode"]),
								       getOutputSymbol(inst["dst"], ot),
								       " <- ",
								       getInputSymbol(inst["src1"], vt, ut, 0),
								       " , ",
								       getInputSymbol(inst["src2"], vt, ut, 0),
								       "(invalid extension id)"],
								    [8, 16, None, 16, None, 16, None])

		k+=0x4

def parseDVLP(data, lt, vt, ut, ot, k):
	l=len(data)
	extOffset=getWord(data, 0x10)
	fnOffset=getWord(data, 0x18)
	# for i in range(fnOffset, l):
	# 	if k==0:
	# 		break
	# 	elif data[i]==0:
	# 		k-=1
	# print(parseSymbol(data,i))
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

def transformRegisterValue(v):
	if v<16:
		return (v&0xF)
	return v+16

def parseVarTable(data, sym):
	l=len(data)
	iprint("Uniforms :")
	indentOut()
	src={}
	for i in range(0,l,0x8):
		off=getWord(data,i)
		v1=getWord(data,i+4,2)
		v2=getWord(data,i+6,2)

		base=transformRegisterValue(v1)
		end=transformRegisterValue(v2)

		# iprint(getRegisterNameSRC(base)+" - "+getRegisterNameSRC(end)+" : "+parseSymbol(sym,off))
		iprint(getRegisterNameSRC(base)+" - "+getRegisterNameSRC(end)+" : "+parseSymbol(sym,off)+" ("+hex(getWord(data,i))+", "+hex(getWord(data,i+4))+")")
		if base==end:
			name=parseSymbol(sym,off)
			src[getRegisterNameSRC(base)]=name
		else:
			for k in range(base, end+1):
				name=parseSymbol(sym,off)+"["+str(k-base)+"]"
				src[getRegisterNameSRC(k)]=name

	unindentOut()
	print("")
	return src

def parseConstTable(data, sym):
	l=len(data)
	iprint("Constants :")
	indentOut()
	out={}
	for i in range(0,l,0x14):
		type=getWord(data,i,2)
		r=getWord(data,i+2,2)
		name=None
		if type==0x0:
			#constant bool
			vec=False if getWord(data,i+4)==0x0 else True
			r+=0x88
			name=str(vec)
		elif type==0x1:
			#constant integer vec4
			vec=[hex(getWord(data,i+k,1)) for k in range(4,8,1)]
			r+=0x80
			out[getRegisterNameSRC(r)+".x"]=vec[0]
			out[getRegisterNameSRC(r)+".y"]=vec[1]
			out[getRegisterNameSRC(r)+".z"]=vec[2]
			out[getRegisterNameSRC(r)+".w"]=vec[3]
		else:
			#constant float24 vec4 (should be type==0x2 but would rather output potential unknowns too)
			vec=[convFloat24(getWord(data,i+k)) for k in range(4,0x14,4)]
			r+=0x20
			name="["+", ".join(["%4.2f"%(v) for v in vec])+"]"
		# iprint(getRegisterNameSRC(r)+" = "+str(vec)+" ("+str([hex(getWord(data,i+k)) for k in range(0,0x14,4)])+")")
		iprint(getRegisterNameSRC(r)+" = "+str(vec))
		if name!=None:
			out[getRegisterNameSRC(r)]=name

	unindentOut()
	print("")
	return out

outputTypes={0x0 : "result.position",
			0x1 : "result.normalquat", #maybe
			0x2 : "result.color",
			0x3 : "result.texcoord0",
			0x4 : "result.texcoord0w",
			0x5 : "result.texcoord1",
			0x6 : "result.texcoord2",
			# 0x7 : "?", #sets outreg info to 0x1f1f1f1f...
			0x8 : "result.view", #"result.view" seems to be pre-projmatrix vertex coordinates
			}

def parseOutputTable(data, sym):
	l=len(data)
	iprint("Output :")
	indentOut()
	out={}
	for i in range(0,l,0x8):
		off=getWord(data,i+4)
		v1=getWord(data,i,2)
		v2=getWord(data,i+2,2)

		dst=getRegisterNameDST(v2)

		if v1 in outputTypes:
			out[dst]=outputTypes[v1]

		iprint("o"+str(v2)+" = "+(outputTypes[v1] if v1 in outputTypes else hex(v1))+" ("+hex(off)+", "+hex(v1)+", "+hex(v2)+")")

	unindentOut()
	print("")
	return out

def parseDVLE(data,dvlp, k):
	l=len(data)

	iprint("DVLE "+str(k))

	shaderType=getWord(data, 0x6, 1)
	mainStart=getWord(data, 0x8)*4
	mainEnd=getWord(data, 0xC)*4

	resetIndentLevel()

	iprint("unkval "+hex(getWord(data, 0x4, 2)))
	iprint("vertex shader" if shaderType==0x0 else "geometry shader")
	iprint("main : "+hex(mainStart)+"-"+hex(mainEnd))
	print("")

	# # temporarily filter out geometry shaders
	# if shaderType!=0x0:
	# 	return

	# # temporarily filter out vertex shaders
	# if shaderType==0x0:
	# 	return

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

	parseDVLP(dvlp, labelTable, varTable, unifTable, outputTable, k)
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

if len(sys.argv)<2:
	print("AEMSTRO :")
	print("    aemstro.py  <input.shbin/input.bcsdr>")
else:
	initIndent()
	src1fn=sys.argv[1]
	data=bytearray(open(src1fn, "rb").read())
	l=len(data)

	for i in range(0,l-4,4):
		if getWord(data, i)==0x424C5644:
			parseDVLB(data[i:l])
