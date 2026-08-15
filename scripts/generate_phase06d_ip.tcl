set script_directory [file dirname [file normalize [info script]]]
set repository_root [file normalize [file join $script_directory ..]]
source [file join $script_directory phase06d_ip_config.tcl]

set run_name [expr {[llength $argv] >= 1 ? [lindex $argv 0] : "canonical"}]
if {![regexp {^[a-zA-Z0-9_-]+$} $run_name]} {
  error "run name must contain only letters, digits, underscore or dash"
}

set build_root [file normalize [file join $repository_root build phase06d ip-generation $run_name]]
set allowed_root [file normalize [file join $repository_root build phase06d]]
if {![string match "${allowed_root}/*" $build_root]} {
  error "refusing to use build directory outside repository build/phase06d"
}
if {[file exists $build_root]} {
  file delete -force $build_root
}
file mkdir $build_root

create_project phase06d_ip_generation $build_root -part $phase06d::target_part -force
set core [phase06d::create_configured_ip [file join $build_root ip]]
phase06d::emit_configuration $core
# PHASE-06D is functional vendor simulation only.  Generate the simulation
# product set; do not invoke synthesis or implementation flows.
generate_target simulation $core

set generated_xci [file normalize [get_property IP_FILE $core]]
set canonical_directory [file normalize [file join $repository_root rtl phase06d ip $phase06d::ip_name]]
file mkdir $canonical_directory
set canonical_xci [file join $canonical_directory "${phase06d::ip_name}.xci"]
file copy -force $generated_xci $canonical_xci

puts "PHASE06D:TARGET_PART=$phase06d::target_part"
puts "PHASE06D:GENERATED_XCI=$generated_xci"
puts "PHASE06D:CANONICAL_XCI=$canonical_xci"
puts "PHASE06D:GENERATED_PRODUCTS=complete"
close_project
exit
