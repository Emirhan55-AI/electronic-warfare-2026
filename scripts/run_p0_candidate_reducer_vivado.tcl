set script_directory [file dirname [file normalize [info script]]]
set repository_root [file normalize [file join $script_directory ..]]
set build_root [file normalize [file join $repository_root build p0 candidate-reducer-vivado]]
set allowed_root [file normalize [file join $repository_root build p0]]
if {![string match "${allowed_root}/*" $build_root]} {
  error "refusing to use build directory outside repository build/p0"
}
if {[file exists $build_root]} {
  file delete -force $build_root
}
file mkdir $build_root
set report_root [file join $build_root reports]
file mkdir $report_root

create_project p0_candidate_reducer $build_root -part xc7z020clg484-1 -force
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]

set rtl_sources [list \
  [file join $repository_root algorithms fpga p0 rtl p0_os_cfar_pkg.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_candidate_reducer_pkg.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_wideband_recovery_pkg.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_sparse_os_candidate_pkg.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_os_cfar_decision_engine.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_os_candidate_ram.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_os_candidate_grouping.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_sparse_os_candidate_top.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_region_bank.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_parallel_region_median.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_wideband_recovery.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_candidate_record_ram.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_candidate_fusion.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_candidate_reducer_top.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_candidate_reducer_synthesis_top.sv] \
]
add_files -fileset sources_1 -norecurse $rtl_sources
set xdc [file join $repository_root algorithms fpga p0 constraints p0_candidate_reducer_50mhz.xdc]
add_files -fileset constrs_1 -norecurse $xdc
set_property used_in_synthesis true [get_files $xdc]
set_property used_in_implementation true [get_files $xdc]
set_property top p0_candidate_reducer_synthesis_top [get_filesets sources_1]
update_compile_order -fileset sources_1

set_property strategy Flow_PerfOptimized_high [get_runs synth_1]
set_property strategy Performance_Explore [get_runs impl_1]

puts "P0_CANDIDATE_REDUCER:TOOL=[version -short]"
puts "P0_CANDIDATE_REDUCER:PART=[get_property PART [current_project]]"
puts "P0_CANDIDATE_REDUCER:TOP=[get_property TOP [get_filesets sources_1]]"

launch_runs synth_1 -jobs 4
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "P0_CANDIDATE_REDUCER:SYNTH_STATUS=$synth_status"
if {![string match "*Complete*" $synth_status]} {
  error "synth_1 did not complete successfully: $synth_status"
}
open_run synth_1
report_utilization -hierarchical -hierarchical_depth 12 -file [file join $report_root synthesis-utilization.rpt]
report_utilization -file [file join $report_root synthesis-utilization-summary.rpt]
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -check_timing_verbose -file [file join $report_root synthesis-timing-summary.rpt]
report_drc -file [file join $report_root synthesis-drc.rpt]
set reducer_cell [get_cells -hierarchical -filter {REF_NAME == "p0_candidate_reducer_top"}]
if {[llength $reducer_cell] > 0} {
  report_utilization -cells $reducer_cell -file [file join $report_root reducer-utilization.rpt]
}
close_design

launch_runs impl_1 -to_step route_design -jobs 4
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "P0_CANDIDATE_REDUCER:IMPLEMENTATION_STATUS=$impl_status"
if {![string match "*Complete*" $impl_status]} {
  error "impl_1 did not complete successfully: $impl_status"
}
open_run impl_1
report_utilization -hierarchical -hierarchical_depth 12 -file [file join $report_root implementation-utilization.rpt]
report_utilization -file [file join $report_root implementation-utilization-summary.rpt]
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -check_timing_verbose -file [file join $report_root implementation-timing-summary.rpt]
report_timing -delay_type max -max_paths 20 -slack_lesser_than 0 -file [file join $report_root setup-failing-paths.rpt]
report_timing -delay_type min -max_paths 20 -slack_lesser_than 0 -file [file join $report_root hold-failing-paths.rpt]
report_route_status -file [file join $report_root route-status.rpt]
report_drc -file [file join $report_root implementation-drc.rpt]
check_timing -verbose -file [file join $report_root check-timing.rpt]
set setup_failures [get_timing_paths -delay_type max -slack_lesser_than 0 -max_paths 1 -quiet]
set hold_failures [get_timing_paths -delay_type min -slack_lesser_than 0 -max_paths 1 -quiet]
puts "P0_CANDIDATE_REDUCER:SETUP_FAILING_PATHS=[llength $setup_failures]"
puts "P0_CANDIDATE_REDUCER:HOLD_FAILING_PATHS=[llength $hold_failures]"
if {[llength $setup_failures] != 0 || [llength $hold_failures] != 0} {
  error "P0 candidate reducer timing failed"
}
puts "P0_CANDIDATE_REDUCER:REPORTS=$report_root"
close_project
exit
