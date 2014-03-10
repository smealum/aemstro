; setup constants
.const 5, 0.0, 1.0, 2.0, 3.0

; setup outmap
.out o0, result.position

main:
	; result.pos = transformMtx * in.pos
	dp4 d40, d20, d00 (0x0)
	dp4 d40, d21, d00 (0x1)
	dp4 d40, d22, d00 (0x2)
	mov d40, d05, d00 (0x4)
	; result.pos = projMtx * in.pos
	dp4 d00, d24, d40 (0x0)
	dp4 d00, d25, d40 (0x1)
	dp4 d00, d26, d40 (0x2)
	dp4 d00, d27, d40 (0x3)
	flush
	end
endmain:
