# Manual Review Checklist

For each design in the dataset, verify:

## Correctness
- [ ] RTL code compiles without errors
- [ ] Testbench executes successfully
- [ ] All tests pass
- [ ] No critical warnings

## Completeness
- [ ] Description is clear and accurate
- [ ] All ports properly declared
- [ ] Comments explain complex logic
- [ ] Testbench covers main functionality

## Quality
- [ ] Code follows style guide
- [ ] Proper indentation (2 or 4 spaces)
- [ ] Meaningful signal names
- [ ] No deprecated constructs

## Metadata
- [ ] Category is correct
- [ ] Complexity level accurate
- [ ] Tags are relevant
- [ ] Bit width matches code

## Documentation
- [ ] Header comment present
- [ ] Module purpose explained
- [ ] Port descriptions included
- [ ] Any assumptions documented

## Special Cases

### Combinational Logic
- [ ] Uses assign or always @(*)
- [ ] No clock or reset
- [ ] Synthesizable

### Sequential Logic
- [ ] Uses always @(posedge clk)
- [ ] Has reset logic
- [ ] Non-blocking assignments (<=)

### FSM
- [ ] State definitions present
- [ ] All states reachable
- [ ] Outputs defined for all states

## Notes
Add any observations or concerns here.
