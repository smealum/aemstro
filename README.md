aemstro
=======

''THE ORIGINAL'' pica200 shader (dis)assembly toolkit !

set of tools used to disassemble and assemble shader code for DMP's MAESTRO shader extension used in the 3DS's PICA200 GPU
see http://3dbrew.org/wiki/Shader_Instruction_Set for more information

it is meant for rapid iteration and experimentation as I reverse engineer the instruction set. as such, the code is dirty and ugly and poorly organized. functionality is also lacking and overall it is not recommended that you use this for your own homebrew projects unless they involve reverse engineering. for more user friendly implementations, see neobrain's nihstro and fincs's picasso.

requires python 3. sorry !

please note that the current iteration of aemstro is very experimental as we are still in the process of reverse engineering the instruction set. the current version is a prototype meant to be iterated upon quickly; not a well thought out piece of clean software. so basically don't fret if you think the code looks like shit and could be written in a much more efficient manner; you're not alone.

aemstro.py :

	- disassembles shbin/bcsdr files
	- usage : aemstro.py  <input.shbin/input.bcsdr>
	- outputs to stdout

aemstro_as.py :

	- assembles vertex shaders
	- usage : aemstro_as.py  <input.vsh>  <output.shbin>
	- see test.vsh for sample code
	- can *not* assemble output from aemstro.py
	- is currently much less up to date than aemstro.py (mostly the instruction format thing is all wrong)
