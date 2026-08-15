set script_directory [file dirname [file normalize [info script]]]
set repository_root [file normalize [file join $script_directory ..]]

set run_name [expr {[llength $argv] >= 1 ? [lindex $argv 0] : "implementation"}]
if {![regexp {^[a-zA-Z0-9_-]+$} $run_name]} {
  error "run name must contain only letters, digits, underscore or dash"
}
set build_root [file normalize [file join $repository_root build phase06e $run_name]]
set allowed_root [file normalize [file join $repository_root build phase06e]]
if {![string match "${allowed_root}/*" $build_root]} {
  error "refusing to use build directory outside repository build/phase06e"
}
if {[file exists $build_root]} {
  file delete -force $build_root
}
file mkdir $build_root
set report_root [file join $build_root reports]
file mkdir $report_root

create_project phase06e_impl $build_root -part xc7z020clg484-1 -force
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]

set rtl_sources [list \
  [file join $repository_root rtl phase06c rtl phase06c_pkg.sv] \
  [file join $repository_root rtl phase06a rtl axis_skid_buffer.sv] \
  [file join $repository_root rtl phase06c rtl axis_fft_wrapper.sv] \
  [file join $repository_root rtl phase06d rtl amd_xfft_adapter.sv] \
  [file join $repository_root rtl phase06e rtl phase06e_fft_implementation_top.sv] \
]
add_files -fileset sources_1 -norecurse $rtl_sources
set xci [file join $repository_root rtl phase06d ip phase06d_fft_4096 phase06d_fft_4096.xci]
import_ip -files $xci -name phase06d_fft_4096
set xdc [file join $repository_root rtl phase06e constraints phase06e_fft_100mhz.xdc]
add_files -fileset constrs_1 -norecurse $xdc
set_property used_in_synthesis true [get_files $xdc]
set_property used_in_implementation true [get_files $xdc]
set_property top phase06e_fft_implementation_top [get_filesets sources_1]
update_compile_order -fileset sources_1
generate_target all [get_ips phase06d_fft_4096]

set_property strategy Flow_PerfOptimized_high [get_runs synth_1]
set_property strategy Performance_Explore [get_runs impl_1]

puts "PHASE06E:TOOL=[version -short]"
puts "PHASE06E:PART=[get_property PART [current_project]]"
puts "PHASE06E:TOP=[get_property TOP [get_filesets sources_1]]"
puts "PHASE06E:BUILD=$build_root"

launch_runs synth_1 -jobs 4
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "PHASE06E:SYNTH_STATUS=$synth_status"
if {![string match "*Complete*" $synth_status]} {
  error "synth_1 did not complete successfully: $synth_status"
}
open_run synth_1
report_utilization -hierarchical -hierarchical_depth 8 -file [file join $report_root synthesis-utilization.rpt]
report_utilization -file [file join $report_root synthesis-utilization-summary.rpt]
report_timing_summary -delay_type min_max -max_paths 10 -report_unconstrained -check_timing_verbose -file [file join $report_root synthesis-timing-summary.rpt]
report_drc -file [file join $report_root synthesis-drc.rpt]
close_design

launch_runs impl_1 -to_step route_design -jobs 4
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "PHASE06E:IMPLEMENTATION_STATUS=$impl_status"
if {![string match "*Complete*" $impl_status]} {
  error "impl_1 did not complete successfully: $impl_status"
}
open_run impl_1
report_utilization -hierarchical -hierarchical_depth 8 -file [file join $report_root implementation-utilization.rpt]
report_utilization -file [file join $report_root implementation-utilization-summary.rpt]
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -check_timing_verbose -file [file join $report_root implementation-timing-summary.rpt]
report_timing -delay_type max -max_paths 20 -slack_lesser_than 0 -file [file join $report_root setup-failing-paths.rpt]
report_timing -delay_type min -max_paths 20 -slack_lesser_than 0 -file [file join $report_root hold-failing-paths.rpt]
report_clocks -file [file join $report_root clocks.rpt]
report_clock_interaction -file [file join $report_root clock-interaction.rpt]
report_cdc -details -file [file join $report_root cdc.rpt]
report_route_status -file [file join $report_root route-status.rpt]
report_drc -file [file join $report_root implementation-drc.rpt]
report_methodology -file [file join $report_root methodology.rpt]
check_timing -verbose -file [file join $report_root check-timing.rpt]

set properties_file [open [file join $report_root run-properties.txt] w]
foreach run [list [get_runs synth_1] [get_runs impl_1]] {
  puts $properties_file "RUN=[get_property NAME $run]"
  foreach property_name [lsort [list_property $run]] {
    if {[string match "STATS.*" $property_name] || $property_name eq "STATUS" || $property_name eq "PROGRESS"} {
      puts $properties_file "$property_name=[get_property $property_name $run]"
    }
  }
}
close $properties_file
puts "PHASE06E:REPORTS=$report_root"
close_project
exit
