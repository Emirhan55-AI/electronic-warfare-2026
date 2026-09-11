set script_directory [file dirname [file normalize [info script]]]
set repository_root [file normalize [file join $script_directory ..]]
set build_root [file normalize [file join $repository_root build p0 vivado]]
set allowed_root [file normalize [file join $repository_root build p0]]
set isolated_build 0
set runtime_config 0
if {[info exists ::env(P0_RUNTIME_CONFIG)] && $::env(P0_RUNTIME_CONFIG) eq "1"} {
  set runtime_config 1
}
if {![info exists ::env(P0_BUILD_VARIANT)] || $::env(P0_BUILD_VARIANT) eq ""} {
  error "ST-06 power build requires a unique P0_BUILD_VARIANT"
}
if {[info exists ::env(P0_BUILD_VARIANT)] && $::env(P0_BUILD_VARIANT) ne ""} {
  if {![regexp {^[A-Za-z0-9_-]+$} $::env(P0_BUILD_VARIANT)]} {
    error "P0_BUILD_VARIANT must be a directory name without path separators"
  }
  set isolated_build 1
  set build_root [file join $allowed_root $::env(P0_BUILD_VARIANT) vivado]
}
set zedboard_part {avnet-tria:zedboard:part0:1.5}
if {[info exists ::env(P0_BOARD_REPO)] && $::env(P0_BOARD_REPO) ne ""} {
  set board_repository [file normalize $::env(P0_BOARD_REPO)]
  if {![file isdirectory $board_repository]} {
    error "P0_BOARD_REPO is not a directory: $board_repository"
  }
  set_param board.repoPaths [list $board_repository]
}
if {[llength [get_board_parts -quiet $zedboard_part]] != 1} {
  error "required ZedBoard preset not found: $zedboard_part (install Avnet bdf or set P0_BOARD_REPO)"
}
if {![string match "${allowed_root}/*" $build_root]} {
  error "refusing to use a build directory outside repository build/p0"
}
if {[file exists $build_root]} {
  if {$isolated_build} {
    error "isolated build already exists; choose a new P0_BUILD_VARIANT"
  }
  file delete -force $build_root
}
file mkdir $build_root

create_project p0_runtime $build_root -part xc7z020clg484-1 -force
set_property board_part $zedboard_part [current_project]
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]

set rtl_sources [list \
  [file join $repository_root algorithms fpga phase06a rtl axis_skid_buffer.sv] \
  [file join $repository_root algorithms fpga phase06b rtl phase06b_pkg.sv] \
  [file join $repository_root algorithms fpga phase06b rtl axis_hann_window.sv] \
  [file join $repository_root algorithms fpga phase06c rtl phase06c_pkg.sv] \
  [file join $repository_root algorithms fpga phase06c rtl axis_fft_wrapper.sv] \
  [file join $repository_root algorithms fpga phase06d rtl amd_xfft_adapter.sv] \
  [file join $repository_root algorithms fpga phase06f rtl axis_fft_linear_power.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_os_cfar_pkg.sv] \
  [file join $repository_root algorithms fpga p0 rtl axis_p0_os_cfar.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_dsp_runtime_top.sv] \
  [file join $repository_root algorithms fpga p0 rtl p0_dsp_runtime_bd.v] \
]
add_files -fileset sources_1 -norecurse $rtl_sources
if {$runtime_config} {
  add_files -fileset sources_1 -norecurse [list \
    [file join $repository_root algorithms fpga p0 rtl p0_detection_control.sv] \
    [file join $repository_root algorithms fpga p0 rtl p0_dsp_configurable_bd.v]]
}
set coefficient_file [file join $repository_root datasets fixtures phase06b hann-coefficients.mem]
add_files -fileset sources_1 -norecurse $coefficient_file
set_property file_type {Memory Initialization Files} [get_files [file tail $coefficient_file]]

set xci [file join $repository_root algorithms fpga phase06d ip phase06d_fft_4096 phase06d_fft_4096.xci]
import_ip -files $xci -name phase06d_fft_4096
generate_target all [get_ips phase06d_fft_4096]
update_compile_order -fileset sources_1

create_bd_design p0_system
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0]
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
  -config {make_external "FIXED_IO, DDR" apply_board_preset "1"} $ps
set_property -dict [list \
  CONFIG.PCW_USE_M_AXI_GP0 {1} \
  CONFIG.PCW_USE_S_AXI_HP0 {1} \
  CONFIG.PCW_USE_FABRIC_INTERRUPT {1} \
  CONFIG.PCW_IRQ_F2P_INTR {1} \
  CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {50.000000} \
] $ps

set dma [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 axi_dma_0]
set_property -dict [list \
  CONFIG.c_include_sg {0} \
  CONFIG.c_include_mm2s {1} \
  CONFIG.c_include_s2mm {1} \
  CONFIG.c_sg_length_width {16} \
  CONFIG.c_m_axis_mm2s_tdata_width {16} \
  CONFIG.c_s_axis_s2mm_tdata_width {64} \
  CONFIG.c_mm2s_burst_size {16} \
  CONFIG.c_s2mm_burst_size {16} \
] $dma

