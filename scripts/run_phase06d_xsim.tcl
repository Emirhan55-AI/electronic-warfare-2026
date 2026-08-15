set script_directory [file dirname [file normalize [info script]]]
set repository_root [file normalize [file join $script_directory ..]]
source [file join $script_directory phase06d_ip_config.tcl]

set run_name [expr {[llength $argv] >= 1 ? [lindex $argv 0] : "run"}]
if {![regexp {^[a-zA-Z0-9_-]+$} $run_name]} {
  error "run name must contain only letters, digits, underscore or dash"
}
set build_root [file normalize [file join $repository_root build phase06d xsim $run_name]]
set allowed_root [file normalize [file join $repository_root build phase06d]]
if {![string match "${allowed_root}/*" $build_root]} {
  error "refusing to use build directory outside repository build/phase06d"
}
if {[file exists $build_root]} {
  file delete -force $build_root
}
file mkdir $build_root

create_project phase06d_xsim $build_root -part $phase06d::target_part -force
set core [phase06d::create_configured_ip [file join $build_root ip]]
phase06d::emit_configuration $core
generate_target simulation $core

set sources [list \
  [file join $repository_root rtl phase06c rtl phase06c_pkg.sv] \
  [file join $repository_root rtl phase06a rtl axis_skid_buffer.sv] \
  [file join $repository_root rtl phase06c rtl axis_fft_wrapper.sv] \
  [file join $repository_root rtl phase06d rtl amd_xfft_adapter.sv] \
  [file join $repository_root rtl phase06d tb tb_phase06d_fft_vendor.sv] \
]
add_files -fileset sim_1 -norecurse $sources
set_property top tb_phase06d_fft_vendor [get_filesets sim_1]
set input_mem [file normalize [file join $repository_root datasets fixtures phase06d axis-input.mem]]
set expected_mem [file normalize [file join $repository_root datasets fixtures phase06d cmodel-expected.mem]]
set capture_mem [file normalize [file join $build_root xsim-capture.mem]]
set options "-onfinish quit -testplusarg INPUT_MEM=$input_mem -testplusarg EXPECTED_MEM=$expected_mem -testplusarg CAPTURE_MEM=$capture_mem"
set_property -name xsim.simulate.xsim.more_options -value $options -objects [get_filesets sim_1]
set_property -name xsim.simulate.runtime -value all -objects [get_filesets sim_1]

puts "PHASE06D:XSIM_BUILD=$build_root"
puts "PHASE06D:XSIM_CAPTURE=$capture_mem"
launch_simulation -simset sim_1 -mode behavioral
run all
# The project is entirely transient under build/.  Force-exit after the
# completed self-checking run avoids saving a large behavioral wave database.
exit -force
