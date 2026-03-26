// Traffic Light Controller - 4-bit FSM
// Intersection control with RED (30s) → GREEN (25s) → YELLOW (5s) cycle

module traffic_controller (
    input  clk,
    input  reset,
    input  enable,
    output reg red,
    output reg green,
    output reg yellow
);

    // FSM States
    localparam IDLE = 2'b00;
    localparam RED_STATE = 2'b01;
    localparam GREEN_STATE = 2'b10;
    localparam YELLOW_STATE = 2'b11;

    // Timing constants (in clock cycles at 1MHz = 1us per cycle)
    localparam RED_TIME = 30_000_000;      // 30 seconds
    localparam GREEN_TIME = 25_000_000;    // 25 seconds
    localparam YELLOW_TIME = 5_000_000;    // 5 seconds

    reg [1:0] state, next_state;
    reg [27:0] timer;  // Can count up to 268M cycles

    // ─────────────────────────────────────────────────────────
    // STATE MACHINE - Sequential Logic
    // ─────────────────────────────────────────────────────────
    always @(posedge clk) begin
        if (reset)
            state <= IDLE;
        else
            state <= next_state;
    end

    // ─────────────────────────────────────────────────────────
    // NEXT STATE LOGIC & TIMER
    // ─────────────────────────────────────────────────────────
    always @(posedge clk) begin
        if (reset)
            timer <= 28'b0;
        else if (!enable)
            timer <= 28'b0;
        else if (timer == 28'b0)
            timer <= 28'b0;
        else
            timer <= timer - 1'b1;
    end

    always @(*) begin
        next_state = state;
        
        case (state)
            IDLE: begin
                if (enable)
                    next_state = RED_STATE;
                else
                    next_state = IDLE;
            end
            
            RED_STATE: begin
                if (timer == 0 || timer == 1)
                    next_state = GREEN_STATE;
            end
            
            GREEN_STATE: begin
                if (timer == 0 || timer == 1)
                    next_state = YELLOW_STATE;
            end
            
            YELLOW_STATE: begin
                if (timer == 0 || timer == 1)
                    next_state = RED_STATE;
            end
            
            default:
                next_state = IDLE;
        endcase
    end

    // ─────────────────────────────────────────────────────────
    // OUTPUT LOGIC & TIMER LOAD
    // ─────────────────────────────────────────────────────────
    always @(posedge clk) begin
        if (reset) begin
            red <= 1'b0;
            green <= 1'b0;
            yellow <= 1'b0;
        end else begin
            case (next_state)
                RED_STATE: begin
                    red <= 1'b1;
                    green <= 1'b0;
                    yellow <= 1'b0;
                    if (timer == 0)
                        timer <= RED_TIME;
                end
                
                GREEN_STATE: begin
                    red <= 1'b0;
                    green <= 1'b1;
                    yellow <= 1'b0;
                    if (timer == 0)
                        timer <= GREEN_TIME;
                end
                
                YELLOW_STATE: begin
                    red <= 1'b0;
                    green <= 1'b0;
                    yellow <= 1'b1;
                    if (timer == 0)
                        timer <= YELLOW_TIME;
                end
                
                default: begin
                    red <= 1'b0;
                    green <= 1'b0;
                    yellow <= 1'b0;
                end
            endcase
        end
    end

endmodule
