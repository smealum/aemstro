aemstro
=======

set of tools used to disassemble and assemble shader code for DMP's MAESTRO shader extension used in the 3DS's PICA200 GPU
see http://3dbrew.org/wiki/Shader_Instruction_Set for more information

please note that the current iteration of aemstro is very experimental as we are still in the process of reverse engineering the instruction set. a more feature complete with cleaner code will become available in the future.

aemstro.py :
	- disassembles shbin/bcsdr files
	- usage : aemstro.py  <input.shbin/input.bcsdr>
	- outputs to stdout

aemstro_as.py :
	- assembles vertex shaders
	- usage : aemstro_as.py  <input.vsh>  <output.shbin>
	- see test.vsh for sample code
