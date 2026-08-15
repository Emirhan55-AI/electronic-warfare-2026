namespace eval phase06d {
  variable ip_name phase06d_fft_4096
  variable ip_vendor xilinx.com
  variable ip_library ip
  variable ip_core xfft
  variable ip_version 9.1
  variable target_part xc7z020clg484-1

  variable config [list \
    CONFIG.channels {1} \
    CONFIG.transform_length {4096} \
    CONFIG.run_time_configurable_transform_length {false} \
    CONFIG.implementation_options {pipelined_streaming_io} \
    CONFIG.throttle_scheme {nonrealtime} \
    CONFIG.target_clock_frequency {250} \
    CONFIG.target_data_throughput {50} \
    CONFIG.super_sample_rates {1} \
    CONFIG.data_format {fixed_point} \
    CONFIG.input_width {16} \
    CONFIG.phase_factor_width {24} \
    CONFIG.scaling_options {unscaled} \
    CONFIG.rounding_modes {convergent_rounding} \
    CONFIG.output_ordering {natural_order} \
    CONFIG.xk_index {true} \
    CONFIG.cyclic_prefix_insertion {false} \
    CONFIG.ovflo {false} \
    CONFIG.butterfly_type {use_luts} \
    CONFIG.complex_mult_type {use_mults_resources} \
    CONFIG.memory_options_data {block_ram} \
    CONFIG.memory_options_phase_factors {block_ram} \
    CONFIG.memory_options_reorder {block_ram} \
    CONFIG.memory_options_hybrid {false} \
    CONFIG.number_of_stages_using_block_ram_for_data_and_phase_factors {5} \
    CONFIG.blocking_run_time_configuration {false} \
    CONFIG.systolicfft_inv {false} \
    CONFIG.aresetn {true} \
    CONFIG.aclken {false} \
  ]

  proc create_configured_ip {ip_directory} {
    variable ip_name
    variable ip_vendor
    variable ip_library
    variable ip_core
    variable ip_version
    variable config

    file mkdir $ip_directory
    create_ip \
      -name $ip_core \
      -vendor $ip_vendor \
      -library $ip_library \
      -version $ip_version \
      -module_name $ip_name \
      -dir $ip_directory
    set core [get_ips $ip_name]
    set_property -dict $config $core
    return $core
  }

  proc emit_configuration {core} {
    puts "PHASE06D:IPDEF=[get_property IPDEF $core]"
    puts "PHASE06D:IP_REVISION=[get_property CORE_REVISION $core]"
    puts "PHASE06D:SW_VERSION=[get_property SW_VERSION $core]"
    foreach property_name [lsort [list_property $core]] {
      if {[string match CONFIG.* $property_name]} {
        puts "PHASE06D:CONFIG:$property_name=[get_property $property_name $core]"
      }
    }
  }
}
