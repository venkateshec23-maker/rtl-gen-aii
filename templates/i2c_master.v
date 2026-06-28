// I2C Master - Simple single-byte write
// Basic I2C master for 7-bit addressing
module i2c_master (
    input           clk,
    input           reset_n,
    input           start,
    input   [6:0]   addr,
    input           rw,
    input   [7:0]   tx_data,
    output reg [7:0] rx_data,
    inout           sda,
    output reg      scl,
    output reg      busy,
    output reg      done,
    output reg      ack_error
);
    reg [3:0] state;
    reg [3:0] bit_cnt;
    reg [7:0] shift_reg;
    reg sda_out;
    reg scl_en;
    
    localparam IDLE = 0, START = 1, ADDR = 2, ACK1 = 3,
               DATA = 4, ACK2 = 5, STOP = 6;
    
    assign sda = sda_out ? 1'bz : 1'b0;
    
    // Drive SDA high (idle) at time 0 to prevent X on open-drain output
    initial sda_out = 1'b1;

    always @(posedge clk) begin
        if (!reset_n) begin
            state <= IDLE; bit_cnt <= 0; shift_reg <= 0;
            sda_out <= 1; scl <= 1; scl_en <= 0;
            busy <= 0; done <= 0; ack_error <= 0; rx_data <= 0;
        end else begin
            done <= 0;
            case (state)
                IDLE: begin
                    if (start) begin
                        state <= START; busy <= 1; scl_en <= 1;
                    end
                end
                START: begin
                    sda_out <= 0;
                    state <= ADDR;
                    shift_reg <= {addr, rw};
                    bit_cnt <= 8;
                end
                ADDR: begin
                    scl <= ~scl;
                    if (!scl) begin
                        sda_out <= shift_reg[7];
                        shift_reg <= {shift_reg[6:0], 1'b1};
                    end else if (scl && bit_cnt > 0) begin
                        bit_cnt <= bit_cnt - 1;
                        if (bit_cnt == 1) state <= ACK1;
                    end
                end
                ACK1: begin
                    scl <= ~scl;
                    if (!scl) begin
                        state <= DATA;
                        bit_cnt <= 8;
                        if (rw) shift_reg <= 8'hFF;
                        else shift_reg <= tx_data;
                    end else if (scl) begin
                        ack_error <= sda;
                    end
                end
                DATA: begin
                    scl <= ~scl;
                    if (!scl) begin
                        sda_out <= shift_reg[7];
                        shift_reg <= {shift_reg[6:0], 1'b1};
                    end else if (scl) begin
                        if (rw) shift_reg <= {shift_reg[6:0], sda};
                        bit_cnt <= bit_cnt - 1;
                        if (bit_cnt == 0) state <= ACK2;
                    end
                end
                ACK2: begin
                    scl <= ~scl;
                    if (!scl) begin
                        sda_out <= 1;
                        state <= STOP;
                    end
                end
                STOP: begin
                    scl <= ~scl;
                    if (!scl) begin
                        sda_out <= 1;
                    end else begin
                        state <= IDLE; busy <= 0; done <= 1; scl_en <= 0;
                        if (rw) rx_data <= shift_reg;
                    end
                end
                default: begin
                    // Unknown state: recover to IDLE safely
                    state <= IDLE; busy <= 0; scl_en <= 0;
                    sda_out <= 1; scl <= 1;
                end
            endcase
            if (!scl_en) scl <= 1;
        end
    end
endmodule
