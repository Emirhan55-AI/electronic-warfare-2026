namespace eval st06_runtime_fft {
  variable ip_name st06_fft_runtime_16384
  variable target_part xc7z020clg484-1

  source [file join [file dirname [file normalize [info script]]] phase06d_ip_config.tcl]
  variable config $phase06d::config
  dict set config CONFIG.transform_length 16384
  dict set config CONFIG.run_time_configurable_transform_length true

  proc create_configured_ip {ip_directory} {
    variable ip_name
    variable config
    file mkdir $ip_directory
    create_ip -name xfft -vendor xilinx.com -library ip -version 9.1 \
      -module_name $ip_name -dir $ip_directory
    set core [get_ips $ip_name]
    set_property -dict $config $core
    return $core
  }
}
