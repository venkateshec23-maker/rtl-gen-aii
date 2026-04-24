# DRC via Magic  –  RTL-Gen AI
tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
gds read /work/my_design.gds
load my_design
drc check
set count [drc list count total]
puts "DRC violations: $count"
set fp [open /work/drc.rpt w]
puts $fp "DRC Report for my_design"
puts $fp "Violations: $count"
foreach {cat cnt} [drc list count] {
    puts $fp "  $cat : $cnt"
    puts "  $cat : $cnt"
}
close $fp
quit