set dsp_module p0_dsp_runtime_bd
if {$runtime_config} { set dsp_module p0_dsp_configurable_bd }
set dsp [create_bd_cell -type module -reference $dsp_module p0_dsp_runtime_0]
set control_ic [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_control_interconnect]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] $control_ic
if {$runtime_config} { set_property CONFIG.NUM_MI {2} $control_ic }
set memory_ic [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_memory_interconnect]
set_property -dict [list CONFIG.NUM_SI {2} CONFIG.NUM_MI {1}] $memory_ic
set reset [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_0]
set irq_concat [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 irq_concat]
set_property -dict [list CONFIG.NUM_PORTS {2}] $irq_concat

connect_bd_intf_net [get_bd_intf_pins $ps/M_AXI_GP0] [get_bd_intf_pins $control_ic/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $control_ic/M00_AXI] [get_bd_intf_pins $dma/S_AXI_LITE]
if {$runtime_config} {
  connect_bd_intf_net [get_bd_intf_pins $control_ic/M01_AXI] [get_bd_intf_pins $dsp/S_AXI]
  connect_bd_net [get_bd_pins $ps/FCLK_CLK0] [get_bd_pins $control_ic/M01_ACLK]
  connect_bd_net [get_bd_pins $reset/peripheral_aresetn] [get_bd_pins $control_ic/M01_ARESETN]
}
connect_bd_intf_net [get_bd_intf_pins $dma/M_AXI_MM2S] [get_bd_intf_pins $memory_ic/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $dma/M_AXI_S2MM] [get_bd_intf_pins $memory_ic/S01_AXI]
connect_bd_intf_net [get_bd_intf_pins $memory_ic/M00_AXI] [get_bd_intf_pins $ps/S_AXI_HP0]
connect_bd_intf_net [get_bd_intf_pins $dma/M_AXIS_MM2S] [get_bd_intf_pins $dsp/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins $dsp/M_AXIS] [get_bd_intf_pins $dma/S_AXIS_S2MM]

connect_bd_net [get_bd_pins $ps/FCLK_CLK0] \
  [get_bd_pins $ps/M_AXI_GP0_ACLK] \
  [get_bd_pins $ps/S_AXI_HP0_ACLK] \
  [get_bd_pins $dma/s_axi_lite_aclk] \
  [get_bd_pins $dma/m_axi_mm2s_aclk] \
  [get_bd_pins $dma/m_axi_s2mm_aclk] \
  [get_bd_pins $control_ic/ACLK] \
  [get_bd_pins $control_ic/S00_ACLK] \
  [get_bd_pins $control_ic/M00_ACLK] \
  [get_bd_pins $memory_ic/ACLK] \
  [get_bd_pins $memory_ic/S00_ACLK] \
  [get_bd_pins $memory_ic/S01_ACLK] \
  [get_bd_pins $memory_ic/M00_ACLK] \
  [get_bd_pins $reset/slowest_sync_clk] \
  [get_bd_pins $dsp/aclk]
connect_bd_net [get_bd_pins $ps/FCLK_RESET0_N] [get_bd_pins $reset/ext_reset_in]
connect_bd_net [get_bd_pins $reset/peripheral_aresetn] \
  [get_bd_pins $dma/axi_resetn] \
  [get_bd_pins $control_ic/ARESETN] \
  [get_bd_pins $control_ic/S00_ARESETN] \
  [get_bd_pins $control_ic/M00_ARESETN] \
  [get_bd_pins $memory_ic/ARESETN] \
  [get_bd_pins $memory_ic/S00_ARESETN] \
  [get_bd_pins $memory_ic/S01_ARESETN] \
  [get_bd_pins $memory_ic/M00_ARESETN] \
  [get_bd_pins $dsp/aresetn]
connect_bd_net [get_bd_pins $dma/mm2s_introut] [get_bd_pins $irq_concat/In0]
connect_bd_net [get_bd_pins $dma/s2mm_introut] [get_bd_pins $irq_concat/In1]
connect_bd_net [get_bd_pins $irq_concat/dout] [get_bd_pins $ps/IRQ_F2P]

assign_bd_address
if {$runtime_config} {
  set config_segment [get_bd_addr_segs -of_objects [get_bd_intf_pins $dsp/S_AXI]]
  if {[llength $config_segment] != 1} { error "Expected one DSP configuration address segment" }
  assign_bd_address -force -offset 0x43C00000 -range 0x00010000 \
    -target_address_space [get_bd_addr_spaces $ps/Data] $config_segment
}
regenerate_bd_layout
validate_bd_design
save_bd_design

set bd_file [get_files p0_system.bd]
generate_target all $bd_file
set wrapper_files [make_wrapper -files $bd_file -top]
add_files -norecurse $wrapper_files
set_property top p0_system_wrapper [get_filesets sources_1]
update_compile_order -fileset sources_1
puts "P0:TOOL=[version -short]"
puts "P0:PROJECT=[file join $build_root p0_runtime.xpr]"
puts "P0:BLOCK_DESIGN=$bd_file"
puts "P0:VALIDATE_BD=PASS"
close_project
if {![info exists ::env(P0_CONTINUE_BUILD)] || $::env(P0_CONTINUE_BUILD) ne "1"} {
  exit
}
