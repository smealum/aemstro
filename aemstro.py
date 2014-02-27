import struct
import os
import sys
 
input={}
# '''0x0 : "vertex.position",
# 0x1 : "vertex.texcoord",
# 0x4 : "vertex.color?"}'''
 
output={0x0 : "glPosition",
		0x2 : "glColor",
		0x4 : "glTexcoord",
		0x6 : "glColor?",
		0x8 : "glTexcoord?"}
 
def getWord(b, k, n=4):
	return sum(list(map(lambda c: b[k+c]<<(c*8),range(n))))

def convFloat24(val):
	if val==0x0:
		return 0.0
	tmp=((val>>16)&0xFF)+0x40
	out=(tmp<<23)|((val&0x800000)<<31)|((val&0xFFFF)<<7)
	try:
		return (struct.unpack("f",struct.pack("I",out)))[0]
	except:
		return (val)

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

def getValue(v, t):
	return t[v] if v in t else ("r%02X"%(v))

def getInputSymbol(v, vt, ut):
	if v in vt:
		return vt[v]
	elif v in ut:
		return "("+",".join(["%.2f"%k for k in ut[v]])+")"
	else:
		return getValue(v, input)

def getOutputSymbol(v):
	return getValue(v, output)

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

def iprint(str, e=False):
	global numIdent
	if e:
		print("	"*numIdent+str,end='')
	else:
		print("	"*numIdent+str)

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
	return {"src1" : (v>>5)&0xFF,
			"src2" : (v>>14)&0xFF,
			"dst" : (v)&0x1F,
			"dstcomp" : parseComponentMask(v&0xF)}
 
def parseComponentSwizzle(v):
	out=""
	for i in range(4):
		out+=comp[(v>>((3-i)*2))&0x3]
	return out

def parseInstFormat1(v):
	return {"opcode" : v>>26,
			"src1" : (v>>12)&0x3F,
			"src2" : (v>>6)&0x3F,
			"dst" : (v>>20)&0x3F,
			"flags" : (v>>18)&0x3,
			"extid" : (v)&0x3F}

def parseInstFormat2(v):
	return {"opcode" : v>>26,
			"addr" : (v>>8)&0x3FFC,
			"flags": (v>>22)&0x3F,
			"ret" : (v)&0x3FF}

def parseCode(data, e, lt, vt, ut, d):
	l=len(data)
	for k in range(0,l,4):
		v=getWord(data,k)
		opcode=v>>26

		if k in d:
			rvt=vt[d[k]]
			rut=ut[d[k]]
		else:
			rvt={}
			rut={}

		if k in lt:
			iprint("%08x [--------] "%(k), True)
			iprint(lt[k][1]+":")

		iprint("%08x [%08x]	"%(k,v), True)
		if opcode==0x00: #could be SUB ?
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("ADD?   "+
			       getOutputSymbol(inst["dst"])+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], rvt, rut)+"."+(parseComponentSwizzle(extd["src1"]))+
			       "   .   "+
			       getInputSymbol(inst["src2"], rvt, rut)+"."+(parseComponentSwizzle(extd["src2"]))+
			       " ("+hex(inst["extid"])+", "+"flags: "+bin(inst["flags"])+")")
		elif opcode==0x01:
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("DP3    "+
			       getOutputSymbol(inst["dst"])+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], rvt, rut)+"."+(parseComponentSwizzle(extd["src1"]))+
			       "   .   "+
			       getInputSymbol(inst["src2"], rvt, rut)+"."+(parseComponentSwizzle(extd["src2"]))+
			       " ("+hex(inst["extid"])+", "+"flags: "+bin(inst["flags"])+")")
		elif opcode==0x02:
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("DP4    "+
			       getOutputSymbol(inst["dst"])+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], rvt, rut)+"."+(parseComponentSwizzle(extd["src1"]))+
			       "   .   "+
			       getInputSymbol(inst["src2"], rvt, rut)+"."+(parseComponentSwizzle(extd["src2"]))+
			       " ("+hex(inst["extid"])+", "+"flags: "+bin(inst["flags"])+")")
		elif opcode==0x13:
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("MOV    "+
			       getOutputSymbol(inst["dst"])+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], rvt, rut)+"."+(parseComponentSwizzle(extd["src1"]))+
				" ("+hex(inst["extid"])+", "+"flags: "+bin(inst["flags"])+", src2: "+hex(inst["src2"])+")")
		elif opcode==0x24 or opcode==0x25 or opcode==0x26 or opcode==0x27:
			inst=parseInstFormat2(v)
			addr=inst["addr"]
			if not (inst['flags'] & (1<<25)):
				addr=addr+k # relative, TODO: sign extension(?)
			iprint("CALL   "+getLabelSymbol(inst["addr"], lt)+
			       " ("+str(inst["ret"])+ " words, flags: "+bin(inst['flags'])+")")
		elif opcode==0x22:
			iprint("FLUSH")
		elif opcode==0x21:
			iprint("END")
		elif opcode==0x2A:
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("EMITV? "+
			       getOutputSymbol(inst["dst"])+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], rvt, rut)+"."+(parseComponentSwizzle(extd["src1"]))+
			       "   .   "+
			       getInputSymbol(inst["src2"], rvt, rut)+"."+(parseComponentSwizzle(extd["src2"]))+
			       " ("+hex(inst["extid"])+", "+"flags: "+bin(inst["flags"])+")")
		# elif opcode==0x2D:
		# 	inst=parseInstFormat1(v)
		# 	ext=e[inst["extid"]][0]
		# 	extd=parseExt(ext)
		# 	iprint("SUB?   "+
		# 	       getOutputSymbol(inst["dst"])+"."+extd["dstcomp"]+
		# 	       "   <-	"+
		# 	       getInputSymbol(i, rutnst["src1"], rvt)+"."+(parseComponentSwizzle(extd["src1"]))+
		# 	       "   .   "+
		# 	       getInputSymbol(i, rutnst["src2"], rvt)+"."+(parseComponentSwizzle(extd["src2"]))+
		# 	       " ("+hex(inst["extid"])+", "+"flags: "+bin(inst["flags"])+")")
		else:
			inst=parseInstFormat1(v)
			ext=e[inst["extid"]][0]
			extd=parseExt(ext)
			iprint("???    "+
			       getOutputSymbol(inst["dst"])+"."+extd["dstcomp"]+
			       "   <-	"+
			       getInputSymbol(inst["src1"], rvt, rut)+"."+(parseComponentSwizzle(extd["src1"]))+
			       "   .   "+
			       getInputSymbol(inst["src2"], rvt, rut)+"."+(parseComponentSwizzle(extd["src2"]))+
			       " ("+hex(inst["extid"])+", "+"flags: "+bin(inst["flags"])+")")
		k+=0x4

