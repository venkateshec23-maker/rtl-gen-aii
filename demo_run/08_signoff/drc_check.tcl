# DRC via Magic  –  RTL-Gen AI
tech load /pdk/sky130A/libs.tech/magic/sky130A.tech
gds read /work/adder_8bit.gds
load adder_8bit
drc check
set count [drc list count total]
puts "DRC violations: $count"
set fp [open /work/drc.rpt w]
puts $fp "DRC Report for adder_8bit"
puts $fp "Violations: $count"
foreach {cat cnt} [drc list count] {
    puts $fp "  $cat : $cnt"
    puts "  $cat : $cnt"
}
close $fp
quit