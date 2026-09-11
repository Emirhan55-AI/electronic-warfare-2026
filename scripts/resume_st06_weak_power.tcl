# Run through a short repository alias on Windows. Completed IP runs are retained.
set task_root [file normalize [file join [file dirname [info script]] ..]]
set ::env(P0_BUILD_VARIANT) st06-weak-power-20260910
if {[info exists ::env(P0_BOARD_REPO)]} {
  set_param board.repoPaths [list [file normalize $::env(P0_BOARD_REPO)]]
}
open_project [file join $task_root build p0 $::env(P0_BUILD_VARIANT) vivado p0_runtime.xpr]
generate_target all [get_files p0_system.bd]
foreach run [get_runs -filter {IS_SYNTHESIS == 1}] {
  set state [get_property STATUS $run]
  puts "P0:RESUME_RUN=$run STATUS=$state DIRECTORY=[get_property DIRECTORY $run]"
  if {[string match "*ERROR*" $state] || [string match "*Error*" $state]} {
    reset_run $run
  }
}
reset_run synth_1
close_project
source [file join $task_root scripts run_p0_vivado.tcl]
