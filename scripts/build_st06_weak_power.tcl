# Isolated current-source implementation. Never opens a frozen project for writing.
set ::env(P0_BUILD_VARIANT) st06-weak-power-20260910
set ::env(P0_CONTINUE_BUILD) 1
set task_script_directory [file dirname [file normalize [info script]]]
source [file join $task_script_directory create_st06_power_vivado_project.tcl]
source [file join $task_script_directory run_p0_vivado.tcl]
