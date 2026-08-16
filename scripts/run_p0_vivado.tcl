set script_directory [file dirname [file normalize [info script]]]
set repository_root [file normalize [file join $script_directory ..]]
set build_root [file normalize [file join $repository_root build p0 vivado]]
set project_file [file join $build_root p0_runtime.xpr]
set report_root [file join $build_root reports]
if {![file isfile $project_file]} {
  error "P0 Vivado project is missing; run create_p0_vivado_project.tcl first"
}
file mkdir $report_root
open_project $project_file
set_property strategy Flow_PerfOptimized_high [get_runs synth_1]
set_property strategy Performance_Explore [get_runs impl_1]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "P0:SYNTH_STATUS=$synth_status"
if {![string match "*Complete*" $synth_status]} {
  error "P0 synthesis failed: $synth_status"
}
open_run synth_1
report_utilization -hierarchical -hierarchical_depth 10 -file [file join $report_root synthesis-utilization.rpt]
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -check_timing_verbose -file [file join $report_root synthesis-timing-summary.rpt]
report_drc -file [file join $report_root synthesis-drc.rpt]
close_design

launch_runs impl_1 -to_step route_design -jobs 4
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "P0:IMPLEMENTATION_STATUS=$impl_status"
if {![string match "*Complete*" $impl_status]} {
  error "P0 implementation failed: $impl_status"
}
open_run impl_1
report_utilization -hierarchical -hierarchical_depth 10 -file [file join $report_root implementation-utilization.rpt]
report_utilization -file [file join $report_root implementation-utilization-summary.rpt]
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -check_timing_verbose -file [file join $report_root implementation-timing-summary.rpt]
report_route_status -file [file join $report_root route-status.rpt]
report_drc -file [file join $report_root implementation-drc.rpt]
report_methodology -file [file join $report_root methodology.rpt]
set check_timing_report [file join $report_root check-timing.rpt]
check_timing -verbose -file $check_timing_report
set setup_failures [get_timing_paths -delay_type max -slack_lesser_than 0 -max_paths 1 -quiet]
set hold_failures [get_timing_paths -delay_type min -slack_lesser_than 0 -max_paths 1 -quiet]
puts "P0:SETUP_FAILING_PATHS=[llength $setup_failures]"
puts "P0:HOLD_FAILING_PATHS=[llength $hold_failures]"
puts "P0:CHECK_TIMING_REPORT=$check_timing_report"
close_design
if {[llength $setup_failures] != 0 || [llength $hold_failures] != 0} {
  error "P0 timing failed; bitstream will not be generated"
}

launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
set bit_status [get_property STATUS [get_runs impl_1]]
puts "P0:BITSTREAM_STATUS=$bit_status"
if {![string match "*Complete*" $bit_status]} {
  error "P0 bitstream generation failed: $bit_status"
}
set hardware_root [file join $repository_root build p0 hardware]
file mkdir $hardware_root
set xsa_file [file join $hardware_root p0_system_50mhz.xsa]
write_hw_platform -fixed -include_bit -force -file $xsa_file
puts "P0:XSA=$xsa_file"
puts "P0:REPORTS=$report_root"
close_project
exit
