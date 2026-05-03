// Simple FSM - 4-state Moore machine
// IDLE -> START -> RUN -> DONE -> IDLE
module fsm (
    input       clk,
    input       reset_n,
    input       go,
    input       done_sig,
    output reg  busy,
    output reg  complete
);
    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam RUN   = 2'd2;
    localparam DONE  = 2'd3;
    
    reg [1:0] state;
    
    always @(posedge clk) begin
        if (!reset_n) begin
            state <= IDLE;
            busy <= 0;
            complete <= 0;
        end else begin
            case (state)
                IDLE: begin
                    busy <= 0;
                    complete <= 0;
                    if (go) state <= START;
                end
                START: begin
                    busy <= 1;
                    state <= RUN;
                end
                RUN: begin
                    if (done_sig) state <= DONE;
                end
                DONE: begin
                    busy <= 0;
                    complete <= 1;
                    state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
