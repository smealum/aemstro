; result.pos = projMtx * in.pos
main:
	dp4 d00, d20, d00 (0x0)
	dp4 d00, d21, d00 (0x1)
	dp4 d00, d22, d00 (0x2)
	dp4 d00, d23, d00 (0x3)
	flush
	end
endmain:
