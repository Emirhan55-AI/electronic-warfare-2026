set ::env(P0_BUILD_VARIANT) st06-runtime-config-v2-20260910
set ::env(P0_RUNTIME_CONFIG) 1
set ::env(P0_CONTINUE_BUILD) 1
source [file join [file dirname [info script]] create_st06_power_vivado_project.tcl]
source [file join [file dirname [info script]] run_p0_vivado.tcl]
