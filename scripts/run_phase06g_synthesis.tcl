set script_directory [file dirname [file normalize [info script]]]
set repository_root [file normalize [file join $script_directory ..]]
set build_root [file normalize [file join $repository_root build phase06g synthesis]]
set allowed_root [file normalize [file join $repository_root build phase06g]]
if {![string match "${allowed_root}/*" $build_root]} {
  error "refusing to use build directory outside repository build/phase06g"
}
if {[file exists $build_root]} {
  file delete -force $build_root
}
file mkdir $build_root
set report_root [file join $build_root reports]
file mkdir $report_root

create_project phase06g_synthesis $build_root -part xc7z020clg484-1 -force
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]

set rtl_sources [list \
  [file join $repository_root rtl phase06c rtl phase06c_pkg.sv] \
  [file join $repository_root rtl phase06a rtl axis_skid_buffer.sv] \
  [file join $repository_root rtl phase06c rtl axis_fft_wrapper.sv] \
  [file join $repository_root rtl phase06d rtl amd_xfft_adapter.sv] \
  [file join $repository_root rtl phase06e rtl phase06e_fft_implementation_top.sv] \
  [file join $repository_root rtl phase06f rtl axis_fft_linear_power.sv] \
  [file join $repository_root rtl phase06g rtl phase06g_pkg.sv] \
  [file join $repository_root rtl phase06g rtl axis_regional_detector.sv] \
  [file join $repository_root rtl phase06g rtl phase06g_detector_synthesis_top.sv] \
]
add_files -fileset sources_1 -norecurse $rtl_sources
set xci [file join $repository_root rtl phase06d ip phase06d_fft_4096 phase06d_fft_4096.xci]
import_ip -files $xci -name phase06d_fft_4096
set xdc [file join $repository_root rtl phase06e constraints phase06e_fft_100mhz.xdc]
add_files -fileset constrs_1 -norecurse $xdc
set_property used_in_synthesis true [get_files $xdc]
set_property used_in_implementation false [get_files $xdc]
set_property top phase06g_detector_synthesis_top [get_filesets sources_1]
update_compile_order -fileset sources_1
generate_target all [get_ips phase06d_fft_4096]
set_property strategy Flow_PerfOptimized_high [get_runs synth_1]

puts "PHASE06G:TOOL=[version -short]"
puts "PHASE06G:PART=[get_property PART [current_project]]"
puts "PHASE06G:TOP=[get_property TOP [get_filesets sources_1]]"
launch_runs synth_1 -jobs 4
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "PHASE06G:SYNTH_STATUS=$synth_status"
if {![string match "*Complete*" $synth_status]} {
  error "synth_1 did not complete successfully: $synth_status"
}
open_run synth_1
report_utilization -hierarchical -hierarchical_depth 10 -file [file join $report_root synthesis-utilization-hierarchical.rpt]
report_utilization -file [file join $report_root synthesis-utilization-summary.rpt]
report_timing_summary -delay_type max -max_paths 10 -report_unconstrained -file [file join $report_root synthesis-timing-estimate.rpt]
report_drc -file [file join $report_root synthesis-drc.rpt]

set top_cell [get_cells -hierarchical -filter {NAME == "detector"}]
if {[llength $top_cell] == 0} {
  set top_cell [get_cells -hierarchical -filter {REF_NAME == "axis_regional_detector"}]
}
if {[llength $top_cell] > 0} {
  report_utilization -cells $top_cell -file [file join $report_root detector-utilization.rpt]
}
puts "PHASE06G:REPORTS=$report_root"
close_project
exit
