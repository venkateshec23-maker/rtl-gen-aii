# DRC via Magic  –  RTL-Gen AI
tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
gds read /work/traffic_controller.gds
load traffic_controller
drc check
set count [drc list count total]
puts "DRC violations: $count"
set fp [open /work/drc.rpt w]
puts $fp "DRC Report for traffic_controller"
puts $fp "Violations: $count"
foreach {cat cnt} [drc list count] {
    puts $fp "  $cat : $cnt"
    puts "  $cat : $cnt"
}
close $fp
quit