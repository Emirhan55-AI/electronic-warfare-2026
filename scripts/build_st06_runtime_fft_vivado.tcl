if {![info exists ::env(P0_RUNTIME_FFT_VARIANT)] ||
    $::env(P0_RUNTIME_FFT_VARIANT) eq ""} {
  set ::env(P0_RUNTIME_FFT_VARIANT) st06-rfft-v3-20260910
}
set ::env(P0_BUILD_VARIANT) $::env(P0_RUNTIME_FFT_VARIANT)
set ::env(P0_RUNTIME_CONFIG) 1
set ::env(P0_CONTINUE_BUILD) 1
source [file join [file dirname [info script]] create_st06_runtime_fft_vivado_project.tcl]
source [file join [file dirname [info script]] run_p0_vivado.tcl]