def parseDVLP(data, lt, vt, ut, d):
	l=len(data)
	extOffset=getWord(data, 0x10)
	extSize=getWord(data, 0x14)*8
	ext=parseExtTable(data[extOffset:(extOffset+extSize)])
	codeOffset=getWord(data, 0x8)
	codeSize=getWord(data, 0xC)*4
	parseCode(data[codeOffset:(codeOffset+codeSize)], ext, lt, vt, ut, d)

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
	if v>>4==0x6:
		out=0x30|(v&0xF)
	elif v>>4==0x5:
		out=0x30|(v&0xF)
	elif v>>4==0x1:
		out=0x20|(v&0xF)
	elif v>>4==0x0:
		out=(v&0xF)
	else:
		out=-1
	return out


def parseVarTable(data, sym):
	l=len(data)
	iprint("Vars:")
	indentOut()
	out={}
	for i in range(0,l,0x8):
		off=getWord(data,i)
		v1=getWord(data,i+4,2)
		v2=getWord(data,i+6,2)

		base=transformRegisterValue(v1)

		if base == -1:
			iprint(parseSymbol(sym,off)+"["+str(k)+"]"+" ???")
		else:
			for k in range(v2-v1+1):
				name=parseSymbol(sym,off)+"["+str(k)+"]"
				loc=base+k
				out[loc]=name
				iprint(parseSymbol(sym,off)+"["+str(k)+"]"+" r%d" % loc)

	unindentOut()
	print("")
	return out

def parseUniformTable(data, sym):
	l=len(data)
	iprint("Uniforms :")
	indentOut()
	out={}
	for i in range(0,l,0x14):
		r=transformRegisterValue(getWord(data,i+2,2))
		vec=[convFloat24(getWord(data,i+k)) for k in range(4,0x14,4)]
		iprint("r%02X"%(r)+" "+str(vec))
		out[r]=vec

	unindentOut()
	print("")
	return out

def parseUnk2Table(data, sym):
	l=len(data)
	iprint("unk2 :")
	indentOut()
	out={}
	for i in range(0,l,0x8):
		off=getWord(data,i+4)
		v1=getWord(data,i,2)
		v2=getWord(data,i+2,2)

		iprint(hex(off)+" : "+hex(v1)+", "+hex(v2))

	unindentOut()
	print("")
	return out

def parseDVLE(data):
	l=len(data)

	codeStartOffset=getWord(data, 0x8)
	codeEndOffset=getWord(data, 0xC)

	unifOffset=getWord(data, 0x18)
	unifSize=getWord(data, 0x1C)*0x14

	labelOffset=getWord(data, 0x20)
	labelSize=getWord(data, 0x24)*0x10

	unk2Offset=getWord(data, 0x28)
	unk2Size=getWord(data, 0x2C)*0x8

	varOffset=getWord(data, 0x30)
	varSize=getWord(data, 0x34)*0x8

	symbolOffset=getWord(data, 0x38)
	symbolSize=getWord(data, 0x3C)

	sym=data[symbolOffset:(symbolOffset+symbolSize)]
	labelTable=parseLabelTable(data[labelOffset:(labelOffset+labelSize)],sym)
	varTable=parseVarTable(data[varOffset:(varOffset+varSize)],sym)
	unifTable=parseUniformTable(data[unifOffset:(unifOffset+unifSize)],sym)
	unk2Table=parseUnk2Table(data[unk2Offset:(unk2Offset+unk2Size)],sym)

	return (labelTable,varTable,unifTable,range(codeStartOffset,codeEndOffset))

def parseDVLB(data):
	l=len(data)
	n=getWord(data, 0x4)
	dvleTable={}
	labelTable={}
	varTable={}
	unifTable={}
	for i in range(n):
		offset=getWord(data, 0x8+0x4*i)
		r=parseDVLE(data[offset:l])
		for k in r[3]:
			dvleTable[k*4]=i
		labelTable.update(r[0])
		varTable[i]=r[1]
		unifTable[i]=r[2]
	parseDVLP(data[(0x8+0x4*n):l],labelTable,varTable,unifTable,dvleTable)
 
initIndent()
src1fn=sys.argv[1]
data=bytearray(open(src1fn, "rb").read())
l=len(data)

for i in range(0,l,4):
	if getWord(data, i)==0x424C5644:
		parseDVLB(data[i:l])
