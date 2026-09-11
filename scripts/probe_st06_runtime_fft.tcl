set script_dir [file dirname [file normalize [info script]]]
set root_dir [file dirname $script_dir]
set output_dir [file normalize [expr {[llength $argv] > 0 \
  ? [lindex $argv 0] \
  : [file join $root_dir build p0 st06-runtime-fft-probe]}]]

file mkdir $output_dir
create_project -force st06_runtime_fft_probe \
  [file join $output_dir vivado] \
  -part xc7z020clg484-1
set_property target_language Verilog [current_project]

source [file join $script_dir phase06d_ip_config.tcl]

set fixed_core [phase06d::create_configured_ip [file join $output_dir ip-fixed]]

set dynamic_name st06_fft_runtime_16384
file mkdir [file join $output_dir ip-runtime]
create_ip \
  -name xfft \
  -vendor xilinx.com \
  -library ip \
  -version 9.1 \
  -module_name $dynamic_name \
  -dir [file join $output_dir ip-runtime]
set dynamic_core [get_ips $dynamic_name]
set dynamic_config $phase06d::config
dict set dynamic_config CONFIG.transform_length 16384
dict set dynamic_config CONFIG.run_time_configurable_transform_length true
set_property -dict $dynamic_config $dynamic_core

foreach core [list $fixed_core $dynamic_core] {
  generate_target all $core
  create_ip_run $core
}

set fixed_run "${phase06d::ip_name}_synth_1"
set dynamic_run "${dynamic_name}_synth_1"
launch_runs [list $fixed_run $dynamic_run] -jobs 4
foreach run_name [list $fixed_run $dynamic_run] {
  wait_on_run $run_name
  set run_status [get_property STATUS [get_runs $run_name]]
  if {![string match "synth_design Complete!*" $run_status]} {
    error "Synthesis failed for $run_name: $run_status"
  }
}

proc emit_core_record {core run_name output_dir label} {
  open_run $run_name
  report_utilization -file [file join $output_dir "utilization-${label}.rpt"]

  set handle [open [file join $output_dir "properties-${label}.txt"] w]
  puts $handle "CORE=$core"
  puts $handle "PART=[get_property PART [current_project]]"
  puts $handle "VIVADO=[version -short]"
  puts $handle "STATUS=[get_property STATUS [get_runs $run_name]]"
  foreach property_name [lsort [list_property [get_ips $core]]] {
    if {[string match CONFIG.* $property_name]} {
      puts $handle "$property_name=[get_property $property_name [get_ips $core]]"
    }
  }
  puts $handle "PORT_WIDTHS"
  foreach base_name [list s_axis_config_tdata m_axis_data_tuser] {
    set bits [get_ports -quiet "${base_name}\[*\]"]
    puts $handle "$base_name=[llength $bits]"
  }
  close $handle
  close_design
}

emit_core_record $phase06d::ip_name $fixed_run $output_dir fixed4096
emit_core_record $dynamic_name $dynamic_run $output_dir runtime16384

close_project
exit
