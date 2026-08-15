set origin_dir [file normalize [file join [file dirname [info script]] ..]]
set build_dir [file join $origin_dir build phase06h synthesis]
set report_dir [file join $build_dir reports]
file mkdir $report_dir

create_project -force phase06h_candidate_grouping $build_dir -part xc7z020clg484-1
set_property target_language Verilog [current_project]
add_files -norecurse [list \
  [file join $origin_dir rtl phase06h rtl phase06h_pkg.sv] \
  [file join $origin_dir rtl phase06h rtl phase06h_candidate_ram.sv] \
  [file join $origin_dir rtl phase06h rtl axis_candidate_grouping.sv] \
  [file join $origin_dir rtl phase06h rtl phase06h_candidate_synthesis_top.sv]]
set_property file_type SystemVerilog [get_files *.sv]
set_property top phase06h_candidate_synthesis_top [current_fileset]

synth_design -top phase06h_candidate_synthesis_top -part xc7z020clg484-1 -flatten_hierarchy rebuilt
report_utilization -file [file join $report_dir synthesis-utilization.rpt]
report_utilization -hierarchical -hierarchical_depth 4 -file [file join $report_dir synthesis-utilization-hierarchical.rpt]
report_ram_utilization -file [file join $report_dir synthesis-ram-utilization.rpt]
report_drc -file [file join $report_dir synthesis-drc.rpt]

set utilization [report_utilization -return_string]
puts "PHASE06H_SYNTHESIS_PASS"
puts $utilization
close_project
exit
