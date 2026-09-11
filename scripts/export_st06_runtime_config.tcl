# Reopen the routed runtime-control project with explicit ZedBoard metadata and
# reject stale or locked inputs before producing the deployable hardware XSA.
set task_root [file normalize [file join [file dirname [info script]] ..]]
set task_build [file join $task_root build p0 st06-runtime-config-v2-20260910]
if {[info exists ::env(P0_BOARD_REPO)]} {
  set_param board.repoPaths [list [file normalize $::env(P0_BOARD_REPO)]]
}
set task_board avnet-tria:zedboard:part0:1.5
if {[llength [get_board_parts -quiet $task_board]] != 1} { error "ZedBoard preset missing" }
open_project [file join $task_build vivado p0_runtime.xpr]
set_property board_part $task_board [current_project]
report_ip_status -file [file join $task_build ip-status-final.rpt]
set locked [get_ips -filter {IS_LOCKED == 1}]
puts "P0:LOCKED_IP_COUNT=[llength $locked]"
if {[llength $locked]} { error "IP lock remains after restoring board metadata" }
foreach run {synth_1 impl_1} {
  set stale [get_property NEEDS_REFRESH [get_runs $run]]
  puts "P0:RUN=$run NEEDS_REFRESH=$stale STATUS=[get_property STATUS [get_runs $run]]"
  if {$stale} { error "Board metadata changed implementation inputs; rebuild required" }
}
open_run impl_1
write_hw_platform -fixed -include_bit -force -file [file join $task_build hardware p0_system_50mhz.xsa]
puts "P0:EXPORT_BOARD_METADATA=PASS"
close_project
exit
